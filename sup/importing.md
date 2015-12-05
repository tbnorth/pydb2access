Importing exported data
=======================

Instructions form importing data exported to .xml and .xsd files for Access.

There are a number of steps which need to be followed.

1. Exported data should consist of two files, one with a `.xml`
   extension, and one with an `.xsd` extension.  There may also be
   a file called `LinkTemplate.accdb`.
2. If your exported data is a single `.zip` file, unzip it to access
   the `.xml` and `.xsd` files.
3. Create a completely new, blank database, called `datadownload.accdb`.
4. In `datadownload.accdb`, use the Import XML tool in the External data
   menu to import all the tables in the **`.xml`** file.
5. Close `datadownload.accb`
6. Make a copy of `LinkTemplate.accdb` called `analysis.accdb`.  Open
   it and enable disabled content, if any is reported.
7. In `analysis.accdb`, link to all the tables in `datadownload.accdb`
   using the **Access** DB Import option in the External data menu - make sure
   to **link**, not copy / import.
8. In `analysis.accdb`, open the `Link tables` form and click the
   `Link tables` button.  You should see a "Tables linked" message.

Now all the relationships between tables should be visible in `analysis.accdb`
in the Database Tools menu Relationships tool.

Queries etc. should be written in `analysis.accdb`.  If you need to update the
imported data, delete `datadownload.accb` and repeat **only** steps 1-5.  Queries
etc. written in `analysis.accdb` will be unaffected.

This two database, start fresh for import approach is known to work with
large databases (hundreds of thousands of records in dozens of tables)
which may give trouble with a simpler recipe, such as using only one database
and importing new data directly into it.

<!-- generate .html version with

     pandoc -H sup/importing.css -o importing.html sup/importing.md
-->

