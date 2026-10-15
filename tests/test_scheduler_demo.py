import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/run_scheduler_demo.py'


def module():
    spec = importlib.util.spec_from_file_location('scheduler_demo', SCRIPT)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


class SchedulerBoundaryTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('airflow'), 'optional Airflow discovery integration')
    def test_generated_dag_is_discoverable_with_airflow_default_safe_mode(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            source = folder/'scheduled_moba.py'
            runner = module()
            source.write_text(runner.dag_source(folder))
            code = ('from airflow.utils.file import might_contain_dag; '
                    f'print(might_contain_dag({str(source)!r}, safe_mode=True))')
            proc = subprocess.run([sys.executable, '-c', code],
                                  env=runner.owned_environment(folder, os.environ),
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip().splitlines()[-1], 'True')

    def test_existing_directory_file_and_broken_symlink_are_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            directory = root/'existing'; directory.mkdir()
            marker = directory/'marker'; marker.write_text('preserve me')
            file = root/'file'; file.write_text('existing file')
            broken = root/'broken'; broken.symlink_to(root/'missing')
            for output in (directory, file, broken):
                with self.subTest(output=output.name):
                    proc = subprocess.run([sys.executable, str(SCRIPT), '--output', str(output)],
                                          capture_output=True, text=True, timeout=15)
                    self.assertNotEqual(proc.returncode, 0)
                    self.assertIn('fresh output', proc.stderr)
            self.assertEqual(marker.read_text(), 'preserve me')
            self.assertEqual(file.read_text(), 'existing file')
            self.assertTrue(broken.is_symlink())
            self.assertEqual(sorted(p.name for p in directory.iterdir()), ['marker'])

    def test_environment_is_owned_without_modifying_caller(self):
        runner = module()
        inherited = {'AIRFLOW_CONFIG':'unrelated.cfg', 'AIRFLOW_OTHER':'private',
                     'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///outside.db',
                     'HOME':'outside', 'PATH':'/usr/bin', 'PYTHONPATH':'outside', 'KEEP':'yes'}
        original = dict(inherited)
        env = runner.owned_environment(Path('/tmp/owned-example'), inherited)
        self.assertEqual(inherited, original)
        self.assertNotIn('AIRFLOW_OTHER', env)
        self.assertEqual(env['HOME'], '/tmp/owned-example/airflow-home')
        self.assertEqual(env['AIRFLOW_CONFIG'], '/tmp/owned-example/airflow-home/airflow.cfg')
        self.assertEqual(env['AIRFLOW__DATABASE__SQL_ALCHEMY_CONN'],
                         'sqlite:////tmp/owned-example/airflow-home/metadata.db')
        self.assertEqual(env['AIRFLOW__CORE__PLUGINS_FOLDER'], '/tmp/owned-example/airflow-home/plugins')
        self.assertEqual(env['KEEP'], 'yes')
        self.assertEqual(env['PATH'].split(os.pathsep)[0], str(Path(sys.executable).parent))
        self.assertNotIn('outside', env['PYTHONPATH'])

    @unittest.skipUnless(importlib.util.find_spec('psutil'), 'optional psutil dependency')
    def test_cleanup_preserves_unrelated_sentinel_and_wrong_process_identity(self):
        import psutil
        runner = module()
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        child_code = ('import os,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                      'print(os.getpid(),flush=True); time.sleep(60)')
        parent_code = ('import subprocess,sys,time; '
                       f'p=subprocess.Popen([sys.executable,"-c",{child_code!r}],stdout=subprocess.PIPE,text=True); '
                       'print(p.stdout.readline().strip(),flush=True); time.sleep(60)')
        owned = subprocess.Popen([sys.executable, '-c', parent_code], stdout=subprocess.PIPE, text=True)
        try:
            identities = {owned.pid:psutil.Process(owned.pid).create_time(),
                          sentinel.pid:psutil.Process(sentinel.pid).create_time()-1}
            child_pid = int(owned.stdout.readline().strip())
            runner.remember(owned, identities)
            self.assertIn(child_pid, identities)
            result = runner.cleanup_owned(owned, identities)
            self.assertEqual(result['owned_processes_remaining'], [])
            self.assertIsNotNone(owned.poll())
            self.assertIsNone(sentinel.poll())
            if psutil.pid_exists(child_pid):
                self.assertEqual(psutil.Process(child_pid).status(), psutil.STATUS_ZOMBIE)
        finally:
            for proc in (sentinel, owned):
                if proc.poll() is None: proc.kill()
                proc.wait(timeout=10)
            owned.stdout.close()


NATIVE = sys.platform == 'linux' and os.environ.get('RUN_SCHEDULER_INTEGRATION') == '1'

@contextmanager
def evidence_folder(label):
    retained = os.environ.get('SCHEDULER_EVIDENCE_DIR')
    if retained:
        folder = Path(retained)/label
        folder.mkdir(parents=True, exist_ok=False)
        yield folder
    else:
        with tempfile.TemporaryDirectory() as name:
            yield Path(name)


@unittest.skipUnless(NATIVE, 'optional native Linux scheduler integration')
class NativeSchedulerTests(unittest.TestCase):
    def run_cli(self, folder, *extra):
        outside = folder/'outside.cfg'; outside.write_text('untouched config')
        database = folder/'outside.db'; database.write_bytes(b'untouched database')
        proc = subprocess.run([sys.executable, str(SCRIPT), '--output', str(folder/'run'), *extra],
                              capture_output=True, text=True, timeout=300,
                              env={**os.environ, 'AIRFLOW_CONFIG':str(outside),
                                   'AIRFLOW__DATABASE__SQL_ALCHEMY_CONN':'sqlite:///'+str(database)})
        (folder/'controller.log').write_text(proc.stdout+proc.stderr)
        self.assertEqual(outside.read_text(), 'untouched config')
        self.assertEqual(database.read_bytes(), b'untouched database')
        return proc

    def test_actual_scheduled_moba_clean_and_failed_gate(self):
        with evidence_folder('success') as folder:
            proc = self.run_cli(folder)
            self.assertEqual(proc.returncode, 0, proc.stdout+proc.stderr)
            summary = json.loads((folder/'run/summary.json').read_text())
            self.assertEqual(summary['airflow_version'], '2.11.0')
            self.assertEqual(summary['cleanup']['owned_processes_remaining'], [])
            for scenario in ('clean', 'bad_metrics'):
                result = summary['scenarios'][scenario]
                self.assertEqual(len(result['runs']), 1)
                self.assertEqual(result['runs'][0][1], 'scheduled')
                self.assertEqual(result['runs'][0][2], 'failed' if scenario=='bad_metrics' else 'success')
                expected = dict(generate_fixture='success', build_metrics='success',
                                validate_metrics='success', publish_local='success')
                if scenario=='bad_metrics': expected.update(validate_metrics='failed', publish_local='upstream_failed')
                self.assertEqual(result['tasks'], expected)
            clean = summary['scenarios']['clean']['verification']
            self.assertEqual(clean['status'], 'verified')
            self.assertEqual(clean['counts'], dict(user_day=101,dau=14,retention=8,hero_stats=3,player_stats=12,monetization=4))
            self.assertEqual(clean['revenue_cents'], 1396)
            self.assertFalse((folder/'run/bad_metrics/published.json').exists())

    def test_actual_scheduler_timeout_has_cleanup_and_no_success_summary(self):
        with evidence_folder('timeout') as folder:
            proc = self.run_cli(folder, '--timeout', '0.001')
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('deadline', proc.stderr)
            self.assertFalse((folder/'run/summary.json').exists())
            cleanup = json.loads((folder/'run/cleanup.json').read_text())
            self.assertGreaterEqual(cleanup['owned_processes_observed'], 1)
            self.assertEqual(cleanup['owned_processes_remaining'], [])

if __name__ == '__main__': unittest.main()
