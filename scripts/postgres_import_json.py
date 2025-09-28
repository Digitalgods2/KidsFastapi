#!/usr/bin/env python3
import os, json, psycopg2
from psycopg2.extras import execute_values

DATA = json.load(open('backups/sqlite_export.json'))
PG_DSN = os.getenv('PG_DSN') or (
    f"host={os.getenv('DB_HOST','localhost')} port={os.getenv('DB_PORT','5432')} "
    f"dbname={os.getenv('DATABASE_NAME','kidsklassiks')} user={os.getenv('DB_USER','glen')} password={os.getenv('DB_PASSWORD','')}"
)
conn = psycopg2.connect(PG_DSN)
cur = conn.cursor()

for table, rows in DATA.items():
    if not rows:
        continue
    cols = list(rows[0].keys())
    values = [[r.get(c) for c in cols] for r in rows]
    cols_sql = ','.join(cols)
    placeholders = '(' + ','.join(['%s']*len(cols)) + ')'
    execute_values(cur, f'INSERT INTO {table} ({cols_sql}) VALUES %s ON CONFLICT DO NOTHING', values)
    conn.commit()

print('Import complete.')
