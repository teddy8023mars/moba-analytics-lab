"""Factory for a local, manually tested Airflow DAG; no scheduler deployment."""
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import pendulum
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException, AirflowFailException
from airflow.operators.python import get_current_context
from moba_lab.fixtures import generate_fixture
from moba_lab.pipeline import run_pipeline


def atomic_json(path, value):
    path=Path(path)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)
    return str(path)


def make_dag(folder, scenario):
    folder=Path(folder).resolve()
    if scenario not in ('clean','transient','bad_metrics'):
        raise ValueError('unknown scenario')
    folder.mkdir(parents=True,exist_ok=True)

    @dag(dag_id='moba_portfolio_local',schedule=None,catchup=False,
         start_date=pendulum.datetime(2026,1,1,tz='UTC'),max_active_runs=1,
         default_args={'owner':'portfolio','retries':0},tags=['synthetic','local-demo'])
    def pipeline():
        @task
        def generate_fixture_task():
            return atomic_json(folder/'fixture.json',generate_fixture(7))

        @task(retries=1,retry_delay=timedelta(0))
        def build_metrics_task(fixture_path):
            ti=get_current_context()['ti']
            with (folder/'build-attempts.jsonl').open('a') as stream:
                stream.write(json.dumps({'attempt':ti.try_number})+'\n')
            marker=folder/'transient-injected'
            if scenario=='transient' and not marker.exists():
                marker.write_text('owned local one-time failure\n')
                raise AirflowException('synthetic temporary failure before metrics write')
            metrics=run_pipeline(json.loads(Path(fixture_path).read_text()),'2026-01-14')
            if scenario=='bad_metrics':
                row=metrics['retention'][0]
                row['retained_users']=row['cohort_users']+1
            return atomic_json(folder/'metrics.json',metrics)

        @task
        def validate_metrics_task(metrics_path):
            metrics=json.loads(Path(metrics_path).read_text())
            expected={'user_day':101,'dau':14,'retention':8,'hero_stats':3,'player_stats':12,'monetization':4}
            counts={key:len(value) for key,value in metrics.items()}
            if counts!=expected or sum(r['revenue_cents'] for r in metrics['monetization'])!=1396:
                raise AirflowFailException('synthetic fixture expected totals mismatch')
            for row in metrics['retention']:
                cohort=row['cohort_users'];retained=row['retained_users'];offset=row['day_offset']
                if (cohort<=0 or not 0<=retained<=cohort or offset not in (1,7)
                    or date.fromisoformat(row['cohort_date'])+timedelta(days=offset)>date(2026,1,14)
                    or abs(row['retention_rate']-retained/cohort)>1e-12):
                    raise AirflowFailException('retention invariant violated; publication blocked')
            return metrics_path

        @task
        def publish_local_task(metrics_path):
            path=Path(metrics_path);metrics=json.loads(path.read_text())
            return atomic_json(folder/'published.json',{
                'scope':'synthetic local artifact; not website or production deployment',
                'metrics_file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'counts':{key:len(value) for key,value in metrics.items()},
                'revenue_cents':sum(r['revenue_cents'] for r in metrics['monetization'])})

        generated=generate_fixture_task.override(task_id='generate_fixture')()
        built=build_metrics_task.override(task_id='build_metrics')(generated)
        checked=validate_metrics_task.override(task_id='validate_metrics')(built)
        publish_local_task.override(task_id='publish_local')(checked)

    return pipeline()
