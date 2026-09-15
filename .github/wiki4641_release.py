#!/usr/bin/env python3
"""Reuse the validated 4.6.4 image validator, with explicitly named hotfix artifacts."""
from pathlib import Path
import hashlib,json,shutil,sys,types
R=Path(__file__).resolve().parents[1]
s=(R/'.github/wiki464_finish.py').read_text().replace('4.6.4','4.6.4.1').replace('wiki464-dist','wiki4641-dist').replace("R/'.github/wiki464_README.md'","R/'.github/wiki4641_README.md'")
m=types.ModuleType('hotfix_package');m.__file__=str(R/'.github/wiki4641_release.py');exec(compile(s,m.__file__,'exec'),m.__dict__)
m.FILES+=['.github/wiki4641_apply.py','.github/wiki4641_test.py','.github/wiki4641_release.py','.github/workflows/wiki4641.yml']
original_excluded=m.excluded
m.excluded=lambda p:original_excluded(p) or p.name in ('FreeInkUIFont.h','gallery_font.h')
mode=sys.argv[1]
if mode=='prepare':
 assert hashlib.sha256((R/'lib/hal/HalStorage.cpp').read_bytes()).hexdigest()=='683b3178253329c462dd4a6aaa4f95f7c92b9677749ff875ae0147dc7dfae4a3'
 assert hashlib.sha256((R/'src/activities/wiki/WikiIndexJob.cpp').read_bytes()).hexdigest()=='19319e2d1d7e75d09ae5222221a4860690191540a90c4a632c3e27964d1f22b3'
 assert hashlib.sha256((R/'src/activities/wiki/WikiArchive.cpp').read_bytes()).hexdigest()=='217449ade6db5fed90e82a3ab04f2edcdefb0b5b9b243b6dffb09418300cab22'
 m.prepare()
elif mode=='test':m.test()
elif mode=='package':
 before=json.loads((R/'wiki4641-before.json').read_text());after=json.loads((R/'wiki4641-real-hal-results.json').read_text())
 assert before['production_HAL_compiled'] and before['baseline_bug_reproduction'] and all(x['passed'] for x in before['cases'])
 assert after['production_HAL_compiled'] and not after['HalFile_mock_used'] and after['source_unchanged'] and all(x['passed'] for x in after['cases'])
 m.package();out=R/'wiki4641-dist'
 for p in sorted(R.glob('wiki4641-*.json'))+sorted(R.glob('wiki4641-*.log')):shutil.copyfile(p,out/p.name)
 manifest=json.loads((out/'build-manifest.json').read_text());manifest.update({'hotfix_for':'4.6.4','fix_scope':'Guard indexer cleanup on unopened handles; retain HAL assertions and index format','baseline_464_commit':'9f74e6271de1075642ad63206874d88ad1b45a8d','actual_HAL_host_cases':len(after['cases']),'actual_HAL_positive_cases':sum(not x['expected_production_assert'] for x in after['cases']),'assertion_negative_control':True,'full_new_2_5GB_hardware_import_tested':False})
 (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
else:raise SystemExit('Expected prepare, test or package')
