"""
pydb2access.py - convert a PEP 249 DB to MS Access
XML preserving data types with XSD

Requires lxml - http://lxml.de/ (pip install lxml)
and dateutil (pip install dateutil)

Terry Brown, Terry_N_Brown@yahoo.com, Wed Jan  7 12:35:33 2015
"""

import argparse
import datetime
import getpass
import pprint

import sqlite3 as db249

from collections import defaultdict, OrderedDict
from xml.sax.saxutils import escape

from dateutil.parser import parse

from lxml import etree
from lxml.builder import ElementMaker

XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XSD_NS = "http://www.w3.org/2001/XMLSchema"
OD_NS = "urn:schemas-microsoft-com:officedata"

NS_MAP = {
    'xsi': XSI_NS,
    'xsd': XSD_NS,
    'od': OD_NS,
}

CONNECT_PARAMS = [
    ('dsn', "Data source name as string"),
    ('user', "User name as string"),
    ('password', "Password as string, 'prompt' for prompt"),
    ('host', "Hostname"),
    ('database', "Database name"),
]




NODATE0 = parse('9000-1-1 12:12')
NODATE1 = parse('9001-2-2 13:13')

def datetime_field(s):
    
    dt0 = parse(s, default=NODATE0)
    dt1 = parse(s, default=NODATE1)
    
    if dt0 != dt1:
        raise TypeError
        
    return dt0
def date_field(s):

    dt0 = parse(s, default=NODATE0)
    dt1 = parse(s, default=NODATE1)
    
    if dt0.date() != dt1.date():
        raise TypeError

    return dt0.date()
def time_field(s):

    dt0 = parse(s, default=NODATE0)
    dt1 = parse(s, default=NODATE1)
    
    if dt0.time() != dt1.time():
        raise TypeError

    return dt0.time()
def text_field(s):
    s = unicode(s)
    if len(s) > 255:
        raise TypeError
    return s

# types ordered from most to least demanding
TYPES = OrderedDict([
    (int, "xsd:integer"), 
    (float, "xsd:decimal"), 
    (datetime_field, "xsd:dateTime"),
    (date_field, "xsd:dateTime"),
    (time_field, "xsd:dateTime"),
    (text_field, "xsd:string"),  # 255 char or less
    (unicode, "NOT USED"),  # memo field
])

TIME_FMT = {
    date_field: "Medium Date",
    time_field: "Long Time",
    datetime_field: "General Date",
}
def make_parser():
     
    parser = argparse.ArgumentParser(
        description="""Convert a PEP 249 DB to MS Access""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
     
    parser.add_argument("--show-tables", action='store_true',
        help="Just show tables"
    )
    
    # parser.add_argument("--sort-fields", action='store_true',
    #     help="Order fields alphabetically"
    # )
    
    parser.add_argument("--tables", type=str, default=[], nargs='+',
        help="tables to include, omit for all"
    )
    
    parser.add_argument("--limit", type=int, default=-1,
        help="max. rows to output, per table, for testing"
    )

    parser.add_argument('output', type=str,
             help="base name for output, '.xml' and '.xsd' files created"
         )

    for cp, desc in CONNECT_PARAMS:
        parser.add_argument("--"+cp, help=desc)

    return parser
 
def chain_end(*elements):
    "Make a chain of elements by .append()ing and return last (inner) element"
    elements = list(elements)
    while len(elements) > 1:
        elements[0].append(elements[1])
        elements.pop(0)
    return elements[0]
    
def get_field_names(cur, table_name, sort=False):
    cur.execute("select * from %s limit 0" % table_name)
    field_names = [i[0] for i in cur.description]
    # if sort:
    #     field_names.sort()
    return field_names
    
def check_types(x, types):
    while types:
        try:
            types[0](unicode(x))  # int(float) fails to fail, int("10.2") doesn't
            break
        except (TypeError, ValueError):
            #D print 'DROPPED', types[0], x
            types.pop(0)    
def main():
    opt = make_parser().parse_args()
    opt.sort_fields = False

    if opt.password == 'prompt':
        opt.password = getpass.getpass("DB password: ")

    E = ElementMaker(nsmap=NS_MAP)
    
    connect_params = {cp: getattr(opt, cp) for 
                      (cp, desc) in CONNECT_PARAMS
                      if getattr(opt, cp) is not None}
    
    con = db249.connect(**connect_params)
    cur = con.cursor()
    
    if not opt.tables:
        cur.execute("select tbl_name from sqlite_master where type = 'table'")
        opt.tables = [i[0] for i in cur.fetchall()]
        
    if opt.show_tables:
        print(' '.join(opt.tables))
        exit(0)
    
    db = E('dataroot')
    db.set('{%s}noNamespaceSchemaLocation' % XSI_NS, "%s.xsd" % opt.output)
    
    output = open('%s.xml' % opt.output, 'w')
    template = etree.tostring(etree.ElementTree(db), 
                              encoding='UTF-8', xml_declaration=True)
    template = template.replace("/>", ">")
    output.write(template+'\n')

    type_map = defaultdict(lambda: list(TYPES))

    for table_name in opt.tables:
        fields = get_field_names(cur, table_name, opt.sort_fields)
        cur.execute("select * from %s" % table_name)
        for row_n, row in enumerate(cur):
            if opt.limit and row_n == opt.limit:
                break
            output.write("<%s>\n" % table_name)
            for field_n, field_name in enumerate(fields):
                x = row[field_n]
                if x is None:
                    continue
                value = "<%s>%s</%s>\n" % (
                    field_name, escape(unicode(x)), field_name)
                output.write(value.encode('utf-8'))
                key = (table_name, field_name)
                if x is not None and len(type_map[key]) > 1:
                    check_types(x, type_map[key])
            output.write("</%s>\n" % table_name)
    
    output.write("</dataroot>\n")
    output.close()
    
    # for k,v in type_map.iteritems():
    #     print k, v

    E = ElementMaker(namespace=XSD_NS, nsmap=NS_MAP)
    
    xsd = E('schema')
    root = chain_end(xsd, E('element', name='dataroot'), E('complexType'), E('sequence'))
    for table_name in opt.tables:
        root.append(E('element', ref=table_name, minOccurs="0",
            maxOccurs="unbounded"))
    for table_name in opt.tables:
        table = chain_end(xsd, E('element', name=table_name), 
                               E('complexType'), E('sequence'))
        
        for field_name in get_field_names(cur, table_name, opt.sort_fields):
            key = (table_name, field_name)
            element = chain_end(table,
                E('element', name=field_name, minOccurs="0"))
            type_ = type_map[key][0]
            if type_ is not unicode:
                element.set('type', TYPES[type_map[key][0]])
            else:
                chain_end(element,
                    E('simpleType'),
                    E('restriction', base='xsd:string'),
                    E('maxLength', value='536870910')
                )
            if type_ in TIME_FMT:
                chain_end(element,
                    E('annotation'),
                    E('appinfo'),
                    E('{%s}fieldProperty' % OD_NS, name='Format', type='10',
                      value=TIME_FMT[type_])
                )
                    
    open('%s.xsd' % opt.output, 'w').write(etree.tostring(xsd, pretty_print=True))

if __name__ == '__main__':
    main()


# for reference
"""
<?xml version="1.0" encoding="utf-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="dataroot">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element ref="others" minOccurs="0"
        maxOccurs="unbounded" />
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
  <xsd:element name="others">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element name="one" minOccurs="0"></xsd:element>
        <xsd:element name="two" minOccurs="0" type="xsd:int">
        </xsd:element>
        <xsd:element name="etc" minOccurs="0"></xsd:element>
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
</xsd:schema>
"""
