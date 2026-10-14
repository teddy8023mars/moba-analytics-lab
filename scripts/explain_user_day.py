"""Reproduce a tiny DISTINCT plan; this is explanatory, not the scale benchmark."""
import argparse
from pathlib import Path
import duckdb
from benchmark_pipeline import workload

SQL='SELECT DISTINCT CAST(occurred_at AS DATE) activity_date, user_id FROM raw_logins'

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    with duckdb.connect(':memory:') as con:
        con.execute("SET TimeZone='UTC'")
        con.execute('CREATE TABLE raw_logins(event_id VARCHAR,user_id VARCHAR,occurred_at TIMESTAMPTZ)')
        con.executemany('INSERT INTO raw_logins VALUES(?,?,?)',
                        [(r['event_id'],r['user_id'],r['occurred_at']) for r in workload(4)['logins']])
        text='EXPLAIN ANALYZE '+SQL+'\n\n'+con.execute('EXPLAIN ANALYZE '+SQL).fetchone()[1]+'\n'
    if args.output:
        args.output.write_text(text)
    print(text,end='')
