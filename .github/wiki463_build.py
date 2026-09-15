#!/usr/bin/env python3
"""Apply the reviewed integrated-4.6.2 delta, then package actual linked output."""
from pathlib import Path
import base64, hashlib, json, lzma, os, re, shutil, subprocess, sys, tarfile
ROOT = Path('.').resolve()
VERSION = '1.6.0-wiki-4.6.3'
PATCH_HASH = '390fa307e30b6479832aecc3e8f0a1cef99d9e308dd5c06c260cebd68ccb920a'

def source_snapshot(names):
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}

def apply():
    encoded = ''.join((ROOT/f'.github/wiki463-full.patch.xz.b64.{i}').read_text().strip() for i in range(3))
    patch = lzma.decompress(base64.b64decode(encoded, validate=True))
    assert hashlib.sha256(patch).hexdigest() == PATCH_HASH, 'Implementation transport checksum failed'
    subprocess.run(['git','apply','--check','-'],input=patch,check=True)
    subprocess.run(['git','apply','-'],input=patch,check=True)
    names = re.findall(r'^diff --git a/(.+) b/.+$',patch.decode(),re.MULTILINE)
    assert len(names)==20
    assert all(not n.endswith(('.ttf','.otf','.woff','.woff2')) and 'builtinFonts' not in n for n in names)
    assert (ROOT/'platformio.local.ini').read_text().count(VERSION)==2
    (ROOT/'wiki463-applied.patch').write_bytes(patch)
    (ROOT/'wiki463-source-sha256.json').write_text(json.dumps(source_snapshot(names),indent=2)+'\n')
    print('Applied checked 4.6.3 implementation to 20 integrated production files.')
    print(json.dumps(source_snapshot(names),indent=2))

