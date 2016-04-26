"""
xml2csv.py - simple re-processing of .xml output of pydb2access.py
to csv

https://mail.python.org/pipermail/python-dev/2000-October/009946.html

Terry Brown, Terry_N_Brown@yahoo.com, Sat Apr 23 19:15:33 2016
"""

import csv
import json
import os
import sys
from xml.sax import make_parser, handler
from xml.sax.saxutils import unescape
class DBHandler(handler.ContentHandler):

    def __init__(self, tables=None):
        self.path = []
        self.table = None
        self.tables = {}
        self.ref_tables = tables
        self.writer = None
        self.row = {}

    def startElement(self, name, attrs):
        self.path.append(name)
        if len(self.path) == 3:
            self.tables.setdefault(self.path[1], list())
            if name not in self.tables[self.path[1]]:
                self.tables[self.path[1]].append(name)
    def characters(self, content):
        if len(self.path) == 3:
            self.row[self.path[2]] = unescape(content)

    def endElement(self, name):
        
        if len(self.path) != 2:
            del self.path[-1]
            return
        if self.table != self.path[1]:
            self.table = self.path[1]
            sys.stderr.write("%s\n" % self.table)
            if self.ref_tables:
                self.writer = csv.writer(open(self.table+'.csv', 'wb'))
                self.writer.writerow(self.ref_tables[self.path[1]])

        if self.ref_tables:
            self.writer.writerow([self.row.get(i) for i in self.ref_tables[self.path[1]]])
        self.row = {}
        
        del self.path[-1]
def main():
    
    parser = make_parser()
    handler = DBHandler()
    parser.setContentHandler(handler)
    parser.parse(sys.argv[1])
    ref_tables = handler.tables
    handler = DBHandler(ref_tables)
    parser.setContentHandler(handler)
    parser.parse(sys.argv[1])
    
    print json.dumps(ref_tables, indent=4)
if __name__ == '__main__':
    main()
