#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str) -> None:
    print('+', ' '.join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def reconstruct_b64(parts: list[str], expected_sha: str, out_name: str) -> Path:
    encoded = ''.join(''.join((ROOT / p).read_text().split()) for p in parts)
    raw = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha:
        raise SystemExit(f'{out_name} SHA mismatch: {actual}')
    out = Path(tempfile.gettempdir()) / out_name
    out.write_bytes(raw)
    print(f'{out_name}: {len(raw)} bytes, SHA-256 {actual}')
    return out


def verify_hash_map(path: Path, base: Path, label: str) -> None:
    for name, digest in json.loads(path.read_text()).items():
        source = base / name
        actual = sha256(source)
        if actual != digest:
            raise SystemExit(f'{label} hash mismatch: {name}: {actual} != {digest}')


def apply_overlay(archive: Path, label: str) -> None:
    work = Path(tempfile.mkdtemp(prefix='wiki-overlay-'))
    try:
        with tarfile.open(archive, 'r:gz') as tf:
            tf.extractall(work, filter='data')
        verify_hash_map(work / 'input-hashes.json', ROOT, label + ' input')
        files = json.loads((work / 'overlay-files-sha256.json').read_text())
        for name, digest in files.items():
            src = work / 'files' / name
            actual = sha256(src)
            if actual != digest:
                raise SystemExit(f'{label} overlay corruption: {name}: {actual}')
            dst = ROOT / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        print(f'Applied {label}: {len(files)} files')
    finally:
        shutil.rmtree(work, ignore_errors=True)
    run('git', 'diff', '--check')


def main() -> None:
    # Start from the pinned CrossPoint 1.6.0 branch state and rebuild every
    # reviewed Wiki layer in the same order used by the successful releases.
    verify_hash_map(ROOT / 'wiki-beta2-reviewed-source.json', ROOT, 'beta 2 baseline')
    run('python', 'scripts/wiki_harden.py')
    run('python', 'scripts/wiki_integrate.py')
    run('python', 'scripts/wiki_beta2_integrate.py')
    run('git', 'diff', '--check')
    run('python', 'scripts/wiki_native_verify.py')
    run('python', 'scripts/wiki_beta2_tests.py')

    beta3 = reconstruct_b64([
        'wiki-beta3-overlay.b64.part00', 'wiki-beta3-overlay.b64.part01',
        'wiki-beta3-overlay.b64.part02', 'wiki-beta3-overlay.b64.part03',
        'wiki-beta3-overlay.b64.part04', 'wiki-beta3-overlay.b64.part05',
        'wiki-beta3-overlay.b64.part06'],
        '67d274746aae27b4d58c5a47e55b16f83eb43112e2cb7b0d3fd877b4a9cc3a2e',
        'wiki-beta3-overlay.tar.gz')
    apply_overlay(beta3, 'beta 3')
    run('python', 'scripts/wiki_beta3_tests.py')
    run('python', 'scripts/wiki_heading_tests.py')

    beta35 = reconstruct_b64([
        'wiki-beta35-overlay.b64.part00', 'wiki-beta35-overlay.b64.part01a',
        'wiki-beta35-overlay.b64.part01b', 'wiki-beta35-overlay.b64.part02'],
        '7a56f4114a721ad6f03da168dfd3b2c129fc6725cb85947fc9677d6f3bc993f8',
        'wiki-beta35-overlay.tar.gz')
    apply_overlay(beta35, 'beta 3.5')
    run('python', 'scripts/wiki_beta35_tests.py')

    beta36 = reconstruct_b64([
        'wiki-beta36-overlay.b64.part00', 'wiki-beta36-overlay.b64.part01',
        'wiki-beta36-overlay.b64.part02a', 'wiki-beta36-overlay.b64.part02b',
        'wiki-beta36-overlay.b64.part03a', 'wiki-beta36-overlay.b64.part03b'],
        '6c7e7ed07abbffca4272f3572a30554c1b5340d6db890bcc7b3dc783b6373989',
        'wiki-beta36-overlay.tar.gz')
    apply_overlay(beta36, 'beta 3.6')
    run('python', 'scripts/wiki_beta36_tests.py')

    run('python', 'scripts/wiki_beta37_integrate.py')
    run('python', 'scripts/wiki_beta38_integrate.py')
    run('python', 'scripts/wiki_beta39_integrate.py')
    run('git', 'diff', '--check')
    run('python', 'scripts/wiki_beta39_tests.py')

    beta40 = reconstruct_b64([
        f'wiki-beta40-overlay.b64.chunk{i:02d}' for i in range(9)],
        '79107fa050bda58f4a51b0e74b4f442deb1cc61ba815f56a7fdbe0ca5ce5b4eb',
        'wiki-beta40-overlay.tar.gz')
    apply_overlay(beta40, 'Wiki 4.0')
    verify_hash_map(ROOT / 'wiki-beta40-reviewed-source.json', ROOT, 'Wiki 4.0 reviewed source')
    run('python', 'scripts/wiki_beta40_xml_tests.py')

    archive_cpp = (ROOT / 'src/activities/wiki/WikiArchive.cpp').read_text()
    archive_h = (ROOT / 'src/activities/wiki/WikiArchive.h').read_text()
    activity = (ROOT / 'src/activities/wiki/WikiActivity.cpp').read_text()
    pio = (ROOT / 'platformio.local.ini').read_text()
    assertions = [
        'MediaWikiXml' in archive_cpp and 'MediaWikiXml' in archive_h,
        'WXMLIDX1' in archive_cpp,
        '.xml' in activity and '[XML]' in activity,
        '1.6.0-wiki-4.0' in pio,
        'wiki-beta3.9' not in pio,
        'XML_INDEX_RECORD_BYTES' in archive_cpp,
        'XML_ARTICLE_MAX' in archive_cpp,
        'builtIndexOnOpen' in archive_cpp,
    ]
    if not all(assertions):
        raise SystemExit('Wiki 4.0 source-contract assertion failed')
    print(f'{len(assertions)} Wiki 4.0 source-contract checks passed.')
    print('Wiki 4.0 integration/test stage complete.')


if __name__ == '__main__':
    main()
