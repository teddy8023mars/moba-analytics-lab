import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class S3WrapperTests(unittest.TestCase):
    def test_isolation_removes_credentials_and_terraform_overrides(self):
        path=ROOT/'scripts/check_s3_infra.py'
        self.assertTrue(path.exists(),'offline infrastructure wrapper is missing')
        spec=importlib.util.spec_from_file_location('s3_wrapper',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source={'PATH':'/test/bin','HOME':'/human/home','AWS_ACCESS_KEY_ID':'dummy-key',
                'AWS_SECRET_ACCESS_KEY':'dummy-secret','AWS_PROFILE':'human',
                'AWS_CONFIG_FILE':'/human/config','TF_VAR_bucket_name':'human-bucket',
                'TF_CLI_ARGS_test':'-filter=unsafe','TF_TOKEN_app_terraform_io':'dummy-token'}
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)
            result=module.isolated_environment(source,home)
            for name in ('AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','AWS_PROFILE',
                         'TF_VAR_bucket_name','TF_CLI_ARGS_test','TF_TOKEN_app_terraform_io'):
                self.assertNotIn(name,result)
            self.assertEqual(result['HOME'],str(home))
            self.assertEqual(result['PATH'],'/test/bin')
            self.assertEqual(result['AWS_EC2_METADATA_DISABLED'],'true')
            self.assertEqual(result['TF_CLI_CONFIG_FILE'],str(home/'empty.tfrc'))
            self.assertFalse(Path(result['AWS_CONFIG_FILE']).exists())
            self.assertFalse(Path(result['AWS_SHARED_CREDENTIALS_FILE']).exists())
            self.assertEqual(source['AWS_PROFILE'],'human')

if __name__=='__main__':unittest.main()
