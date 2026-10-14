"""Independent small workload answers; timings are observations, never pass thresholds."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from moba_lab.pipeline import run_pipeline

ROOT=Path(__file__).resolve().parents[1]

class BenchmarkTests(unittest.TestCase):
    def module(self):
        spec=importlib.util.spec_from_file_location('benchmark_demo', ROOT/'scripts/benchmark_pipeline.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_four_user_workload_has_independent_exact_answers(self):
        data=self.module().workload(4)
        self.assertEqual({k:len(v) for k,v in data.items()},
                         {'users':4,'logins':60,'matches':2,'participants':8,'payments':12})
        result=run_pipeline(data,'2026-01-14')
        self.assertEqual([r['dau'] for r in result['dau']], [4]*14)
        self.assertEqual(result['retention'],[
            {'cohort_date':'2026-01-01','day_offset':1,'cohort_users':4,'retained_users':4,'retention_rate':1.0},
            {'cohort_date':'2026-01-01','day_offset':7,'cohort_users':4,'retained_users':4,'retention_rate':1.0}])
        self.assertEqual(len(result['user_day']),56)
        self.assertEqual([r['player_matches'] for r in result['player_stats']],[2]*4)
        self.assertEqual(sum(r['revenue_cents'] for r in result['monetization']),4792)
        self.assertEqual(sum(r['transactions'] for r in result['monetization']),8)

    def test_benchmark_cli_records_each_fresh_process_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json'
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/benchmark_pipeline.py'),
                '--users','4','--repeats','2','--output',str(path)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            report=json.loads(path.read_text())
            self.assertEqual(report['measurement'],'validated in-memory full rebuild; fixture generation and imports excluded')
            run=report['workloads'][0]
            self.assertEqual(run['input_rows'],86)
            self.assertEqual(run['correctness'],{'user_days':56,'dau_per_day':4,'retention_rows':2,'revenue_cents':4792,'transactions':8})
            self.assertEqual(len(run['samples']),2)
            self.assertEqual(len({s['pid'] for s in run['samples']}),2)
            self.assertTrue(all(s['seconds']>0 and s['peak_process_rss_bytes']>0 for s in run['samples']))

    def test_invalid_scale_fails_explicitly(self):
        for value in [0,-4,3,True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module().workload(value)

if __name__=='__main__': unittest.main()
