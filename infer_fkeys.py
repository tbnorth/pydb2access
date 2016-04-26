"""
infer_fkeys.py - infer foreign key relationships by field content

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
                    # /here error is in source xml
                    print filename, n, row, col
                    print content[filename]
                    raise
        

if __name__ == '__main__':
    main()
