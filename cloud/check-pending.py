import sqlite3,sys
db=sqlite3.connect(sys.argv[1]);pending=db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','dispatched','running')").fetchone()[0]
if pending: print('A restart action is pending; no update performed.')
sys.exit(1 if pending else 0)
