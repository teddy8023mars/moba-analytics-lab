"""Build actual dbt models, reconcile metrics and prove a singular test detects corruption."""
import argparse
from datetime import date
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import duckdb
from moba_lab.pipeline import SCHEMAS, KEYS, METRICS, _validated, run_pipeline

ROOT = Path(__file__).resolve().parents[1]


def run_demo(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    database = output / 'warehouse.duckdb'
    # Avoid overwriting an existing warehouse or unrelated tables.
    if database.exists():
        raise ValueError('output warehouse exists; use a new output directory')
    data = json.loads((ROOT / 'examples/fixture.json').read_text())
    clean = _validated(data)
    with duckdb.connect(str(database)) as con:
        con.execute("SET TimeZone='UTC'")
        for table, schema in SCHEMAS.items():
            con.execute(f"CREATE TABLE raw_{table} ({', '.join(f'{f} {t}' for f,t in schema)})")
            by_key = {tuple(r[k] for k in KEYS[table]): r for r in clean[table]}
            rows = [by_key[tuple(r[k] for k in KEYS[table])] for r in data[table]]
            if rows:
                con.executemany(f"INSERT INTO raw_{table} VALUES ({','.join('?' for _ in schema)})",
                                [tuple(r[f] for f,_ in schema) for r in rows])
    env = {**os.environ, 'MOBA_DBT_DATABASE': str(database), 'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'}
    dbt = Path(sys.executable).parent / ('dbt.exe' if os.name == 'nt' else 'dbt')

    def invoke(command, label, as_of='2026-01-14', select=None):
        args = [str(dbt), '--log-path', str(output / 'logs'), command,
                '--project-dir', str(ROOT / 'dbt'), '--profiles-dir', str(ROOT / 'dbt'),
                '--target-path', str(output / 'target'), '--vars', json.dumps({'as_of': as_of})]
        if select:
            args += ['--select', select]
        result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=120)
        (output / (label+'.log')).write_text(result.stdout + result.stderr)
        if result.returncode not in (0,1):
            raise RuntimeError(f'{label}: dbt exited {result.returncode}; see log')
        artifacts = json.loads((output / 'target/run_results.json').read_text())
        (output / (label+'-results.json')).write_text(json.dumps(artifacts, indent=2)+'\n')
        return result.returncode, artifacts

    def metrics():
        with duckdb.connect(str(database), read_only=True) as con:
            answer = {}
            for name in METRICS:
                cur = con.execute(f'SELECT * FROM analytics.{name} ORDER BY 1,2')
                columns = [c[0] for c in cur.description]
                answer[name] = [dict(zip(columns, [v.isoformat() if isinstance(v,date) else v for v in row])) for row in cur.fetchall()]
            return answer

    code, built = invoke('build', 'clean-build')
    if code != 0:
        raise RuntimeError('clean dbt build failed; see clean-build.log')
    full = metrics()
    if full != run_pipeline(data, '2026-01-14'):
        raise AssertionError('dbt/canonical metric mismatch')
    with duckdb.connect(str(database)) as con:
        con.execute("UPDATE analytics.retention SET retained_users=cohort_users+1 WHERE cohort_date=DATE '2026-01-01' AND day_offset=1")
    bad_code, bad = invoke('test', 'corrupt-retention', select='retention_invariants')
    failures = sum(r.get('failures') or 0 for r in bad['results'])
    if bad_code != 1 or failures != 1 or [r['status'] for r in bad['results']] != ['fail']:
        raise AssertionError('deliberate retained-count corruption was not detected')
    restored, _ = invoke('build', 'restored-build')
    if restored != 0 or metrics() != full:
        raise AssertionError('rebuild did not restore clean marts')
    earlier, _ = invoke('build', 'earlier-cutoff-build', as_of='2026-01-08')
    small = metrics()
    if earlier != 0 or small != run_pipeline(data, '2026-01-08'):
        raise AssertionError('earlier cutoff mismatch')
    summary = {'as_of':'2026-01-14','row_counts':{k:len(v) for k,v in full.items()},
               'jan1_retention':[[r['day_offset'],r['cohort_users'],r['retained_users']] for r in full['retention'] if r['cohort_date']=='2026-01-01'],
               'revenue_cents':sum(r['revenue_cents'] for r in full['monetization']),
               'earlier_cutoff_retention_rows':len(small['retention']), 'all_marts_match_canonical':True,
               'bad_retention_test_exit':bad_code,'bad_retention_failures':failures,'restored_test_exit':restored,
               'models_built':sum(r['unique_id'].startswith('model.') for r in built['results']),
               'data_tests_passed':sum(r['unique_id'].startswith('test.') and r['status']=='pass' for r in built['results']),
               'versions':{p:importlib.metadata.version(p) for p in ('dbt-core','dbt-duckdb','duckdb')}}
    (output / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output), indent=2))
