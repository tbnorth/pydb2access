"""
infer_fkeys.py - infer foreign key relationships by field content

ABANDONED: major conceptual flaw, any field with a small set of ints
as possible values is a subset of any other field that contains those
ints.  This code doesn't consider the uniqueness of fields as a
criteria for being an FK, but that would only help a little.

Terry Brown, Terry_N_Brown@yahoo.com, Sun Apr 24 13:20:37 2016
"""

import csv
import os
import sys

def main():

    content = {}
    for filename in sys.argv[1:]:
        reader = csv.reader(open(filename))
        fields = next(reader)
        content[filename] = {
            'fields': fields,
            'content': [set() for i in fields],
        }
        for row in reader:
            for n, col in enumerate(row):
                try:
                    content[filename]['content'][n].add(col)
                except:
                    print filename, n, row, col
                    print content[filename]
                    raise

    for table0 in content:
        for table1 in content:
            if table1 == table0:
                continue
            for n0, field0 in enumerate(content[table0]['content']):
                for n1, field1 in enumerate(content[table1]['content']):
                    if field1.issubset(field0):
                        print table1, content[table1]['fields'][n1], table0, content[table0]['fields'][n0]

if __name__ == '__main__':
    main()
