#!/usr/bin/env python3
"""Keep the beta 1 image-validation gates and extend the verified beta 2 package."""
import hashlib
import json
import shutil
import tarfile
import wiki_package as base

EXTRAS = [
    'scripts/wiki_beta2_integrate.py', 'scripts/wiki_beta2_package.py', 'scripts/wiki_beta2_tests.py',
    'src/components/icons/wikiGlobe.h', 'src/components/UiAppHelpers.h',
    'src/components/themes/BaseTheme.h', 'src/components/themes/BaseTheme.cpp',
    'src/components/themes/lyra/LyraTheme.cpp', 'src/components/themes/roundedraff/RoundedRaffTheme.cpp',
    '.github/workflows/wiki-x4-beta.yml', 'WIKI_BETA2.md',
]

def main():
    base.NAME = 'crosspoint-1.6.0-wiki-beta2-x4-UNTESTED.bin'
    base.UI_VERSION = '1.6.0-wiki-beta2'
    # The original validator checks the configured SDK descriptor version,
    # ESP32-C3 image, actual partition table, native-decoder fix and esptool.
    base.main()
    root, out = base.ROOT, base.OUT
    manifest = json.loads((out/'build-manifest.json').read_text())
    hashes = manifest['compiled_and_supporting_source_sha256']
    for name in EXTRAS:
        hashes[name] = hashlib.sha256((root/name).read_bytes()).hexdigest()
    manifest['features'] = ['Search-first Wiki landing screen', '16-row bounded title results',
        'Visible random action', '64-entry / 16 KiB SD bookmark snapshots',
        'Globe menu icon', 'Clean and original pack text views']
    manifest['images_supported'] = False
    manifest['wiki_data_changed'] = False
    manifest['bookmark_files'] = ['/.crosspoint/wiki/bookmarks.a', '/.crosspoint/wiki/bookmarks.b']
    manifest['hardware_tested'] = False
    manifest['ui_test_boundary'] = 'Host adapters and test fonts; not physical-device verification'
    (out/'build-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with tarfile.open(out/'wiki-changed-source.tar.gz','w:gz') as archive:
        for name in sorted(hashes): archive.add(root/name,arcname=name)
    for name in ['WIKI_BETA2.md','wiki-beta2-tests.log']:
        shutil.copy2(root/name,out/name)
    sums = [hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name
            for p in sorted(out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt']
    (out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')
    print('Beta 2 package finalized with all '+str(len(hashes))+' source fingerprints; no firmware bytes patched.')

if __name__=='__main__': main()
