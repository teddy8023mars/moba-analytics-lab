"""Interleave reference/candidate fresh-process samples; verify complete metric parity."""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
from benchmark_pipeline import benchmark


def compare(sizes,repeats):
    if not 1<=repeats<=10: raise ValueError('repeats must be between 1 and 10')
    # Reuse the environment capture and timing-boundary description without samples.
    report=benchmark([],1)
    report['method']='fresh process per variant; alternating reference/candidate order; full metric SHA256 parity'
    report['workloads']=[]
    for users in sizes:
        pairs=[]
        for repeat in range(repeats):
            order=['executemany','batched'] if repeat%2==0 else ['batched','executemany']
            pair={'order':order,'samples':{}}
            for strategy in order:
                proc=subprocess.run([sys.executable,str(Path(__file__).with_name('benchmark_pipeline.py')),
                    '--worker','--users',str(users),'--profile-stages','--load-strategy',strategy,
                    '--insert-batch-size','500'],capture_output=True,text=True,timeout=180)
                if proc.returncode:raise RuntimeError(proc.stderr or proc.stdout)
                pair['samples'][strategy]=json.loads(proc.stdout)
            reference=pair['samples']['executemany'];candidate=pair['samples']['batched']
            if reference['metric_digest']!=candidate['metric_digest'] or reference['correctness']!=candidate['correctness']:
                raise AssertionError('loader outputs differ')
            pair['full_metric_parity']=True
            pairs.append(pair)
        times={strategy:statistics.median(pair['samples'][strategy]['seconds'] for pair in pairs)
               for strategy in ('executemany','batched')}
        report['workloads'].append({'users':users,'input_rows':pairs[0]['samples']['batched']['input_rows'],
            'pairs':pairs,'seconds_median':times,'median_ratio_reference_over_candidate':times['executemany']/times['batched']})
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--users',type=int,nargs='+',default=[1000,5000])
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=compare(args.users,args.repeats)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({w['users']:w['seconds_median'] for w in report['workloads']},indent=2))
