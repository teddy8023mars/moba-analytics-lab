"""Validate S3 configuration with mocked plans only; never provision AWS resources."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def isolated_environment(source, home):
    """Do not inherit the human's cloud credentials or Terraform overrides."""
    env={k:v for k,v in source.items() if not(k.startswith('AWS_') or k.startswith('TF_') or k=='HOME')}
    env.update({'HOME':str(home),'TF_CLI_CONFIG_FILE':str(home/'empty.tfrc'),
                'AWS_CONFIG_FILE':str(home/'no-aws-config'),
                'AWS_SHARED_CREDENTIALS_FILE':str(home/'no-aws-credentials'),
                'AWS_EC2_METADATA_DISABLED':'true','TF_IN_AUTOMATION':'1'})
    return env


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path,help='fresh directory for actual logs')
    parser.add_argument('--plugin-cache',type=Path,help='optional existing provider cache, not credentials')
    args=parser.parse_args()
    output=args.output.absolute()
    try:
        output.mkdir(parents=True,exist_ok=False)
    except OSError as exc:
        parser.exit(2,f'fresh evidence directory required: {exc}\n')
    report={'scope':'configuration validation and mocked provider plans only; no AWS deployment',
            'status':'failed','steps':[]}
    try:
        with tempfile.TemporaryDirectory(prefix='moba-s3-check-') as temp:
            home=Path(temp)/'home';home.mkdir()
            env=isolated_environment(os.environ,home)
            (home/'empty.tfrc').write_text('disable_checkpoint = true\n')
            if args.plugin_cache:
                cache=args.plugin_cache.resolve(strict=True)
                if not cache.is_dir():raise ValueError('plugin cache must be an existing directory')
                env['TF_PLUGIN_CACHE_DIR']=str(cache)
            module=Path(temp)/'module';module.mkdir()
            source=ROOT/'infra/s3-snapshot'
            for path in source.glob('*.tf'):shutil.copyfile(path,module/path.name)
            shutil.copyfile(source/'.terraform.lock.hcl',module/'.terraform.lock.hcl')
            shutil.copytree(source/'tests',module/'tests')
            commands=[('version',['version','-json']),('format',['fmt','-check','-recursive']),
                      ('init',['init','-backend=false','-input=false','-lockfile=readonly','-no-color']),
                      ('validate',['validate','-no-color']),('mock-test',['test','-no-color'])]
            for name,argv in commands:
                result=subprocess.run(['terraform',*argv],cwd=module,env=env,text=True,
                                      capture_output=True,timeout=300)
                (output/f'{name}.txt').write_text(result.stdout+result.stderr)
                report['steps'].append({'name':name,'command':['terraform',*argv],'exit_code':result.returncode})
                if result.returncode:raise ValueError(f'{name} failed; see its recorded log')
                if name=='version':
                    version=json.loads(result.stdout)['terraform_version']
                    report['terraform_version']=version
                    if version!='1.12.2':raise ValueError('Terraform1.12.2 required for this reproducible exercise')
                if name=='mock-test':
                    match=re.search(r'Success! (\d+) passed, (\d+) failed\.',result.stdout)
                    if not match or match.groups()!=('8','0'):
                        raise ValueError('expected all eight mock-plan acceptance cases, not an empty test run')
                    report['mock_plan_cases_passed']=int(match.group(1))
            report['status']='passed'
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        report['error']=str(exc)
    (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 2


if __name__=='__main__':raise SystemExit(main())
