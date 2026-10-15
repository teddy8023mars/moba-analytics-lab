"""Consumer-visible integrity checks over literal local synthetic artifacts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.metrics = {name: [] for name in ('user_day', 'dau', 'retention', 'hero_stats', 'player_stats')}
        self.metrics['monetization'] = [{'revenue_cents': 125}, {'revenue_cents': 75}]
        self.data = self.folder / 'metrics.json'
        self.data.write_text(json.dumps(self.metrics))
        self.manifest = {'scope': 'synthetic local artifact; not website or production deployment',
                         'metrics_file': 'metrics.json', 'sha256': hashlib.sha256(self.data.read_bytes()).hexdigest(),
                         'counts': {'user_day': 0, 'dau': 0, 'retention': 0, 'hero_stats': 0,
                                    'player_stats': 0, 'monetization': 2}, 'revenue_cents': 200}
        self.path = self.folder / 'published.json'

    def invoke(self):
        self.path.write_text(json.dumps(self.manifest))
        return subprocess.run([sys.executable, '-m', 'moba_lab', 'verify', '--manifest', str(self.path)],
                              cwd=self.folder, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
                              text=True, capture_output=True, timeout=15)

    def rejected(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('artifact verification failed', result.stderr)
        self.assertEqual(result.stdout, '')

    def test_matching_artifact_cli_is_read_only(self):
        before = self.data.read_bytes()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'verified')
        self.assertEqual(report['revenue_cents'], 200)
        from moba_lab.artifacts import verify_manifest
        self.assertEqual(verify_manifest(self.path)['revenue_cents'], 200)
        self.assertEqual(report['counts']['monetization'], 2)
        self.assertEqual(self.data.read_bytes(), before)
        self.assertEqual(set(p.name for p in self.folder.iterdir()), {'metrics.json', 'published.json'})

    def test_modified_or_missing_metrics_fail(self):
        self.data.write_bytes(self.data.read_bytes() + b' ')
        self.rejected()
        self.data.unlink()
        self.rejected()

    def test_manifest_summary_and_types_are_checked(self):
        for change in ({'revenue_cents': 201}, {'revenue_cents': True}, {'sha256': 'not-a-hash'},
                       {'counts': {**self.manifest['counts'], 'dau': True}},
                       {'counts': {**self.manifest['counts'], 'dau': 1}}, {'metrics_file': None}):
            original = dict(self.manifest)
            with self.subTest(change=change):
                self.manifest.update(change)
                self.rejected()
                self.manifest = original

    def test_unsafe_paths_and_symlink_target_fail(self):
        for name in ('../outside.json', '/tmp/outside.json', '..', '.', 'sub/metrics.json', 'sub\\metrics.json'):
            with self.subTest(name=name):
                self.manifest['metrics_file'] = name
                self.rejected()
        self.data.rename(self.folder / 'real.json')
        self.data.symlink_to(self.folder / 'real.json')
        self.manifest['metrics_file'] = 'metrics.json'
        self.rejected()

    def test_matching_hash_does_not_hide_malformed_metrics(self):
        for value in ([], {'dau': []}, {**self.metrics, 'dau': {}},
                      {**self.metrics, 'dau': [1]},
                      {**self.metrics, 'monetization': [{'revenue_cents': True}, {'revenue_cents': 75}]},
                      {**self.metrics, 'monetization': [{'revenue_cents': -1}, {'revenue_cents': 75}]}):
            with self.subTest(value=value):
                self.data.write_text(json.dumps(value))
                self.manifest['sha256'] = hashlib.sha256(self.data.read_bytes()).hexdigest()
                self.rejected()

    def test_malformed_manifest_and_missing_manifest_exit_cleanly(self):
        for raw in ('{broken', '[]', '{"metrics_file": "metrics.json"}'):
            self.path.write_text(raw)
            result = subprocess.run([sys.executable, '-m', 'moba_lab', 'verify', '--manifest', str(self.path)],
                                    env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn('artifact verification failed', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
        self.path.unlink()
        result = subprocess.run([sys.executable, '-m', 'moba_lab', 'verify', '--manifest', str(self.path)],
                                env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertIn('artifact verification failed', result.stderr)

    def test_deep_duplicate_and_nonfinite_json_exit_cleanly(self):
        raw_deep = b'[' * 20000 + b'0' + b']' * 20000
        self.path.write_bytes(raw_deep)
        result = subprocess.run([sys.executable, '-m', 'moba_lab', 'verify', '--manifest', str(self.path)],
                                env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
                                capture_output=True, text=True, timeout=15)
        with self.subTest(manifest='deep'):
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('artifact verification failed', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
        for raw in (raw_deep, json.dumps(self.metrics).encode()[:-1] + b', "dau": []}',
                    json.dumps({**self.metrics, 'dau': [{'value': 0.0}]}).encode().replace(b'0.0', b'1e999')):
            with self.subTest(prefix=raw[:40]):
                self.data.write_bytes(raw)
                self.manifest['sha256'] = hashlib.sha256(raw).hexdigest()
                self.manifest['counts']['dau'] = 1 if b'1e999' in raw else 0
                self.rejected()


if __name__ == '__main__':
    unittest.main()
