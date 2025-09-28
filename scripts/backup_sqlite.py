#!/usr/bin/env python3
import sqlite3, os, time, pathlib

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///./kidsklassiks.db')
path = DB_URL
if DB_URL.startswith('sqlite:////'):
    path = '/' + DB_URL[len('sqlite:////'):]
elif DB_URL.startswith('sqlite:///'):
    path = os.path.abspath(DB_URL[len('sqlite:///'):])

src_path = pathlib.Path(path)
backup_dir = pathlib.Path('backups')
backup_dir.mkdir(exist_ok=True)
ts = time.strftime('%Y%m%d-%H%M%S')
dst_path = backup_dir / f'kidsklassiks-{ts}.db'

with sqlite3.connect(src_path) as src, sqlite3.connect(dst_path) as dst:
    src.backup(dst)
print(f'Backup created: {dst_path}')
