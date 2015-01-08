"""
pydb2access.py - convert a PEP 249 DB to MS Access
XML preserving data types with XSD

Requires lxml - http://lxml.de/ (pip install lxml)
and parsedatetime (pip install parsedatetime)

Terry Brown, Terry_N_Brown@yahoo.com, Wed Jan  7 12:35:33 2015
"""

import argparse
import datetime
import getpass
import pprint

import sqlite3 as db249

from collections import defaultdict, OrderedDict
from xml.sax.saxutils import escape

from lxml import etree
from lxml.builder import ElementMaker

import parsedatetime

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

"""https://bear.im/code/parsedatetime/docs/index.html
   0 = not parsed at all
   1 = parsed as a C{date}
   2 = parsed as a C{time}
   3 = parsed as a C{datetime}
"""

CAL = parsedatetime.Calendar()

def datetime_field(s):
    time_s, level = CAL.parse(s)
    if level != 3:
        raise TypeError
    return datetime.datetime(time_s[0], time_s[1], time_s[2],
                             time_s[3], time_s[4], time_s[5])
def time_field(s):
    time_s, level = CAL.parse(s)
    if level != 2:
        raise TypeError
    return datetime.time(time_s[3], time_s[4], time_s[5])
def date_field(s):
    time_s, level = CAL.parse(s)
    if level != 1:
        raise TypeError
    return datetime.date(time_s[0], time_s[1], time_s[2])
def text_field(s):
    s = unicode(s)
    if len(s) > 255:
        raise TypeError
    return s

# types ordered from most to least demanding
TYPES = OrderedDict([
    (datetime_field, "xsd:dateTime"),
    (date_field, "xsd:dateTime"),  # '2014-06-06' parses as a time
    (time_field, "xsd:dateTime"),
    (int, "xsd:integer"), 
    (float, "xsd:decimal"), 
    (text_field, "xsd:string"),
    (unicode, "NOT USED"),
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
            print 'DROPPED', types[0], x
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
