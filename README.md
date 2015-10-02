# pydb2access.py - Convert a PEP 249 DB to MS Access

``pydb2access.py`` connects to a database (Postgresql or SQLite currently)
and dumps data into an .xml file and schema (table structure) into an .xsd
file.  This pair of files can be read by Microsoft Access with correct
column types etc.

``pydb2access.py`` also creates a table (Postgresql only) ``_LOOKUPS`` which
lists the relationships (foreign keys) in the database.  XML-Schema (.xsd) files
are capable of representing this information, but a long web search only
yielded an answer saying that Access does not utilize such information.  So instead,
the relationships can be re-created in the Access file with the the ``_LOOKUPS``
table and the Access in [relink.tables.vb](./relink.tables.vb).

## --exclude-types

Some types, e.g. geometry types (GIS polygons etc.) can't be exported, use
``--exclude-types`` with a list of type codes to suppress exporting of
these types.  Run ``pydb2access.py`` with ``--show-types`` to get a list
of type codes seen in the database, or in the subset of tables specified
with ``--tables``.

Command line::

    positional arguments:
      output                base name for output folder for .xml and .xsd files

    optional arguments:
      -h, --help            show this help message and exit
      --tables TABLES [TABLES ...]
                            list of tables to include, omit for all
      --exclude-tables EXCLUDE_TABLES [EXCLUDE_TABLES ...]
                            list of tables to exclude
      --exclude-types EXCLUDE_TYPES [EXCLUDE_TYPES ...]
                            list of types to exclude, get numbers using --show-
                            types
      --module MODULE       name of DB API module, 'sqlite3' or 'psycopg2' for
                            PostgreSQL
      --prefix PREFIX       prefix for all exported table names, e.g. 'myschema_'
      --schema SCHEMA       PostgreSQL schema (i.e. namespace)
      --limit LIMIT         max. rows to output, per table, for testing
      --show-tables         Just show list of table names and exit
      --show-types          Just show list of types names and exit
      --sort-fields         Order fields alphabetically
      --top-id              Order fields alphabetically, but place fields with the
                            same name as the table first
      --dsn DSN             Data source name as string
      --user USER           User name as string
      --password PASSWORD   Password as string, 'prompt' for prompt
      --host HOST           Hostname
      --database DATABASE   Database name
