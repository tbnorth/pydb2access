export_db () {

  # invoke pydb2access.py to export data, zip it, and scp it

  TS=$1
  SCHEMA=$2
  DSN=$3
  DEST=$4

  # type 29555946 is a geometry type

  python pydb2access/pydb2access.py \
    --module psycopg2 \
    --exclude-types 29555946 \
    --exclude-tables userlog \
    --dsn "$DSN" \
    --top-id \
    --schema $SCHEMA \
    /tmp/$SCHEMA$TS

  OWD="$(pwd)"
  cd /tmp
  zip -r $SCHEMA$TS.zip $SCHEMA$TS
  cd "$OWD"

  scp /tmp/$SCHEMA$TS.zip example.com:/home/user/exports/$SCHEMA/"$SCHEMA"_Access.zip

  rm -rf /tmp/$SCHEMA$TS.zip /tmp/$SCHEMA$TS

}

TS=$(date '+%Y%m%d%H%M')

# export three sets of data, from two databases
export_db $TS clockparts "dbname=busbot host=srv1.example.com port=5432"
export_db $TS sprockets  "dbname=busbot host=srv1.example.com port=5432"
export_db $TS weather    "dbname=metinf host=127.0.0.1 port=15432"
