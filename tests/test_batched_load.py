import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import duckdb
from moba_lab.pipeline import run_pipeline, SCHEMAS
from test_pipeline import fixture

class BatchedLoadTests(unittest.TestCase):
    def test_batch_boundaries_and_values_match_baseline(self):
        data=fixture()
        unsafe="x'); DROP TABLE observation; --"
        for rows in data.values():
            for row in rows:
                if row.get('user_id')=='a':row['user_id']=unsafe
        data['payments'][0]['amount_cents']=2**63-1
        data['payments'][1]['amount_cents']=2**63-2
        before=copy.deepcopy(data)
        baseline=run_pipeline(data,'2026-01-08',load_strategy='executemany')
        for size in [1,2,3,500]:
            with self.subTest(size=size):
                actual=run_pipeline(data,'2026-01-08',load_strategy='batched',insert_batch_size=size)
                self.assertEqual(actual,baseline)
                self.assertEqual(actual['monetization'][0]['revenue_cents'],2**64-3)
                self.assertEqual(actual['retention'][0]['cohort_users'],2)
        self.assertEqual(data,before)

    def test_raw_duplicate_cardinality_and_partial_batch(self):
        from moba_lab.pipeline import _insert_rows
        with duckdb.connect(':memory:') as con:
            con.execute("SET TimeZone='UTC'")
            con.execute('CREATE TABLE raw_payments(payment_id VARCHAR,user_id VARCHAR,occurred_at TIMESTAMPTZ,amount_cents BIGINT)')
            rows=[('p','u','2026-01-02T00:30:00+08:00',2**63-1)]*5
            _insert_rows(con,'raw_payments',SCHEMAS['payments'],rows,'batched',2)
            self.assertEqual(con.execute('SELECT COUNT(*),SUM(amount_cents) FROM raw_payments').fetchone(),(5,5*(2**63-1)))
            self.assertEqual(str(con.execute('SELECT occurred_at::DATE FROM raw_payments LIMIT 1').fetchone()[0]),'2026-01-01')

    def test_comparison_cli_alternates_and_checks_whole_outputs(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'comparison.json'
            proc=subprocess.run([sys.executable,str(root/'scripts/compare_loaders.py'),'--users','4',
                '--repeats','2','--output',str(path)],cwd=root,
                env={**os.environ,'PYTHONPATH':str(root/'src')},capture_output=True,text=True,timeout=60)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            report=json.loads(path.read_text());work=report['workloads'][0]
            self.assertEqual(work['input_rows'],86)
            self.assertEqual([pair['order'] for pair in work['pairs']],
                             [['executemany','batched'],['batched','executemany']])
            for pair in work['pairs']:
                self.assertTrue(pair['full_metric_parity'])
                for sample in pair['samples'].values():
                    self.assertEqual(sample['correctness']['user_days'],56)
                    self.assertEqual(sample['correctness']['revenue_cents'],4792)

    def test_invalid_loader_options_fail_even_when_input_empty(self):
        empty={table:[] for table in SCHEMAS}
        for options in [{'load_strategy':'typo'},{'insert_batch_size':0},{'insert_batch_size':True},{'insert_batch_size':1001}]:
            with self.subTest(options=options),self.assertRaises(ValueError):
                run_pipeline(empty,'2026-01-14',**options)

if __name__=='__main__':unittest.main()
