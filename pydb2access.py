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
import os
import sys

from collections import defaultdict, OrderedDict
from xml.sax.saxutils import escape

try:
    from dateutil.parser import parse
except ImportError:
    sys.stderr.write("pydb2access requires dateutil")
    exit(10)

try:
    from lxml import etree
    from lxml.builder import ElementMaker
except ImportError:
    sys.stderr.write("pydb2access requires lxml")
    exit(10)

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

# see datetime_field()
NODATE0 = parse('9000-1-1 12:12')
NODATE1 = parse('9001-2-2 13:13')

def con_cur(opt, db249):
    """
    con_cur - Return connection to database

    :param argparse Namespace opt: options
    :param module db249: PEP 249 DB API 2 module
    :return: connection, cursor tuple
    :rtype: (con, cur)
    """
    connect_params = {cp: getattr(opt, cp) for 
                      (cp, desc) in CONNECT_PARAMS
                      if getattr(opt, cp) is not None}

    if opt.dsn:
        con = db249.connect(
            opt.dsn + 
            ((" password=%s" % opt.password) if opt.password else '')
        )
    else:
        con = db249.connect(**connect_params)

    cur = con.cursor()
    
    if opt.schema:
        cur.execute('set search_path to %s' % opt.schema)
    
    return con, cur
def get_tables(opt, db249):
    """
    get_tables - Return list of tables

    :param argparse Namespace opt: options
    :param module db249: PEP 249 DB API 2 module
    :return: list of tables
    :rtype: [str,...]
    """
    
    con, cur = con_cur(opt, db249)
    
    if opt.module == 'sqlite3':
        cur.execute("select tbl_name from sqlite_master where type = 'table'")
    elif opt.schema:
        cur.execute("select table_name from information_schema.tables "
                    "where table_schema=%s", [opt.schema])
    elif opt.module == 'psycopg2':
        cur.execute("select table_schema||'.'||table_name "
                    "from information_schema.tables")
    else:
        cur.execute("select table_name from information_schema.tables")
    
    return [i[0] for i in cur.fetchall()]
def datetime_field(s):
    """Try and parse str s as a date and time, raise TypeError if not possible
    """
    dt0 = parse(s, default=NODATE0)
    dt1 = parse(s, default=NODATE1)
    
    if dt0 != dt1:
        # s is the same for both calls, but all parts (year, minute,
        # etc.) of NODATE0 and NODATE1 differ, so any difference comes
        # from the use of part of the default, implying s is not a
        # complete date and time
        raise TypeError
        
    return dt0
def date_field(s):
    """Try and parse str s as a date, raise TypeError if not possible
    """
    dt0 = parse(s, default=NODATE0)
    dt1 = parse(s, default=NODATE1)
    
    if dt0.date() != dt1.date():
        # see datetime_field
        raise TypeError

    return dt0.date()
def time_field(s):
    """Try and parse str s as a time, raise TypeError if not possible
    """
    dt0 = parse(s, default=NODATE0)
    dt1 = parse(s, default=NODATE1)
    
    if dt0.time() != dt1.time():
        # see datetime_field
        raise TypeError

    return dt0.time()
def text_field(s):
    """Try and parse str s as a string <= 255 char, raise TypeError otherwise
    """
    s = unicode(s)  # FIXME: 255 character unicode can be more than 255 bytes?
    if len(s) > 255:
        raise TypeError
    return s

# types ordered from most to least demanding
TYPES = OrderedDict([
    (int, "xsd:integer"), 
    (float, "xsd:double"), 
    (datetime_field, "xsd:dateTime"),
    (date_field, "xsd:dateTime"),
    (time_field, "xsd:dateTime"),
    (text_field, "xsd:string"),  # 255 char or less
    (unicode, "NOT NEEDED"),  # memo field
])

