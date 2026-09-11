#!/usr/bin/env python3
"""Read-only image validation and beta packaging. Never flashes a device."""
import functools
import hashlib
import json
import operator
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
from wiki_harden import harden

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '.pio/build/wiki_x4_beta'
OUT = ROOT / 'wiki-dist'
NAME = 'crosspoint-1.6.0-wiki-beta1-x4-UNTESTED.bin'
UI_VERSION = '1.6.0-wiki-beta1'

def inspect(data):
    def require(condition, message):
        if not condition: raise ValueError(message)
    require(len(data) >= 256 and data[0] == 0xe9 and 1 <= data[1] <= 16, 'Bad image header')
    require(struct.unpack_from('<H', data, 12)[0] == 5, 'Not an ESP32-C3 application')
    require(data[23] == 1, 'Missing appended image SHA-256')
    cursor, checksum = 24, 0xef
    for index in range(data[1]):
        require(cursor + 8 <= len(data), 'Truncated segment header')
        address, size = struct.unpack_from('<II', data, cursor)
        cursor += 8
        require(cursor + size <= len(data), 'Truncated segment')
        if index == 0:
            require(size >= 176 and data[cursor:cursor+4] == b'\x32\x54\xcd\xab', 'No application descriptor')
            raw_version = data[cursor+16:cursor+48]
            require(b'\0' in raw_version, 'Unterminated application version')
            version = raw_version.split(b'\0')[0].decode('ascii')
            require(bool(version), 'Empty application descriptor version')
        checksum = functools.reduce(operator.xor, data[cursor:cursor+size], checksum)
        cursor += size
    end = (cursor // 16) * 16 + 16
    require(end + 32 == len(data), 'Unexpected trailing bytes or truncated image footer')
    require(data[end-1] == checksum, 'Image checksum failed')
    require(all(x == 0 for x in data[cursor:end-1]), 'Nonzero image padding')
    require(hashlib.sha256(data[:end]).digest() == data[end:], 'Appended SHA-256 failed')
    return {'chip': 'ESP32-C3', 'app_descriptor_version': version, 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(), 'checksum_valid': True, 'appended_sha256_valid': True}

def partitions(data):
    result, md5_ok = [], False
    for offset in range(0, min(len(data), 0xc00), 32):
        record = data[offset:offset+32]
        if len(record) != 32: raise ValueError('Truncated partition table')
        if record[:2] == b'\xeb\xeb':
            if record[16:] != hashlib.md5(data[:offset]).digest(): raise ValueError('Partition MD5 failed')
            md5_ok = True
            break
        if record[:2] != b'\xaa\x50': raise ValueError('Unexpected partition record')
        _, kind, subtype, start, size, label, flags = struct.unpack('<HBBII16sI', record)
        if not size or start + size > 16 * 1024 * 1024: raise ValueError('Invalid partition bounds')
        result.append({'label': label.split(b'\0')[0].decode(), 'type': kind,
            'subtype': subtype, 'offset': start, 'size': size})
    if not md5_ok: raise ValueError('No partition checksum')
    ordered = sorted(result, key=lambda p: p['offset'])
    for left, right in zip(ordered, ordered[1:]):
        if left['offset'] + left['size'] > right['offset']: raise ValueError('Overlapping partitions')
    return result

def main():
    harden(check_only=True)
    image = (BUILD / 'firmware.bin').read_bytes()
    info = inspect(image)
    # The Arduino/ESP-IDF application descriptor uses git-describe, whereas
    # CrossPoint's on-screen release name comes from CROSSPOINT_VERSION.
    # Preserve and verify both instead of treating the two as interchangeable.
    expected_git_version = subprocess.check_output(
        ['git', 'describe', '--tags', '--always', '--dirty'], cwd=ROOT, text=True).strip()
    if info['app_descriptor_version'] != expected_git_version:
        raise ValueError('Application descriptor does not match this source checkout: '
            + repr(info['app_descriptor_version']) + ' != ' + repr(expected_git_version))
    expected_flag = '-DCROSSPOINT_VERSION=\\"' + UI_VERSION + '\\"'
    if expected_flag not in (ROOT / 'platformio.local.ini').read_text():
        raise ValueError('The custom beta display-version flag is missing')
    if UI_VERSION.encode('ascii') + b'\0' not in image:
        raise ValueError('Custom beta display version absent from compiled application')
    table = partitions((BUILD / 'partitions.bin').read_bytes())
    apps = [p for p in table if p['type'] == 0]
    if not apps or any(len(image) > p['size'] for p in apps): raise ValueError('Firmware does not fit application slots')
    first = next((p for p in apps if p['label'] == 'app0'), None)
    if not first or first['offset'] != 0x10000 or first['size'] != 0x640000:
        raise ValueError('Unexpected build partition layout')
    broken = bytearray(image); broken[256] ^= 1
    try: inspect(bytes(broken))
    except ValueError: pass
    else: raise ValueError('Corruption self-test failed')
    OUT.mkdir(exist_ok=False)
    (OUT / NAME).write_bytes(image)
    log = subprocess.run([sys.executable, '-m', 'esptool', 'image-info', str(BUILD / 'firmware.bin')],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    (OUT / 'image-info.txt').write_text(log)
    source_names = [str(path.relative_to(ROOT)) for path in sorted((ROOT/'src/activities/wiki').glob('*')) if path.is_file()]
    source_names += ['src/activities/ActivityManager.h', 'src/activities/home/HomeActivity.h',
        'src/activities/home/HomeActivity.cpp', 'lib/uzlib/src/tinflate.c', 'platformio.local.ini',
        'scripts/wiki_integrate.py', 'scripts/wiki_harden.py', 'scripts/wiki_package.py',
        'scripts/wiki_host_tests.py', 'scripts/wiki_native_verify.py']
    source_hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
    manifest = {'artifact': NAME, 'image': info, 'ui_version': UI_VERSION,
        'expected_git_descriptor_version': expected_git_version,
        'descriptor_matches_source_checkout': True,
        'custom_display_version_found_in_image': True,
        'build_partitions': table,
        'crosspoint_base': '54337e6d73fc628f4ba523ddc89a743ca8c6e4c5',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'submodules': subprocess.check_output(['git', 'submodule', 'status', '--recursive'], cwd=ROOT, text=True).strip(),
        'github_run_id': os.getenv('GITHUB_RUN_ID'), 'hardware_tested': False,
        'format': 'WCDB; not ZIM', 'image_kind': 'application-only, not a merged full-flash image',
        'device_partition_layout_verified': False,
        'compiled_and_supporting_source_sha256': source_hashes,
        'decoder_negative_symbol_bounds_fix_verified': True}
    (OUT / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for name in ['WIKI_BETA.md', 'WIKI_VALIDATION.md', 'LICENSE', 'wiki-host-tests.log', 'wiki-build.log', 'wiki-real-pack-report.json']:
        path = ROOT / name
        if path.is_file(): shutil.copy2(path, OUT / name)
    (OUT / 'build-dependencies.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True))
    # Include modified C/C++ sources with their notices, never font assets.
    with tarfile.open(OUT / 'wiki-changed-source.tar.gz', 'w:gz') as archive:
        for name in source_names: archive.add(ROOT/name, arcname=name)
    sums = []
    for path in sorted(OUT.iterdir()):
        if path.is_file(): sums.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name)
    (OUT / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
