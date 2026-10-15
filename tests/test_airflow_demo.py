import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
try:
    importlib.metadata.version('apache-airflow')
    HAVE_AIRFLOW=True
except importlib.metadata.PackageNotFoundError:
    HAVE_AIRFLOW=False

@unittest.skipUnless(HAVE_AIRFLOW,'optional Airflow environment not installed')
class AirflowDemoTests(unittest.TestCase):
    def test_existing_scenario_is_preserved_and_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'clean';folder.mkdir()
            marker=folder/'keep.txt';marker.write_text('existing user artifact')
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/run_airflow_demo.py'),'--output',temp],
                cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=30)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('fresh output directory',proc.stderr)
            self.assertEqual(marker.read_text(),'existing user artifact')
            self.assertFalse((Path(temp)/'transient').exists())
            self.assertFalse((Path(temp)/'summary.json').exists())

    def test_real_dag_dependency_retry_and_publication_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            proc=subprocess.run([sys.executable,str(ROOT/'scripts/run_airflow_demo.py'),'--output',temp],
                cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),
                     'AIRFLOW_CONFIG':str(Path(temp)/'unrelated-config.cfg'),
                     'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///'+str(Path(temp)/'unrelated-metadata.db')},
                capture_output=True,text=True,timeout=180)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            report=json.loads((Path(temp)/'summary.json').read_text())
            self.assertEqual(report['airflow_version'],'2.11.0')
            self.assertFalse((Path(temp)/'unrelated-config.cfg').exists())
            self.assertFalse((Path(temp)/'unrelated-metadata.db').exists())
            for mode,attempts in [('clean',1),('transient',2)]:
                run=report['scenarios'][mode]
                self.assertEqual(run['state'],'success')
                self.assertEqual(run['tasks'],{'generate_fixture':'success','build_metrics':'success',
                                               'validate_metrics':'success','publish_local':'success'})
                self.assertEqual(run['build_attempts'],attempts)
                self.assertTrue(run['published'])
                self.assertEqual(run['published_counts'],{'user_day':101,'dau':14,'retention':8,
                    'hero_stats':3,'player_stats':12,'monetization':4})
                self.assertEqual(run['published_revenue_cents'],1396)
                from moba_lab.artifacts import verify_manifest
                manifest=Path(temp)/mode/'artifacts/published.json'
                checked=verify_manifest(manifest)
                self.assertEqual(checked['status'],'verified')
                self.assertEqual(checked['revenue_cents'],1396)
                metrics=manifest.parent/'metrics.json'
                metrics.write_bytes(metrics.read_bytes()+b' ')
                with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
                    verify_manifest(manifest)
            bad=report['scenarios']['bad_metrics']
            self.assertEqual(bad['state'],'failed')
            self.assertEqual(bad['tasks'],{'generate_fixture':'success','build_metrics':'success',
                                           'validate_metrics':'failed','publish_local':'upstream_failed'})
            self.assertEqual(bad['build_attempts'],1)
            self.assertFalse(bad['published'])
            self.assertFalse((Path(temp)/'bad_metrics/artifacts/published.json').exists())

if __name__=='__main__':unittest.main()