# Access format names for date/time
TIME_FMT = {
    date_field: "Medium Date",
    time_field: "Long Time",
    datetime_field: "General Date",
}
def make_parser():
    """Return an argparse parser"""

    parser = argparse.ArgumentParser(
        description="""Convert a PEP 249 DB to MS Access""",
        # formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
     
    parser.add_argument('output', type=str,
        help="base name for output folder for .xml and .xsd files"
    )

    parser.add_argument("--tables", type=str, nargs='+',
        help="list of tables to include, omit for all", default=[]
    )
    
    parser.add_argument("--exclude-tables", type=str, nargs='+',
        help="list of tables to exclude", default=[]
    )
    
    parser.add_argument("--exclude-types", type=str, nargs='+',
        help="list of types to exclude, get numbers using --show-types", default=[]
    )
    
    parser.add_argument("--module", type=str, default='sqlite3',
        help="name of DB API module, 'sqlite3' or 'psycopg2' for PostgreSQL"
    )
    
    parser.add_argument("--prefix", type=str, default='',
        help="prefix for all exported table names, e.g. 'myschema_'"
    )
    
    parser.add_argument("--schema", type=str, default='',
        help="PostgreSQL schema (i.e. namespace)"
    )
    
    parser.add_argument("--limit", type=int, default=None,
        help="max. rows to output, per table, for testing"
    )

    parser.add_argument("--show-tables", action='store_true',
        help="Just show list of table names and exit"
    )

    parser.add_argument("--show-types", action='store_true',
        help="Just show list of types names and exit"
    )
    
    # parser.add_argument("--infer-types", action='store_true',
    #     help="Infer types instead of using DB types (always True for SQLite)"
    # )
    
    parser.add_argument("--sort-fields", action='store_true',
        help="Order fields alphabetically"
    )
    
    parser.add_argument("--top-id", action='store_true',
        help="Order fields alphabetically, but place fields with the same "
             "name as the table first"
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
    """
    get_field_names - Return list of field names in `table_name`

    :param PEP 249 cursor cur: cursor to acces DB
    :param str table_name: table name
    :param bool sort: sort field names before returning
    :return: list of field names
    :rtype: [str,...]
    """
    cur.execute("select * from %s limit 0" % table_name)
    field_names = [i[0] for i in cur.description]
    if sort:
        field_names.sort()
    return field_names
    
def make_type_map(opt, db249):
    pass
def check_types(x, types):
    """
    check_types - trim list of types until first type can interpret x

    :param variant x: value to test type list with
    :param list types: types ordered from most specific to most general
    :return: nothing, but changes `types`
    """

    while types:
        try:
            types[0](unicode(x))  # int(float) fails to fail, int("10.2") doesn't
            break
        except (TypeError, ValueError):
            #D print 'DROPPED', types[0], x
            types.pop(0)    
def main():

    opt = make_parser().parse_args()
    if opt.module == 'sqlite3':
        opt.infer_types = True
        
    opt.infer_types = True  # nothing else implemented yet
    
    exec "import %s as db249" % opt.module

    if opt.password == 'prompt':
        opt.password = getpass.getpass("DB password: ")

    if not opt.tables:
        opt.tables = get_tables(opt, db249)
    opt.tables = [i for i in opt.tables if i not in opt.exclude_tables]
        
    if opt.show_tables:
        print(' '.join(sorted(opt.tables)))
        exit(0)

    if opt.show_types:
        # usage = defaultdict(lambda: list())
        # doesn't work because of above exec
        usage = {}
        for k, v in get_types(opt, db249).items():
            usage.setdefault(v, list()).append("%s.%s" % k)
        for k in sorted(usage):
            print(k)
            print("  "+str(usage[k]))
            print("")
        exit(0)

    if not os.path.isdir(opt.output):
        os.mkdir(opt.output)
        
    output = open('%s/%s.xml' % (opt.output, opt.output), 'w')
    
    type_map = dump_data(opt, db249, output)
    
    if opt.show_tables:
        return

    if not opt.infer_types:
        type_map = make_type_map(opt, db249)
    
    output = open('%s/%s.xsd' % (opt.output, opt.output), 'w')

    dump_schema(opt, type_map, output)
def dump_data(opt, db249, output):
    """
    dump_data - write data to .xml file

    :param argparse Namespace opt: options
    :param module db249: PEP 249 DB API 2 module to use
    :param file output: open file
    """

    E = ElementMaker(nsmap=NS_MAP)
    
    con, cur = con_cur(opt, db249)
        
    db = E('dataroot')
    db.set('{%s}noNamespaceSchemaLocation' % XSI_NS, "%s.xsd" % opt.output)

    template = etree.tostring(etree.ElementTree(db), 
                              encoding='UTF-8', xml_declaration=True)
    template = template.replace("/>", ">")
    output.write(template+'\n')

    type_map = defaultdict(lambda: list(TYPES))
    
    types_used = get_types(opt, db249)

    for table_n, table_name in enumerate(opt.tables):
        fields = get_field_names(cur, table_name)
        fields = [i for i in fields 
                  if str(types_used[(table_name, i)]) not in opt.exclude_types]
        q = "select %s from %s" % (', '.join('"%s"' % i for i in fields), table_name)
        if opt.limit is not None:
            q += ' limit %d' % opt.limit
        cur.execute(q)
        print("Table %d/%d '%s', %d rows." % (table_n+1, len(opt.tables), table_name, cur.rowcount))
        for row_n, row in enumerate(cur):
            output.write("<%s%s>\n" % (opt.prefix, table_name))
            for field_n, field_name in enumerate(fields):
                
                x = row[field_n]
                
                if x is None:
                    continue
                    
                if isinstance(x, str):
                    x = x.decode('utf-8')
                if not isinstance(x, unicode):
                    x = unicode(x)
                value = "<%s>%s</%s>\n" % (
                    field_name, escape(x), field_name)
                    
                output.write(value.encode('utf-8'))
                
                if opt.infer_types:
                    key = (table_name, field_name)
                    if x is not None and len(type_map[key]) > 1:
                        check_types(x, type_map[key])

            output.write("</%s%s>\n" % (opt.prefix, table_name))

    type_map["_FKS"] = get_fks(opt, db249)
    if type_map["_FKS"]:
        
        for k, v in type_map["_FKS"].items():
            if (k[1], k[2]) in type_map and (v[1], v[2]) in type_map:
                output.write("<%s%s>\n" % (opt.prefix, '_LOOKUPS'))
                output.write("<from_table>%s</from_table>\n" % k[1])
                output.write("<from_field>%s</from_field>\n" % k[2])
                output.write("<to_table>%s</to_table>\n" % v[1])
                output.write("<to_field>%s</to_field>\n" % v[2])
                output.write("</%s%s>\n" % (opt.prefix, '_LOOKUPS'))
        
    output.write("</dataroot>\n")
    output.close()
    
    return type_map
    
def dump_schema(opt, type_map, output):
    """
    dump_schema - Write XML-Schema to .xsd file

    :param argparse Namespace opt: options
    :param dict type_map: type mappings
    :param file output: open file type object
    """

    tables = set(k[0] for k in type_map)
    if type_map["_FKS"]:
        tables.add("_LOOKUPS")
        type_map[("_LOOKUPS", "from_table")] = [text_field]
        type_map[("_LOOKUPS", "from_field")] = [text_field]
        type_map[("_LOOKUPS", "to_table")] = [text_field]
        type_map[("_LOOKUPS", "to_field")] = [text_field]
    
    E = ElementMaker(namespace=XSD_NS, nsmap=NS_MAP)
    
    xsd = E('schema')
    root = chain_end(xsd, E('element', name='dataroot'), E('complexType'), E('sequence'))
    for table_name in sorted(tables):
        root.append(E('element', ref=opt.prefix+table_name, minOccurs="0",
            maxOccurs="unbounded"))

    for table_name in sorted(tables):
        table = chain_end(xsd, E('element', name=opt.prefix+table_name), 
                               E('complexType'), E('sequence'))
        
        field_names = [k[1] for k in type_map if k[0] == table_name]
        if opt.sort_fields:
            field_names.sort()
        if opt.top_id:
            field_names = sort_fields(field_names, table_name)
        for field_name in field_names:
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
                    
    output.write(etree.tostring(xsd, pretty_print=True))
    output.close()
def get_types(opt, db249):
    """get_types - list types seen in DB

    :param argparse opt: options
    :param module db249: DB API module
    :return: dict of type usage
    :rtype: dict
    """

    con, cur = con_cur(opt, db249)
    types = {}
    
    for table in opt.tables:
        cur.execute("select * from %s limit 0" % table)
        for field in cur.description:
            types[(table, field.name)] = field.type_code
    
    return types
def sort_fields(fields, table_name):
    """sort_fields - sort fields to get PK first

    :param [str] fields: field names
    :param str table_name: table name
    :return: sorted field
    :rtype: [str]
    """
    
    if table_name in fields:
        return [table_name] + sorted([i for i in fields if i != table_name])
    guess_table = table_name.split('_', 1)[-1]
    return sorted(fields, key=lambda x: ' ' if x == guess_table else x)

def get_fks(opt, db249):
    """get_fks - return schema.table.field -> schema.table.field foreign key info

    :param argparse namespace opt: options
    :param module db249: pep 249 module
    :return: {(table, field): (table, field),...}
    :rtype: dict
    """

    if opt.module != 'psycopg2':
        return {}
    
    con, cur = con_cur(opt, db249)

    if opt.schema:
        # this makes things much faster
        filter = "where table_schema = '%s'" % opt.schema
    else:
        filter = ""
    q = """
        select constraint_column_usage.table_schema,
               constraint_column_usage.table_name,  -- the constraining table
               constraint_column_usage.column_name,
               key_column_usage.table_schema,
               key_column_usage.table_name,         -- the constrained table
               key_column_usage.column_name
          from (select * from information_schema.table_constraints
                 where constraint_type='FOREIGN KEY') table_constraints
               join 
               (select * from information_schema.key_column_usage
                 {filter}) key_column_usage using (constraint_name)
               join 
               (select * from information_schema.constraint_column_usage
                 {filter}) constraint_column_usage using (constraint_name)
        ;
    """.format(filter=filter)
    cur.execute(q)
    ans = {}
    for row in cur:
        ans[(row[3], row[4], row[5])] = (row[0], row[1], row[2])
    return ans

    
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

-- this is quite slow if not pre-filtered for schema, 'FOREIGN KEY' filter doesn't help much
select constraint_column_usage.table_schema,
       constraint_column_usage.table_name,  -- the constraining table
       constraint_column_usage.column_name,
       key_column_usage.table_schema,
       key_column_usage.table_name,         -- the constrained table
       key_column_usage.column_name
  from (select * from information_schema.table_constraints
         where constraint_type='FOREIGN KEY') table_constraints
       join 
       (select * from information_schema.key_column_usage
         where table_schema = 'glrimon') key_column_usage using (constraint_name)
       join 
       (select * from information_schema.constraint_column_usage
         where table_schema = 'glrimon') constraint_column_usage using (constraint_name)
;
"""
