"""Metadata-only row_hash maintenance; check-only unless explicitly approved.

Never rewrites raw business fields, audit counters, or a non-NULL hash. Does not
reset, reload, launch Mage/dbt, or fill action counts. PRIMARY apply is a separate
maintenance approval after migration and verified backup, not ordinary logging.
"""
import argparse
import json
from pathlib import Path
import sys
import pyodbc

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from mage_project.amazon_delivery_contract import HASH_COLUMNS, compute_raw_row_hash


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--environment',choices=['TEST','PRIMARY'],required=True)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--approval',default='')
    args=p.parse_args()
    if args.apply and args.approval!='APPROVED_'+args.environment+'_HASH_BASELINE':
        p.error('Separate explicit hash-baseline approval required')
    database='AmazonDeliveryBI_TEST' if args.environment=='TEST' else 'AmazonDeliveryBI'
    c=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost\\SQLEXPRESS;'
                     f'DATABASE={database};Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;',
                     autocommit=False,timeout=5)
    try:
        c.execute('SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000; SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;')
        row=c.execute("""SELECT DB_NAME(),CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')),
            CONVERT(nvarchar(128),(SELECT value FROM sys.extended_properties WHERE class=0 AND name='ETLMonitoring.Environment'))""").fetchone()
        if tuple(row)!=(database,r'DESKTOP-OBDFK6B\SQLEXPRESS','APPROVED_'+args.environment):
            raise RuntimeError('Explicit migrated target/environment marker required')
        columns=','.join('['+n+']' for n in HASH_COLUMNS)
        lock=' WITH(TABLOCKX,HOLDLOCK)' if args.apply else ''
        rows=c.execute('SELECT staging_row_id,'+columns+',row_hash FROM staging.raw_amazon_delivery'+lock).fetchall()
        pending=[];mismatches=0
        for r in rows:
            measured=compute_raw_row_hash(list(r[1:-1]))
            if r[-1] is None:pending.append((measured,r[0]))
            elif r[-1].lower()!=measured:mismatches+=1
        if mismatches:raise RuntimeError(f'{mismatches} non-NULL hashes differ; no automatic overwrite')
        if args.apply:
            cursor=c.cursor()
            if pending:
                cursor.executemany('UPDATE staging.raw_amazon_delivery SET row_hash=? WHERE staging_row_id=? AND row_hash IS NULL',pending)
            c.commit()
        else:c.rollback()
        print(json.dumps(dict(environment=args.environment,mode='apply' if args.apply else 'check-only',rows=len(rows),
                              null_hashes=len(pending),non_null_mismatches=mismatches,applied=len(pending) if args.apply else 0)))
    except BaseException:
        c.rollback()
        raise
    finally:c.close()


if __name__=='__main__':main()
