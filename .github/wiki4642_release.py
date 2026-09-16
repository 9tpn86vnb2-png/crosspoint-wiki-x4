#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,shutil,sys,types
R=Path(__file__).resolve().parents[1]
s=(R/'.github/wiki464_finish.py').read_text().replace('4.6.4','4.6.4.2').replace('wiki464-dist','wiki4642-dist')
m=types.ModuleType('speed_package');m.__file__=str(R/'.github/wiki4642_release.py');exec(compile(s,m.__file__,'exec'),m.__dict__)
m.FILES+=['.github/wiki4641_test.py','.github/wiki4642_apply.py','.github/wiki4642_release.py','.github/workflows/wiki4642.yml']
old_excluded=m.excluded
m.excluded=lambda p:old_excluded(p) or p.name in ('FreeInkUIFont.h','gallery_font.h')
README='''# CrossPoint Wiki 4.6.4.2 — indexing-speed experiment

Original Xteink X4 / ESP32-C3 ONLY. Not tested on a physical X4.
Application-only image; not a bootloader, partition table or full-flash image.

## Scope

Based on 4.6.4.1, including its real-HAL guarded-close fix. Library reuse,
source signatures, index namespace and index/checkpoint formats are unchanged.
This release targets on-device indexing throughput, not library-switch behavior.

- Refill the existing 8 KiB scan buffer within one bounded work quantum instead
  of always returning after one buffer. Maximum 64 KiB consumed per step, with
  an 8 ms soft time budget. Slow SD calls can exceed that budget; it is not an
  input-latency guarantee. Timing starts before read(). No 64 KiB allocation.
- Check time after batches of lexer work, not every small plain-text fragment.
- Realign the first source read after resuming at a non-sector-aligned page.
- Process up to four 64-record sorted runs per step and up to 256 merge records
  per step within the same soft budget. Initial sort-run size is still 64.
- Double each merge read cache from 32 to 64 records (3,840 extra bytes total),
  and avoid redundant seeks when the same handle is already at the next record.
  The fixed indexer object remains below its enforced 32 KiB ceiling.
- Refresh ongoing progress every 8 seconds instead of 3. Phase changes, pause,
  errors and completion still request immediate updates. The progress bar stays.
- Show recent observed scan throughput in decimal kB/s. This includes display,
  input and SD overhead; it is not an ETA or a promised whole-import speed.

CPU normal-speed policy, SPI clock/bus mode, panel waveforms, watchdog yielding,
CRC checks, final verification, checkpoint byte/time intervals, recoverable
commits and pause/resume remain enabled and unchanged. No overclocking.
No measured X4 speedup factor or battery improvement is claimed.

## Installation and current import

Do not interrupt a healthy nearly-completed import solely to install this build.
Let it finish, or press Back and wait for PAUSED / checkpoint saved before an
intentional normal exit or shutdown. Never update firmware or remove the card
while indexing is actively writing. Back up /.crosspoint/ and keep known-working
firmware. Use the established compatible original-X4 APPLICATION update route,
selecting the .bin only. Do not erase, repartition, or write the app at 0x0.
The build app0 offset is 0x10000; that does not identify your active OTA slot.

Keep the XML, -464.xwi, .search and .resume-* files. The new version uses the same
formats. Select the same unchanged XML and Confirm to resume a valid checkpoint;
do not press Right, which explicitly restarts the import. A saved checkpoint can
be earlier than the last displayed percentage. Source changes, corrupted data
or failed writes can prevent recovery. Back pauses; Confirm resumes.

The percentage is for the CURRENT STAGE. 72% scanning is not 72% of scanning plus
all sort passes and verification. Scan throughput appears after an update interval.
For comparison, use the same card/file and stage; do not infer an overall speed
factor from host tests or a single percentage reading.

## Unchanged limits

Plain decompressed UTF-8 MediaWiki XML only, not gzip/bzip2/zstd. 64-bit offsets do
not override filesystem limits. Full first scan plus external disk sorting is
still necessary. Individual raw article text is capped at 32768 bytes, with a
256 KiB page-read guard. Unlimited article pagination is not added. Allow ample
SD space for the XML, primary index, two sorting files, backups and checkpoints.
Keep external power connected during long imports.

The CLI build and host tests are release gates, not physical-X4 validation.
Real HalStorage.cpp ownership/assertion logic is compiled by the HAL host test;
the SD driver and mutex primitives are host adapters. A deliberate invalid-handle
control must still assert. No HAL assertions were disabled. No fonts or Wiki data
are distributed as separate assets.
'''
mode=sys.argv[1]
if mode=='prepare':
 assert hashlib.sha256((R/'lib/hal/HalStorage.cpp').read_bytes()).hexdigest()=='683b3178253329c462dd4a6aaa4f95f7c92b9677749ff875ae0147dc7dfae4a3'
 m.prepare()
elif mode=='test':
 m.test()
elif mode=='package':
 after=json.loads((R/'wiki4641-real-hal-results.json').read_text())
 assert after['production_HAL_compiled'] and not after['HalFile_mock_used'] and after['source_unchanged'] and all(x['passed'] for x in after['cases'])
 assert any(x['case']=='raw-empty-close' and x['expected_production_assert'] for x in after['cases'])
 m.package();out=R/'wiki4642-dist'
 for p in sorted(R.glob('wiki4642-*.json'))+sorted(R.glob('wiki4642-*.log')):
  shutil.copyfile(p,out/p.name)
 shutil.copyfile(R/'wiki4641-real-hal-results.json',out/'real-hal-results.json')
 (out/'README.md').write_text(README)
 manifest=json.loads((out/'build-manifest.json').read_text())
 manifest.update({'baseline_version':'1.6.0-wiki-4.6.4.1','baseline_commit':'cbcd8bf73ede03e2849c7f05c0e49cf0443b1754','scope':'Indexing throughput only; unchanged reuse and disk formats','actual_HAL_host_cases':len(after['cases']),'assertion_negative_control':True,'max_scan_step_bytes':65536,'soft_step_budget_ms':8,'merge_cache_records_per_handle':64,'progress_refresh_ms':8000,'device_speedup_measured':False,'checkpoint_format_unchanged':True})
 (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
else:raise SystemExit('Expected prepare, test or package')
