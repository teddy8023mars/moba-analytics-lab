import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from moba_lab.pipeline import run_pipeline
    from moba_lab.fixtures import generate_fixture
except ImportError:
    run_pipeline = generate_fixture = None


def fixture():
    return {
        "users": [{"user_id": u, "signup_at": d} for u, d in [
            ("a", "2026-01-01T00:00:00Z"), ("b", "2026-01-01T01:00:00Z"),
            ("c", "2026-01-08T00:00:00Z"), ("future", "2026-01-09T00:00:00Z")]],
        "logins": [{"event_id": e, "user_id": u, "occurred_at": d} for e, u, d in [
            ("l1", "a", "2026-01-01T12:00:00Z"), ("l2", "b", "2026-01-01T13:00:00Z"),
            ("l3", "a", "2026-01-02T00:30:00Z"), ("l3", "a", "2026-01-02T00:30:00Z"),
            ("l4", "a", "2026-01-08T10:00:00Z"), ("l5", "c", "2026-01-08T10:00:00Z"),
            ("l6", "future", "2026-01-09T10:00:00Z"),
            ("l7", "b", "2026-01-02T00:30:00+08:00")]],
        "matches": [{"match_id": "m1", "started_at": "2026-01-02T12:00:00Z", "duration_seconds": 600}],
        "participants": [
            {"match_id": "m1", "user_id": "a", "hero": "Ember", "won": True, "kills": 3, "deaths": 1, "assists": 2},
            {"match_id": "m1", "user_id": "b", "hero": "Tide", "won": False, "kills": 1, "deaths": 3, "assists": 0}],
        "payments": [
            {"payment_id": "p1", "user_id": "a", "occurred_at": "2026-01-02T14:00:00Z", "amount_cents": 100},
            {"payment_id": "p2", "user_id": "a", "occurred_at": "2026-01-02T15:00:00Z", "amount_cents": 200}]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(run_pipeline, "pipeline is not implemented")

    def test_retention_observable_denominators(self):
        # Removing eligibility filters would incorrectly turn c/future into churn.
        r = run_pipeline(fixture(), "2026-01-08")
        self.assertEqual(r["retention"], [
            {"cohort_date": "2026-01-01", "day_offset": 1, "cohort_users": 2, "retained_users": 1, "retention_rate": 0.5},
            {"cohort_date": "2026-01-01", "day_offset": 7, "cohort_users": 2, "retained_users": 1, "retention_rate": 0.5}])

    def test_dau_dedup_utc_and_future_cutoff(self):
        r = run_pipeline(fixture(), "2026-01-08")
        self.assertEqual(r["dau"], [{"activity_date": "2026-01-01", "dau": 2},
                                    {"activity_date": "2026-01-02", "dau": 1},
                                    {"activity_date": "2026-01-08", "dau": 2}])
        self.assertEqual(len(r["user_day"]), 5)

    def test_hero_and_player_grains_do_not_multiply_payments(self):
        r = run_pipeline(fixture(), "2026-01-08")
        self.assertEqual(r["hero_stats"][0], {"hero": "Ember", "player_matches": 1,
            "distinct_matches": 1, "wins": 1, "win_rate": 1.0, "kills": 3, "deaths": 1, "assists": 2})
        self.assertEqual(r["player_stats"][0]["player_matches"], 1)
        self.assertEqual(r["monetization"], [{"payment_date": "2026-01-02", "transactions": 2,
            "paying_users": 1, "revenue_cents": 300, "arppu_cents": 300.0}])

    def test_duplicate_payment_and_participant_do_not_inflate(self):
        d = fixture()
        d["payments"].append(copy.deepcopy(d["payments"][0]))
        d["participants"].append(copy.deepcopy(d["participants"][0]))
        self.assertEqual(run_pipeline(d, "2026-01-08"), run_pipeline(fixture(), "2026-01-08"))

    def test_invalid_inputs_fail_explicitly(self):
        for table, field, value in [("logins", "user_id", None), ("payments", "user_id", "missing"),
                                    ("payments", "amount_cents", -1), ("logins", "occurred_at", "2026-01-01T12:00:00")]:
            with self.subTest(table=table, field=field):
                d = fixture(); d[table][0][field] = value
                with self.assertRaises(ValueError): run_pipeline(d, "2026-01-08")

    def test_conflicting_identity_fails(self):
        d = fixture(); row = copy.deepcopy(d["payments"][0]); row["amount_cents"] = 999
        d["payments"].append(row)
        with self.assertRaises(ValueError): run_pipeline(d, "2026-01-08")

    def test_partial_observation_excludes_d7_but_keeps_d1(self):
        rows = run_pipeline(fixture(), "2026-01-02")["retention"]
        self.assertEqual(rows, [{"cohort_date": "2026-01-01", "day_offset": 1,
            "cohort_users": 2, "retained_users": 1, "retention_rate": 0.5}])

    def test_missing_match_and_pre_signup_fail(self):
        d = fixture(); d["participants"][0]["match_id"] = "unknown"
        with self.assertRaises(ValueError): run_pipeline(d, "2026-01-08")
        d = fixture(); d["logins"][0]["occurred_at"] = "2025-12-31T23:59:59Z"
        with self.assertRaises(ValueError): run_pipeline(d, "2026-01-08")

    def test_asof_requires_explicit_calendar_format(self):
        with self.assertRaises(ValueError): run_pipeline(fixture(), "20260108")

    def test_empty_data_has_empty_metrics(self):
        self.assertTrue(all(not rows for rows in run_pipeline({k: [] for k in fixture()}, "2026-01-08").values()))

    def test_generator_and_pipeline_are_repeatable(self):
        self.assertIsNotNone(generate_fixture)
        self.assertEqual(generate_fixture(7), generate_fixture(7))
        self.assertNotEqual(generate_fixture(7), generate_fixture(8))
        self.assertEqual(run_pipeline(generate_fixture(7), "2026-01-14"), run_pipeline(generate_fixture(7), "2026-01-14"))

    def test_cli_exports_and_invalid_input_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); source = p / "fixture.json"
            source.write_text(json.dumps(fixture()))
            command = [sys.executable, "-m", "moba_lab", "run", "--input", str(source), "--as-of", "2026-01-08", "--output", str(p / "report")]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with (p / "report/retention.csv").open() as exported:
                rows = list(csv.DictReader(exported))
            self.assertEqual([x["retention_rate"] for x in rows], ["0.5", "0.5"])
            self.assertIn("Synthetic MOBA", (p / "report/index.html").read_text())
            source.write_text("{broken")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
