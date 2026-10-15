"""Disposable scheduler-service capability probe; only owned processes and files."""
import argparse,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
import psutil


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=args.output.absolute()
    root.mkdir(parents=True,exist_ok=False)
    home=root/'airflow-home';home.mkdir(exist_ok=False)
    dags=home/'dags';dags.mkdir()
    env={k:v for k,v in os.environ.items() if not(k.startswith(('AIRFLOW_','AIRFLOW_CTX_')) or k in ('HOME','PYTHONPATH','PYTHONHOME'))}
    env.update({'PATH':str(Path(sys.executable).parent)+os.pathsep+env.get('PATH',''),'HOME':str(home),'AIRFLOW_HOME':str(home),'AIRFLOW_CONFIG':str(home/'airflow.cfg'),
        'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///'+str(home/'metadata.db'),
        'AIRFLOW__CORE__DAGS_FOLDER':str(dags),'AIRFLOW__CORE__PLUGINS_FOLDER':str(home/'plugins'),'AIRFLOW__CORE__LOAD_EXAMPLES':'False',
        'AIRFLOW__CORE__EXECUTOR':'SequentialExecutor','AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION':'False',
        'AIRFLOW__CORE__EXECUTE_TASKS_NEW_PYTHON_INTERPRETER':'True','AIRFLOW__CORE__MP_START_METHOD':'spawn',
        'AIRFLOW__LOGGING__BASE_LOG_FOLDER':str(home/'logs'),'AIRFLOW__METRICS__STATSD_ON':'False',
        'AIRFLOW__SCHEDULER__MIN_FILE_PROCESS_INTERVAL':'1','AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL':'1',
        'AIRFLOW__SCHEDULER__SCHEDULER_IDLE_SLEEP_TIME':'1'})
    os.environ.clear();os.environ.update(env)
    from airflow.utils import db
    db.initdb(load_connections=False)
    target=root/'completed.json'
    code='''from airflow.decorators import dag, task
import pendulum
import json
from pathlib import Path
@dag(dag_id='owned_scheduler_probe', schedule='@once', start_date=pendulum.datetime(2026,1,14,tz='UTC'), catchup=False)
def probe():
    @task
    def build():
        return 3
    @task
    def publish(count):
        if count != 3:
            raise ValueError('synthetic count mismatch')
        Path(TARGET).write_text(json.dumps({'synthetic':True,'records':count}))
    publish(build())
probe()
'''.replace('TARGET',repr(str(target)))
    (dags/'owned_probe.py').write_text(code)
    owned={};result=None;runs=[];tasks=[]
    def remember(pid):
        try:
            parent=psutil.Process(pid)
            for child in parent.children(recursive=True):owned[child.pid]=child.create_time()
        except psutil.NoSuchProcess:pass
    with (root/'scheduler.log').open('w') as log:
        proc=subprocess.Popen([sys.executable,'-m','airflow','scheduler','--skip-serve-logs','--num-runs','200'],
                              env=env,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        owned[proc.pid]=psutil.Process(proc.pid).create_time()
        try:
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                remember(proc.pid)
                with sqlite3.connect(home/'metadata.db',timeout=1) as conn:
                    runs=conn.execute("SELECT run_id,run_type,state FROM dag_run WHERE dag_id='owned_scheduler_probe'").fetchall()
                    tasks=conn.execute("SELECT task_id,state FROM task_instance WHERE dag_id='owned_scheduler_probe' ORDER BY task_id").fetchall()
                if runs and runs[0][2] in ('success','failed'):
                    result={'execution_mode':'actual scheduler service + SequentialExecutor; @once timetable',
                            'runs':runs,'tasks':tasks,'manifest':json.loads(target.read_text()) if target.exists() else None}
                    break
                if proc.poll() is not None:raise RuntimeError('scheduler exited before terminal DAG run')
                time.sleep(1)
            if result is None:raise TimeoutError('scheduler probe exceeded120seconds')
            assert result['runs'][0][1:] == ('scheduled','success'),result
            assert result['tasks']==[('build','success'),('publish','success')],result
            assert result['manifest']=={'synthetic':True,'records':3},result
        finally:
            remember(proc.pid)
            if proc.poll() is None:proc.terminate()
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            remaining=[]
            for pid,created in owned.items():
                try:
                    p=psutil.Process(pid)
                    if p.create_time()==created and p.is_running() and p.status()!=psutil.STATUS_ZOMBIE:
                        p.terminate();remaining.append(p)
                except psutil.NoSuchProcess:pass
            _,alive=psutil.wait_procs(remaining,timeout=5)
            for p in alive:p.kill()
            psutil.wait_procs(alive,timeout=5)
            still=[]
            for pid,created in owned.items():
                try:
                    p=psutil.Process(pid)
                    if p.create_time()==created and p.is_running() and p.status()!=psutil.STATUS_ZOMBIE:still.append(pid)
                except psutil.NoSuchProcess:pass
            (root/'cleanup.json').write_text(json.dumps({'owned_processes_observed':len(owned),'owned_processes_remaining':still},indent=2)+'\n')
            (root/'last-observation.json').write_text(json.dumps({'runs':runs,'tasks':tasks},indent=2)+'\n')
            if still:raise RuntimeError('owned process cleanup incomplete')
    (root/'output.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
