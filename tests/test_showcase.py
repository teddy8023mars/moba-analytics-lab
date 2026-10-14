"""The explorer must expose canonical results without treating censoring as churn."""
import importlib.util
import json
import re
import unittest
from datetime import date, timedelta
from pathlib import Path

from moba_lab.pipeline import run_pipeline

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('showcase', ROOT / 'scripts/build_showcase.py')
showcase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(showcase)


class ShowcaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((ROOT / 'examples/fixture.json').read_text())
        cls.data = json.loads((ROOT / 'docs/showcase-data.json').read_text())

    def test_recorded_snapshots_equal_canonical_pipeline(self):
        for cutoff, snapshot in self.data['snapshots'].items():
            with self.subTest(cutoff=cutoff):
                self.assertEqual(snapshot['metrics'], run_pipeline(self.source, cutoff))

    def test_na_cells_are_censored_and_never_zero(self):
        found_na = False
        for cutoff, snapshot in self.data['snapshots'].items():
            observed = {(r['cohort_date'], r['day_offset']): r for r in snapshot['metrics']['retention']}
            for cell in snapshot['retention_cells']:
                eligible = date.fromisoformat(cell['cohort_date']) + timedelta(days=cell['day_offset']) <= date.fromisoformat(cutoff)
                self.assertEqual(cell['observable'], eligible)
                if not eligible:
                    found_na = True
                    self.assertIsNone(cell['retention_rate'])
                    self.assertIsNone(cell['retained_users'])
                    self.assertNotIn((cell['cohort_date'], cell['day_offset']), observed)
                else:
                    row = observed[(cell['cohort_date'], cell['day_offset'])]
                    self.assertEqual(cell['retention_rate'], row['retention_rate'])
                    self.assertEqual(cell['retained_users'], row['retained_users'])
        self.assertTrue(found_na)
        # Hand-calculated Jan 03 D1 for Jan 02 at Jan 08 is observed (1/3).
        jan8 = self.data['snapshots']['2026-01-08']['retention_cells']
        self.assertEqual([r['observable'] for r in jan8 if r['day_offset'] == 7], [True, False, False, False])

    def test_observed_zero_is_distinct_from_unobservable(self):
        empty_logins = dict(self.source, logins=[])
        custom = showcase.build_data(empty_logins)
        jan8 = custom['snapshots']['2026-01-08']['retention_cells']
        eligible = next(r for r in jan8 if r['cohort_date'] == '2026-01-01' and r['day_offset'] == 7)
        censored = next(r for r in jan8 if r['cohort_date'] == '2026-01-02' and r['day_offset'] == 7)
        self.assertEqual(eligible['retention_rate'], 0)
        self.assertEqual(eligible['retained_users'], 0)
        self.assertIsNone(censored['retention_rate'])

    def test_reproducible_export_and_embedded_offline_data(self):
        self.assertEqual(self.data, showcase.build_data())
        html = (ROOT / 'docs/index.html').read_text()
        payload = re.search(r'<script id="showcase-data" type="application/json">(.*?)</script>',html,re.S)[1]
        self.assertEqual(json.loads(payload), self.data)
        self.assertNotIn('<script src=',html)
        self.assertEqual((ROOT / 'docs/assets/showcase.svg').read_text(),showcase.make_preview(self.data))

    def test_preview_key_values_match_full_snapshot(self):
        preview = showcase.make_preview(self.data)
        metrics = self.data['snapshots'][self.data['as_of_utc']]['metrics']
        self.assertIn('1,396 cents = 13.96 currency units',preview)
        self.assertEqual(sum(r['revenue_cents'] for r in metrics['monetization']),1396)
        self.assertEqual(sum(r['player_matches'] for r in metrics['hero_stats']),40)
        self.assertEqual(len(metrics['user_day']),101)
        self.assertIn('68.8% · 11/16',preview)

if __name__ == '__main__':
    unittest.main()
