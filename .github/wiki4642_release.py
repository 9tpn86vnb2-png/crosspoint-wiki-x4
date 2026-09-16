#!/usr/bin/env python3
"""4.6.4.2 release gates; production tests never rewrite production files."""
from pathlib import Path
import hashlib,json,shutil,sys,types
R=Path(__file__).resolve().parents[1]
s=(R/'.github/wiki464_finish.py').read_text()
s=s.replace('4.6.4','4.6.4.2').replace('wiki464-dist','wiki4642-dist')
s=s.replace("R/'.github/wiki464_README.md'","R/'.github/wiki4642_README.md'")
s=s.replace("'READ_BYTES = 8192'", "'READ_BYTES = 12288'")
s=s.replace("'8KiB-XML-buffer'", "'12KiB-XML-buffer'")
m=types.ModuleType('speed_package');m.__file__=str(R/'.github/wiki4642_release.py')
exec(compile(s,m.__file__,'exec'),m.__dict__)
m.FILES += ['.github/wiki4642_apply.py','.github/wiki4642_release.py','.github/wiki4642_README.md','.github/workflows/wiki4642.yml','.github/wiki464_host/tests.cpp','.github/wiki4641_test.py']
old_excluded=m.excluded
m.excluded=lambda p:old_excluded(p) or p.name in ('FreeInkUIFont.h','gallery_font.h')
mode=sys.argv[1]
if mode=='prepare':
    assert hashlib.sha256((R/'lib/hal/HalStorage.cpp').read_bytes()).hexdigest()=='683b3178253329c462dd4a6aaa4f95f7c92b9677749ff875ae0147dc7dfae4a3'
    assert hashlib.sha256((R/'src/activities/wiki/WikiArchive.cpp').read_bytes()).hexdigest()=='217449ade6db5fed90e82a3ab04f2edcdefb0b5b9b243b6dffb09418300cab22'
    m.prepare()
elif mode=='test':
    m.test()
elif mode=='package':
    actual=json.loads((R/'wiki4641-real-hal-results.json').read_text())
    assert actual['production_HAL_compiled'] and not actual['HalFile_mock_used']
    assert actual['source_unchanged'] and all(x['passed'] for x in actual['cases'])
    assert len(actual['cases'])==31 and any(x['expected_production_assert'] for x in actual['cases'])
    m.package();out=R/'wiki4642-dist'
    for pattern in ('wiki4642-*.log','wiki4641-real-hal-results.json','4.6.4.1-to-4.6.4.2.patch'):
        for p in R.glob(pattern):shutil.copyfile(p,out/p.name)
    manifest=json.loads((out/'build-manifest.json').read_text())
    manifest.update({'baseline_4641_commit':'cbcd8bf73ede03e2849c7f05c0e49cf0443b1754','fix_scope':'Indexing speed only; library reuse and persistent formats unchanged','indexer_XML_read_buffer_bytes':12288,'indexer_slice_target_ms':8,'indexer_max_quanta':8,'indexer_max_scan_bytes_per_call':98304,'indexer_compiler_optimization':'-O2 scoped to WikiIndexJob.cpp only','index_ui_refresh_ms':10000,'actual_HAL_host_cases':31,'assertions_retained':True,'hardware_tested':False,'measured_hardware_speed_or_current':False})
    (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
else:raise SystemExit('Expected prepare, test or package')
