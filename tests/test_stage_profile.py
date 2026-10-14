import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import duckdb
from moba_lab.pipeline import run_pipeline
from test_pipeline import fixture

ROOT=Path(__file__).resolve().parents[1]
STAGES={'validation','connection_setup','raw_load','sql_models','result_fetch','connection_close'}

class StageProfileTests(unittest.TestCase):
    def test_timing_preserves_metrics_and_covers_completed_pipeline(self):
        data=fixture();before=copy.deepcopy(data);timings={'stale':123}
        result=run_pipeline(data,'2026-01-08',timings=timings)
        self.assertEqual(result,run_pipeline(before,'2026-01-08'))
        self.assertEqual(result['retention'][0]['retained_users'],1)
        self.assertEqual(result['monetization'][0]['revenue_cents'],300)
        self.assertEqual(data,before)
        self.assertEqual(set(timings),STAGES|{'total'})
        self.assertTrue(all(value>=0 for value in timings.values()))
        self.assertAlmostEqual(sum(timings[k] for k in STAGES),timings['total'],places=9)

    def test_failure_does_not_publish_partial_timing(self):
        timings={'previous_success':123}
        with self.assertRaises(ValueError): run_pipeline(fixture(),'bad-date',timings=timings)
        self.assertEqual(timings,{'previous_success':123})
        with patch('moba_lab.pipeline.files') as sql_resource:
            sql_resource.return_value.joinpath.return_value.read_text.return_value = 'SELECT missing_column FROM raw_users'
            with self.assertRaises(duckdb.Error):
                run_pipeline(fixture(),'2026-01-08',timings=timings)
        self.assertEqual(timings,{'previous_success':123})
        with self.assertRaises(ValueError): run_pipeline(fixture(),'2026-01-08',timings=[])

    def test_profile_cli_keeps_independent_totals_and_each_sample_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'report.json'
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/benchmark_pipeline.py'),'--users','4',
                '--repeats','1','--profile-stages','--output',str(path)],cwd=ROOT,
                env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            report=json.loads(path.read_text())
            sample=report['workloads'][0]['samples'][0]
            self.assertEqual(sample['correctness']['revenue_cents'],4792)
            self.assertEqual(sample['correctness']['user_days'],56)
            self.assertEqual(set(sample['stage_seconds']),STAGES|{'total'})
            self.assertLessEqual(sample['stage_seconds']['total'],sample['seconds'])

if __name__=='__main__':unittest.main()
