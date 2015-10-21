"""
make_testdata.py - one time run to generate test SQLite DB

Terry Brown, Terry_N_Brown@yahoo.com, Wed Oct 21 15:21:18 2015
"""

import datetime
import os
import sqlite3
import sys

TESTDB = "test_data.sqlite3"

def main():
    if not "onetimerun" in sys.argv:
        print(
            "usage: python make_testdata.py onetimerun\n\n"
            "this program shouldn't need to be run again "
            "unless the test DB needs replacing\n\n"
        )
        exit(10)

    make_db()

def make_db():

    if os.path.exists(TESTDB):
        print("'%s' already exists" % TESTDB)
        exit(10)

    con = sqlite3.connect(TESTDB)
    cur = con.cursor()
    cur.execute("""
        create table test_table_1 (
            aString text,
            anInt int,
            aFloat float,
            aDate date,
            aDateTime datetime,
            aBool boolean
        );
    """)
    for n in range(1000):
        aString = "str%06d" % n
        anInt = n
        aFloat = anInt / 1.7
        aDate = datetime.date.today()
        aDateTime = datetime.datetime.now()
        aBool = n % 2 == 0
        cur.execute("insert into test_table_1 values(?,?,?,?,?,?)",
            [aString, anInt, aFloat, aDate, aDateTime, aBool])
    con.commit()

if __name__ == '__main__':
    main()


