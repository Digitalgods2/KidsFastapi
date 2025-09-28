#!/usr/bin/env python3
import sqlite3, json, os, pathlib

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///./kidsklassiks.db')
path = DB_URL
if DB_URL.startswith('sqlite:////'):
    path = '/' + DB_URL[len('sqlite:////'):]
elif DB_URL.startswith('sqlite:///'):
    path = os.path.abspath(DB_URL[len('sqlite:///'):])

conn = sqlite3.connect(path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
tables = [r[0] for r in cur.fetchall()]
export = {}
for t in tables:
    cur.execute(f'SELECT * FROM {t}')
    rows = cur.fetchall()
    export[t] = [dict(r) for r in rows]

out = pathlib.Path('backups/sqlite_export.json')
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(export, indent=2, default=str))
print(f'Exported JSON: {out}')
