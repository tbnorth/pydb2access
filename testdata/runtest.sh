python ../pydb2access.py --module sqlite3 --database test_data.sqlite3 test_out
echo
git status
echo
echo git should not report a change in test_out/test_out.*
echo

