"""Opt-in actual dbt build: literal expectations, canonical parity and failing data test."""
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def dbt_installed():
    try:
        importlib.metadata.version('dbt-core')
        importlib.metadata.version('dbt-duckdb')
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


@unittest.skipUnless(dbt_installed(), 'optional dbt dependencies not installed')
class DbtIntegrationTests(unittest.TestCase):
    def test_build_parity_boundaries_and_fault_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_dbt_demo.py'),
                                     '--output', temp], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((Path(temp) / 'summary.json').read_text())
            self.assertEqual(report['as_of'], '2026-01-14')
            self.assertEqual(report['models_built'], 13)
            self.assertEqual(report['data_tests_passed'], 3)
            self.assertEqual(report['row_counts'], {'user_day':101,'dau':14,'retention':8,
                            'hero_stats':3,'player_stats':12,'monetization':4})
            self.assertEqual(report['jan1_retention'], [[1,3,2],[7,3,3]])
            self.assertEqual(report['revenue_cents'], 1396)
            self.assertEqual(report['earlier_cutoff_retention_rows'], 5)
            self.assertTrue(report['all_marts_match_canonical'])
            self.assertEqual(report['bad_retention_test_exit'], 1)
            self.assertEqual(report['bad_retention_failures'], 1)
            self.assertEqual(report['restored_test_exit'], 0)

if __name__ == '__main__':
    unittest.main()