def package():
    sys.path.insert(0,str(ROOT/'scripts'))
    from wiki_package import inspect, partitions
    build=ROOT/'.pio/build/wiki_x4_beta'
    image=(build/'firmware.bin').read_bytes()
    info=inspect(image)
    assert info['app_descriptor_version']==VERSION, info
    assert VERSION.encode()+b'\0' in image
    parts=partitions((build/'partitions.bin').read_bytes())
    apps=[p for p in parts if p['type']==0]
    assert apps and all(len(image)<=p['size'] for p in apps)
    app0=next(p for p in apps if p['label']=='app0')
    assert app0['offset']==0x10000 and app0['size']==0x640000, parts
    bad=bytearray(image);bad[256]^=1
    try: inspect(bytes(bad))
    except (ValueError,AssertionError): pass
    else: raise AssertionError('Modified image escaped checksum validation')
    before=json.loads((ROOT/'wiki463-source-sha256.json').read_text())
    assert source_snapshot(before)==before,'Build changed patched production source'
    out=ROOT/'wiki463-dist';out.mkdir(exist_ok=False)
    name='CrossPoint-Wiki-4.6.3-X4-experimental.bin'
    (out/name).write_bytes(image)
    for n in ['firmware.elf','firmware.map']:
        assert (build/n).is_file(),n
        shutil.copy2(build/n,out/n)
    for n in ['wiki-build.log','wiki463-source-sha256.json','wiki463-applied.patch']:
        shutil.copy2(ROOT/n,out/n)
    (out/'partition-layout.json').write_text(json.dumps(parts,indent=2)+'\n')
    packages=Path.home()/'.platformio/packages'
    size=list(packages.glob('toolchain-riscv*/bin/riscv32*-size'))
    nm=list(packages.glob('toolchain-riscv*/bin/riscv32*-nm'))
    assert size and nm
    (out/'elf-sections.txt').write_text(subprocess.check_output([str(size[0]),'-A',str(build/'firmware.elf')],text=True))
    symbols=subprocess.check_output([str(nm[0]),'-S','--size-sort','--radix=d','-C',str(build/'firmware.elf')],text=True)
    (out/'largest-symbols.txt').write_text('\n'.join(symbols.splitlines()[-100:][::-1])+'\n')
    (out/'esptool-image-info.txt').write_text(subprocess.check_output([sys.executable,'-m','esptool','image-info',str(build/'firmware.bin')],text=True))
    (out/'python-dependencies.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
    # Only changed program code, never font assets or a user's Wikipedia data.
    with tarfile.open(out/'4.6.3-changed-source.tar.gz','w:gz') as tar:
        for n in before: tar.add(ROOT/n,arcname=n)
        for n in ['LICENSE','.github/wiki463_build.py','.github/workflows/wiki463-build.yml']:
            if (ROOT/n).is_file(): tar.add(ROOT/n,arcname=n)
    aj=ROOT/'.pio/libdeps/wiki_x4_beta/ArduinoJson'
    assert (aj/'src/ArduinoJson.h').is_file(), 'Actual build ArduinoJson headers not found'
    with tarfile.open(out/'host-test-ArduinoJson.tar.gz','w:gz') as tar:
        tar.add(aj/'src',arcname='ArduinoJson/src')
        for n in ['LICENSE.txt','library.json']:
            if (aj/n).is_file():tar.add(aj/n,arcname='ArduinoJson/'+n)
    manifest={'version':VERSION,'image':info,'artifact':name,'hardware':'Original Xteink X4 / ESP32-C3 only',
        'experimental':True,'hardware_tested':False,'image_kind':'application-only; not a merged/factory image',
        'app0_offset':hex(app0['offset']),'app_slot_bytes':app0['size'],'slot_headroom_bytes':app0['size']-len(image),
        'baseline_462_image_bytes':5539824,'size_delta_from_462':len(image)-5539824,
        'physical_partition_table_read':False,'patch_sha256':PATCH_HASH,'source_sha256':before,
        'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'submodules':subprocess.check_output(['git','submodule','status','--recursive'],text=True).strip(),
        'github_run_id':os.getenv('GITHUB_RUN_ID'),'firmware_source_unchanged_by_build':True,
        'validation':'Compiled and linked; application checksum/hash, ESP32-C3 chip ID, version, partition bounds and source fingerprints verified. Hardware not tested.'}
    (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'README.txt').write_text('''CrossPoint Wiki 4.6.3 EXPERIMENTAL -- original Xteink X4 only

This is an application-only update, NOT a factory/merged image. Do not write it
at address 0x0. Do not use it for X4 Pro, X4 Classic, X3 or other boards.
Back up your SD card (especially /.crosspoint/) and retain working 4.6.2.
Charge the X4. Use the same compatible custom APPLICATION updater used for
previous Wiki builds, selecting CrossPoint-Wiki-4.6.3-X4-experimental.bin.
Do not erase flash or replace partitions. Do not interrupt power during update.
Your physical partition layout was not read. The linked app0 layout is 0x10000
with a 0x640000-byte slot. ELF/map/JSON/source files are NOT flash images.

Implemented: ordered reader input queue, input-first cooperative preparation,
heap-gated reusable next page, chapter-title caching, consistent completion
percentage, success-aware Finished Books saving with bounded retries, verified
buffered JSON with recoverable replacement, torn catalog-tail repair and
checked appends/replacement, fixed-memory negative lookup accelerator, sorted
SD-backed XML title index with record integrity checks and fallback, off-strip
geometry culling and reusable ruby/bidi preparation. Retains 10ms Power Saving
polling, no explicit light sleep, existing Wiki typography/fonts/settings/tables
and native reader features. No global LTO is enabled or font/language removed.

No measured battery or page-turn performance improvement is claimed. The
32-entry navigation queue explicitly rejects the newest event on overflow.
Idle budgets are cooperative: a synchronous SD/parser call may exceed them.
XML first open can build an extra search sidecar (about 60 bytes per article,
plus merge temporary files); missing space falls back to linear search.
FAT replacement is recoverable, not universally power-loss atomic. Existing
XFB1 records remain compatible; corrupt catalog headers are preserved, not
silently erased. No font files or Wikipedia data packs are included.

Compiled image and source evidence is in build-manifest.json and build logs.
This build has NOT been booted on a physical X4. Test rapid turns, opposing
turns, holds, chapter boundaries, font/rotation changes, grayscale/tables,
Wikipedia search, Saved Articles, completion persistence, sleep/wake and
rollback before relying on the build.
''')
    (out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':
    {'apply':apply,'package':package}[sys.argv[1]]()
