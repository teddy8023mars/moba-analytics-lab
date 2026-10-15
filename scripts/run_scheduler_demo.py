"""Bounded native Linux Airflow scheduler demo; synthetic local artifacts only."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('clean', 'bad_metrics')


def owned_environment(output, inherited):
    home = output/'airflow-home'
    env = {k:v for k,v in inherited.items()
           if not k.startswith('AIRFLOW_') and k not in ('HOME','PYTHONPATH','PYTHONHOME')}
    env.update({
        'HOME':str(home), 'AIRFLOW_HOME':str(home), 'AIRFLOW_CONFIG':str(home/'airflow.cfg'),
        'PATH':str(Path(sys.executable).parent)+os.pathsep+env.get('PATH',''),
        'PYTHONPATH':str(ROOT/'src'),
        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///'+str(home/'metadata.db'),
        'AIRFLOW__CORE__DAGS_FOLDER':str(home/'dags'),
        'AIRFLOW__CORE__PLUGINS_FOLDER':str(home/'plugins'),
        'AIRFLOW__CORE__LOAD_EXAMPLES':'False',
        'AIRFLOW__CORE__EXECUTOR':'SequentialExecutor',
        'AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION':'False',
        'AIRFLOW__CORE__EXECUTE_TASKS_NEW_PYTHON_INTERPRETER':'True',
        'AIRFLOW__CORE__MP_START_METHOD':'spawn',
        'AIRFLOW__LOGGING__BASE_LOG_FOLDER':str(home/'logs'),
        'AIRFLOW__METRICS__STATSD_ON':'False',
        'AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL':'1',
        'AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL':'1',
        'AIRFLOW__SCHEDULER__SCHEDULER_IDLE_SLEEP_TIME':'1',
    })
    return env


def remember(proc, identities):
    import psutil
    try:
        parent = psutil.Process(proc.pid)
        if parent.create_time() != identities.get(proc.pid):
            return
        for child in parent.children(recursive=True):
            identities[child.pid] = child.create_time()
    except psutil.NoSuchProcess:
        pass


def cleanup_owned(proc, identities):
    """Only observed PID+creation-time matches; never search unrelated processes."""
    import psutil
    remember(proc, identities)
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait(timeout=5)
    tracked = []
    for pid, created in identities.items():
        try:
            process = psutil.Process(pid)
            if process.create_time()==created and process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:
                process.terminate(); tracked.append(process)
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(tracked, timeout=5)
    for process in alive:
        try: process.kill()
        except psutil.NoSuchProcess: pass
    psutil.wait_procs(alive, timeout=5)
    remaining = []
    for pid, created in identities.items():
        try:
            process = psutil.Process(pid)
            if process.create_time()==created and process.is_running() and process.status()!=psutil.STATUS_ZOMBIE:
                remaining.append(pid)
        except psutil.NoSuchProcess:
            pass
    return {'owned_processes_observed':len(identities), 'owned_processes_remaining':remaining}


def observe(database):
    results = {}
    with sqlite3.connect(database, timeout=1) as conn:
        for scenario in SCENARIOS:
            dag_id = 'moba_scheduled_'+scenario
            runs = conn.execute('SELECT run_id,run_type,state FROM dag_run WHERE dag_id=?', (dag_id,)).fetchall()
            tasks = conn.execute('SELECT task_id,state FROM task_instance WHERE dag_id=?', (dag_id,)).fetchall()
            results[scenario] = {'runs':runs, 'tasks':dict(tasks)}
    return results


def check_results(output, results):
    from moba_lab.artifacts import verify_manifest
    for scenario, result in results.items():
        wanted = dict(generate_fixture='success', build_metrics='success',
                      validate_metrics='success', publish_local='success')
        state = 'success'
        if scenario=='bad_metrics':
            wanted.update(validate_metrics='failed', publish_local='upstream_failed'); state='failed'
        if len(result['runs'])!=1 or tuple(result['runs'][0][1:])!=('scheduled',state) or result['tasks']!=wanted:
            raise RuntimeError(f'{scenario}: unexpected scheduler/task states: {result}')
        manifest = output/scenario/'published.json'
        if scenario=='bad_metrics':
            if manifest.exists(): raise RuntimeError('invalid metrics were published')
        else:
            checked = verify_manifest(manifest)
            if checked['counts']!=dict(user_day=101,dau=14,retention=8,hero_stats=3,player_stats=12,monetization=4) or checked['revenue_cents']!=1396:
                raise RuntimeError('canonical synthetic totals mismatch')
            result['verification'] = checked


def run_demo(output, timeout=180):
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('use a fresh output path; existing files and directories are never overwritten')
    if not 0 < timeout <= 300:
        raise ValueError('timeout must be positive and at most 300 seconds')
    if sys.platform != 'linux':
        raise RuntimeError('native scheduler demo requires Linux; use run_airflow_demo.py for DAG.test on macOS')
    version = importlib.metadata.version('apache-airflow')
    if version != '2.11.0': raise RuntimeError('requires pinned Airflow 2.11.0')
    import psutil
    output.mkdir(parents=True, exist_ok=False)
    env = owned_environment(output, os.environ)
    home = output/'airflow-home'; dags = home/'dags'; dags.mkdir(parents=True)
    # Initialization is a separate bounded process; this controller never imports Airflow.
    with (output/'init.log').open('w') as log:
        subprocess.run([sys.executable,'-c','from airflow.utils import db; db.initdb(load_connections=False)'],
                       cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60, check=True)
    source = ('import sys\nimport pendulum\n'
              f'sys.path.insert(0, {str(ROOT/"orchestration")!r})\n'
              'from moba_dag import make_dag\n')
    for scenario in SCENARIOS:
        source += (f'{scenario}_dag = make_dag({str(output/scenario)!r}, {scenario!r}, '
                   f'dag_id={"moba_scheduled_"+scenario!r}, schedule="@once", '
                   'start_date=pendulum.datetime(2026,1,14,tz="UTC"))\n')
    (dags/'scheduled_moba.py').write_text(source)
    results = {}; cleanup = None
    with (output/'scheduler.log').open('w') as log:
        proc = subprocess.Popen([sys.executable,'-m','airflow','scheduler','--skip-serve-logs','--num-runs','300'],
                                cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        identities = {proc.pid:psutil.Process(proc.pid).create_time()}
        try:
            deadline = time.monotonic()+timeout
            while time.monotonic()<deadline:
                remember(proc, identities)
                results = observe(home/'metadata.db')
                if all(len(r['runs'])==1 and r['runs'][0][2] in ('success','failed') for r in results.values()):
                    break
                if proc.poll() is not None: raise RuntimeError('scheduler exited before terminal runs')
                time.sleep(min(0.5, max(0, deadline-time.monotonic())))
            else:
                raise TimeoutError('scheduler deadline exceeded')
            check_results(output, results)
        finally:
            cleanup = cleanup_owned(proc, identities)
            (output/'cleanup.json').write_text(json.dumps(cleanup,indent=2)+'\n')
            (output/'last-observation.json').write_text(json.dumps(results,indent=2)+'\n')
            if cleanup['owned_processes_remaining']: raise RuntimeError('owned cleanup incomplete')
    summary = {'airflow_version':version,
               'execution_mode':'native Linux scheduler + SequentialExecutor; two @once synthetic DAGs',
               'scope':'bounded local experiment; no recurring uptime, cloud or HA deployment',
               'scenarios':results, 'cleanup':cleanup}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=180, help='scheduler observation deadline in seconds (0..300)')
    args = parser.parse_args()
    print(json.dumps(run_demo(args.output, args.timeout), indent=2))
