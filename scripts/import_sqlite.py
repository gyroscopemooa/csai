"""Offline SQLite -> private PostgreSQL import. Dry run by default.

Stop writes to both databases, take a verified source backup, initialize the
target schema with this branch, then dry-run. Never merges or overwrites rows.
The source must be a SQLite backup, not a live application database.
"""
import argparse,os,re,sqlite3,sys
from pathlib import Path
from postgres_store import connect,SCHEMA,checked_name

def tables(src):
    return [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]

def ordered(src,names):
    pending=set(names);done=[]
    parents={n:{r[2] for r in src.execute('PRAGMA foreign_key_list('+checked_name(n)+')')} & pending for n in names}
    while pending:
        ready=sorted(n for n in pending if not parents[n]&pending)
        if not ready:raise RuntimeError('Foreign key cycle: manual migration required')
        done.extend(ready);pending.difference_update(ready)
    return done

def transfer(src,raw,apply=False):
    target={}
    for row in raw.execute("SELECT table_name,column_name,is_identity FROM information_schema.columns WHERE table_schema=%s ORDER BY ordinal_position",(SCHEMA,)):
        target.setdefault(row['table_name'],{})[row['column_name']]=row['is_identity']
    names=tables(src)
    if not {'workspace','thread','message','training'}.issubset(names):raise RuntimeError('Not a CS AI source database')
    if not set(names)<=set(target):raise RuntimeError('Target schema must be initialized with this branch; missing tables: '+', '.join(sorted(set(names)-set(target))))
    for n in target:
        if raw.execute('SELECT 1 FROM '+checked_name(n)+' LIMIT 1').fetchone():raise RuntimeError('Target contains existing data: '+n)
    if src.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('SQLite integrity check failed')
    if src.execute('PRAGMA foreign_key_check').fetchone():raise RuntimeError('SQLite contains invalid foreign keys; repair backup first')
    order=ordered(src,names)
    count=0
    for n in order:
        q=checked_name(n)
        fields=[r[1] for r in src.execute('PRAGMA table_info('+q+')')]
        if not set(fields)<=set(target[n]):raise RuntimeError('Unexpected source columns: '+n)
        preserve='rowid' in target[n] and 'rowid' not in fields
        select='SELECT '+('rowid,' if preserve else '')+','.join(checked_name(f) for f in fields)+' FROM '+q
        if preserve:fields=['rowid']+fields;select+=' ORDER BY rowid'
        expected=src.execute('SELECT count(*) FROM '+q).fetchone()[0]
        if apply:
            sql='INSERT INTO '+q+' ('+','.join(checked_name(f) for f in fields)+') VALUES ('+','.join(['%s']*len(fields))+')'
            cursor=src.execute(select)
            with raw.cursor() as dst:
                while True:
                    batch=cursor.fetchmany(500)
                    if not batch:break
                    dst.executemany(sql,batch)
            actual=raw.execute('SELECT count(*) AS n FROM '+q).fetchone()['n']
            if actual!=expected:raise RuntimeError('Row-count mismatch: '+n)
            if preserve and expected:
                seq=raw.execute('SELECT pg_get_serial_sequence(%s,%s) AS seq',(SCHEMA+'.'+n,'rowid')).fetchone()['seq']
                if not seq:raise RuntimeError('Missing identity sequence: '+n)
                maximum=raw.execute('SELECT MAX(rowid) AS n FROM '+q).fetchone()['n']
                raw.execute('SELECT setval(%s::regclass,%s,true)',(seq,maximum))
        print(n+': '+str(expected)+' rows')
        count+=expected
    print(('Imported and verified ' if apply else 'Dry run: eligible ')+str(count)+' rows across '+str(len(order))+' tables.')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,help='Path to an offline SQLite backup')
    p.add_argument('--apply',action='store_true',help='Write only into an empty initialized target')
    p.add_argument('--confirmed-offline-backup',action='store_true')
    a=p.parse_args()
    if a.apply and not a.confirmed_offline_backup:p.error('Apply requires --confirmed-offline-backup')
    path=Path(a.source).resolve(strict=True)
    if not path.is_file():p.error('Source must be a file')
    dsn=os.getenv('DATABASE_URL','')
    src=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        src.execute('BEGIN')
        with connect(dsn,write=a.apply) as dst:transfer(src,dst.raw,apply=a.apply)
    finally:src.close()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Do not print a connection URL, customer records or provider secrets.
        print('Migration stopped: '+type(exc).__name__,file=sys.stderr)
        if isinstance(exc,RuntimeError):print(str(exc),file=sys.stderr)
        sys.exit(1)
