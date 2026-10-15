import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import duckdb
try:
    from moba_lab.parquet_snapshot import export_user_days
except ImportError:
    export_user_days = None

ROOT = Path(__file__).resolve().parents[1]
ROWS = [{'activity_date': d, 'user_id': u} for d,u in [
    ('2026-01-01','a'),('2026-01-01','b'),('2026-01-02','a'),
    ('2026-01-08','a'),('2026-01-08','c')]]

class ParquetSnapshotTests(unittest.TestCase):
    def exporter(self):
        self.assertTrue(callable(export_user_days), 'Parquet snapshot API is missing')
        return export_user_days

    def test_hand_computed_roundtrip_dau_and_date_type(self):
        export = self.exporter()
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'snapshot'
            result=export(ROWS,folder,'2026-01-02')
            self.assertEqual(result['rows'],5)
            self.assertEqual(result['partition_count'],3)
            self.assertEqual(result['dau'],[{'activity_date':'2026-01-01','dau':2},
                {'activity_date':'2026-01-02','dau':1},{'activity_date':'2026-01-08','dau':2}])
            self.assertEqual(result['filtered_user_ids'],['a'])
            self.assertTrue(result['full_rows_equal'])
            self.assertEqual(json.loads((folder/'summary.json').read_text()),result)
            with duckdb.connect(':memory:') as con:
                glob=str(folder/'user_day/*/*.parquet')
                actual=con.execute('SELECT activity_date::VARCHAR,user_id FROM read_parquet(?,hive_partitioning=true) ORDER BY 1,2',[glob]).fetchall()
                self.assertEqual(actual,[('2026-01-01','a'),('2026-01-01','b'),('2026-01-02','a'),('2026-01-08','a'),('2026-01-08','c')])
                self.assertEqual(con.execute('SELECT typeof(activity_date) FROM read_parquet(?,hive_partitioning=true) LIMIT 1',[glob]).fetchone()[0],'DATE')
            self.assertIn('Scanning Files: 1/3',result['explain'])

    def test_quotes_unicode_and_absent_filter(self):
        export=self.exporter()
        with tempfile.TemporaryDirectory() as temp:
            result=export([{'activity_date':'2026-01-01','user_id':"a'); DROP TABLE user_day;--"},
                           {'activity_date':'2026-01-01','user_id':'玩家'}],Path(temp)/"quoted' folder",'2026-01-02')
            self.assertEqual(result['rows'],2)
            self.assertEqual(result['dau'],[{'activity_date':'2026-01-01','dau':2}])
            self.assertEqual(result['filtered_user_ids'],[])
            self.assertTrue(result['full_rows_equal'])

    def test_invalid_input_creates_no_output(self):
        export=self.exporter()
        cases=[([], '2026-01-01'),(ROWS+ROWS[:1],'2026-01-01'),
            ([{'activity_date':'20260101','user_id':'a'}],'2026-01-01'),
            ([{'activity_date':'2026-02-30','user_id':'a'}],'2026-01-01'),
            ([{'activity_date':True,'user_id':'a'}],'2026-01-01'),
            ([{'activity_date':'2026-01-01','user_id':' '}],'2026-01-01'),
            ([{'activity_date':'2026-01-01','user_id':'a','extra':1}],'2026-01-01'),
            (ROWS,'20260101')]
        with tempfile.TemporaryDirectory() as temp:
            for index,(rows,day) in enumerate(cases):
                folder=Path(temp)/str(index)
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):export(rows,folder,day)
                    self.assertFalse(folder.exists())

    def test_existing_output_and_broken_symlink_are_refused(self):
        export=self.exporter()
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'existing';folder.mkdir()
            marker=folder/'keep';marker.write_text('user data')
            with self.assertRaises(FileExistsError):export(ROWS,folder,'2026-01-02')
            self.assertEqual(marker.read_text(),'user data')
            self.assertEqual(list(folder.iterdir()),[marker])
            link=Path(temp)/'broken';link.symlink_to(Path(temp)/'absent')
            with self.assertRaises(FileExistsError):export(ROWS,link,'2026-01-02')
            self.assertTrue(link.is_symlink())
            self.assertFalse((Path(temp)/'absent').exists())

    def test_summary_write_failure_leaves_only_owned_partial_output(self):
        export=self.exporter()
        original=Path.write_text
        def fail_summary(path,*args,**kwargs):
            if path.name=='.summary.json.tmp':
                raise OSError('injected report write failure')
            return original(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'partial'
            with patch.object(Path,'write_text',fail_summary):
                with self.assertRaises(OSError):export(ROWS,folder,'2026-01-02')
            self.assertEqual(len(list(folder.rglob('*.parquet'))),3)
            self.assertFalse((folder/'summary.json').exists())
            with self.assertRaises(FileExistsError):export(ROWS,folder,'2026-01-02')

    def test_real_seed_demo_and_existing_output_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'run'
            command=[sys.executable,str(ROOT/'scripts/run_parquet_demo.py'),'--output',str(folder)]
            env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
            proc=subprocess.run(command,cwd=temp,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            report=json.loads(proc.stdout)
            self.assertEqual(report['rows'],101)
            self.assertEqual(report['partition_count'],14)
            self.assertEqual(len(report['dau']),14)
            self.assertEqual(report['filtered_user_ids'],['u00','u01','u02','u03','u05','u07','u09','u10','u11'])
            self.assertIn('Scanning Files: 1/14',report['explain'])
            self.assertTrue(report['full_rows_equal'])
            before=(folder/'summary.json').read_bytes()
            rerun=subprocess.run(command,cwd=temp,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(rerun.returncode,2)
            self.assertEqual((folder/'summary.json').read_bytes(),before)

if __name__=='__main__':unittest.main()
