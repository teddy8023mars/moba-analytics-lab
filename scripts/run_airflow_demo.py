"""Own isolated local Airflow homes; exercise actual DAG.test and persist real states."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('clean','transient','bad_metrics')


def worker(output,scenario):
    # Parent sets isolation before this child imports any Airflow module.
    home=output/'airflow-home'
    if (os.environ.get('AIRFLOW_HOME')!=str(home)
        or os.environ.get('AIRFLOW_CONFIG')!=str(home/'airflow.cfg')
        or os.environ.get('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN')!='sqlite:///'+str(home/'metadata.db')):
        raise ValueError('worker requires the wrapper-owned isolated Airflow configuration')
    import pendulum
    from airflow.utils import db
    from airflow.utils.session import create_session
    sys.path.insert(0,str(ROOT/'orchestration'))
    from moba_dag import make_dag
    db.initdb(load_connections=False)
    dag=make_dag(output/'artifacts',scenario)
    run=dag.test(execution_date=pendulum.datetime(2026,1,14,tz='UTC'),use_executor=False)
    with create_session() as session:
        tasks={ti.task_id:ti.state for ti in run.get_task_instances(session=session)}
    artifact=output/'artifacts/published.json'
    manifest=json.loads(artifact.read_text()) if artifact.exists() else None
    attempts=[json.loads(line)['attempt'] for line in (output/'artifacts/build-attempts.jsonl').read_text().splitlines()]
    result={'state':run.state,'tasks':tasks,'build_attempts':len(attempts),'attempt_numbers':attempts,
            'published':manifest is not None,'published_counts':manifest['counts'] if manifest else None,
            'published_revenue_cents':manifest['revenue_cents'] if manifest else None}
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')


def run_demo(output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=True)
    if any((output/scenario).exists() for scenario in SCENARIOS) or (output/'summary.json').exists():
        raise ValueError('use a fresh output directory; existing scenarios are never overwritten')
    results={}
    for scenario in SCENARIOS:
        folder=output/scenario;folder.mkdir()
        home=folder/'airflow-home'
        inherited={key:value for key,value in os.environ.items()
                   if not (key in ('AIRFLOW_HOME','AIRFLOW_CONFIG')
                           or key.startswith(('AIRFLOW__','AIRFLOW_CTX_')))}
        env={**inherited,'AIRFLOW_HOME':str(home),'AIRFLOW_CONFIG':str(home/'airflow.cfg'),
             'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///'+str(home/'metadata.db'),
             'AIRFLOW__CORE__EXECUTOR':'SequentialExecutor','AIRFLOW__CORE__LOAD_EXAMPLES':'False',
             'AIRFLOW__CORE__UNIT_TEST_MODE':'True','AIRFLOW__CORE__DAGS_FOLDER':str(ROOT/'orchestration'),
             'AIRFLOW__LOGGING__BASE_LOG_FOLDER':str(home/'logs'),'AIRFLOW__METRICS__STATSD_ON':'False',
             'AIRFLOW__CORE__TEST_CONNECTION':'Disabled'}
        proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',scenario,'--output',str(folder)],
                            env=env,capture_output=True,text=True,timeout=120)
        (folder/'worker.log').write_text(proc.stdout+proc.stderr)
        if proc.returncode:
            raise RuntimeError(f'{scenario} worker exit {proc.returncode}; see {folder.name}/worker.log')
        result=json.loads((folder/'result.json').read_text())
        wanted={'generate_fixture':'success','build_metrics':'success','validate_metrics':'success','publish_local':'success'}
        if scenario=='bad_metrics':wanted.update(validate_metrics='failed',publish_local='upstream_failed')
        if result['tasks']!=wanted or result['state']!=('failed' if scenario=='bad_metrics' else 'success'):
            raise AssertionError(f'{scenario} unexpected Airflow states: {result}')
        if result['attempt_numbers']!=([1,2] if scenario=='transient' else [1]):
            raise AssertionError('native Airflow attempt sequence mismatch')
        if result['published']!=(scenario!='bad_metrics'):
            raise AssertionError('local publication gate failed')
        results[scenario]=result
    summary={'airflow_version':importlib.metadata.version('apache-airflow'),
             'execution_mode':'actual DAG.test; serialized local tasks, no scheduler/executor service',
             'metadata':'fresh SQLite database and AIRFLOW_HOME per scenario','scenarios':results}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--worker',choices=SCENARIOS,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:worker(args.output.resolve(),args.worker)
    else:print(json.dumps(run_demo(args.output),indent=2))
