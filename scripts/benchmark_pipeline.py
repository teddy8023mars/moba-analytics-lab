"""Bounded POSIX benchmark of the unchanged canonical full-rebuild pipeline."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import time
import duckdb
from moba_lab.pipeline import run_pipeline


def workload(users):
    if type(users) is not int or users <= 0 or users > 20000 or users % 4:
        raise ValueError('users must be a positive multiple of 4, at most 20000')
    data={k:[] for k in ('users','logins','matches','participants','payments')}
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    stamps=[(start+timedelta(days=d,hours=9)).isoformat() for d in range(14)]
    for n in range(users):
        user=f'user-{n}'
        data['users'].append({'user_id':user,'signup_at':start.isoformat()})
        for day,stamp in enumerate(stamps):
            data['logins'].append({'event_id':f'login-{n}-{day}','user_id':user,'occurred_at':stamp})
        data['logins'].append(dict(data['logins'][-14]))
        for day,cents in [(1,199),(2,999)]:
            data['payments'].append({'payment_id':f'pay-{n}-{day}','user_id':user,
                                     'occurred_at':stamps[day],'amount_cents':cents})
        data['payments'].append(dict(data['payments'][-2]))
    for group in range(users//4):
        for day in (3,4):
            match=f'match-{group}-{day}'
            data['matches'].append({'match_id':match,'started_at':stamps[day],'duration_seconds':900})
            for position in range(4):
                data['participants'].append({'match_id':match,'user_id':f'user-{group*4+position}',
                    'hero':'Ember','won':position<2,'kills':2,'deaths':1,'assists':3})
    return data


def check_metrics(metrics,users):
    observed={'user_days':len(metrics['user_day']),'dau_per_day':users,'retention_rows':len(metrics['retention']),
              'revenue_cents':sum(r['revenue_cents'] for r in metrics['monetization']),
              'transactions':sum(r['transactions'] for r in metrics['monetization'])}
    if observed!={'user_days':14*users,'dau_per_day':users,'retention_rows':2,
                  'revenue_cents':1198*users,'transactions':2*users}:
        raise AssertionError('workload closed-form totals mismatch')
    if len(metrics['dau'])!=14 or any(r['dau']!=users for r in metrics['dau']):
        raise AssertionError('DAU mismatch')
    expected=[{'cohort_date':'2026-01-01','day_offset':d,'cohort_users':users,'retained_users':users,'retention_rate':1.0} for d in (1,7)]
    if metrics['retention']!=expected:
        raise AssertionError('retention mismatch')
    if len(metrics['player_stats'])!=users or any(r['player_matches']!=2 for r in metrics['player_stats']):
        raise AssertionError('player-match grain mismatch')
    return observed


def sample(users, profile_stages=False):
    data=workload(users)
    timings={} if profile_stages else None
    start=time.perf_counter()
    metrics=run_pipeline(data,'2026-01-14',timings=timings)
    seconds=time.perf_counter()-start
    correctness=check_metrics(metrics,users)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform!='darwin':
        rss*=1024
    report={'pid':os.getpid(),'seconds':seconds,'peak_process_rss_bytes':rss,
            'input_rows':sum(len(v) for v in data.values()),'correctness':correctness}
    if timings is not None:
        report['stage_seconds']=timings
    return report


def benchmark(sizes,repeats,profile_stages=False):
    if type(repeats) is not int or not 1<=repeats<=10:
        raise ValueError('repeats must be between 1 and 10')
    if sys.platform not in ('darwin','linux'):
        raise ValueError('RSS normalization is supported only on macOS/Linux')
    with duckdb.connect(':memory:') as con:
        threads=con.execute("SELECT current_setting('threads')").fetchone()[0]
    report={'measurement':'validated in-memory full rebuild; fixture generation and imports excluded',
            'environment':{'os':platform.system(),'os_release':platform.release(),'architecture':platform.machine(),
                           'python':platform.python_version(),'duckdb':duckdb.__version__,
                           'logical_cpus':os.cpu_count(),'duckdb_default_threads':threads},
            'rss_scope':'whole child-process peak, including imports, fixture generation, pipeline and correctness checks',
            'workloads':[]}
    for users in sizes:
        samples=[]
        for _ in range(repeats):
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker','--users',str(users)] + (['--profile-stages'] if profile_stages else []),
                                  capture_output=True,text=True,timeout=180)
            if result.returncode:
                raise RuntimeError(result.stderr or result.stdout)
            samples.append(json.loads(result.stdout))
        if any(s['correctness']!=samples[0]['correctness'] for s in samples):
            raise AssertionError('sample result drift')
        seconds=[s['seconds'] for s in samples]
        report['workloads'].append({'users':users,'input_rows':samples[0]['input_rows'],
            'correctness':samples[0]['correctness'],'samples':samples,
            'seconds_min':min(seconds),'seconds_median':statistics.median(seconds),'seconds_max':max(seconds)})
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--users',type=int,nargs='+',default=[100,1000,5000])
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--profile-stages',action='store_true',help='record six full-pipeline stages per sample')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    try:
        if args.worker:
            if len(args.users)!=1:
                raise ValueError('worker takes exactly one scale')
            report=sample(args.users[0],args.profile_stages)
        else:
            report=benchmark(args.users,args.repeats,args.profile_stages)
        text=json.dumps(report,indent=2)+'\n'
        if args.output:
            args.output.write_text(text)
        print(text,end='')
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
        parser.exit(2,str(exc)+'\n')
