#!/usr/bin/env python3
"""Finalize 4.6.3 from the reconstructed 4.6.2 tree; never patch firmware bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.6.0-wiki-4.6.3"


def replace_once(path, old, new):
    source = path.read_text()
    if source.count(old) != 1:
        raise RuntimeError(f"Ambiguous or missing finalization anchor: {path}")
    path.write_text(source.replace(old, new, 1))


def apply():
    profile = ROOT / "platformio.local.ini"
    source = profile.read_text()
    if source.count("1.6.0-wiki-4.6.2") != 2:
        raise RuntimeError("Expected the exact two 4.6.2 UI/SDK version settings")
    profile.write_text(source.replace("1.6.0-wiki-4.6.2", VERSION))
    persist = ROOT / "lib/Serialization/PersistableStore.cpp"
    replace_once(persist,
        '  const size_t written = serializeJson(doc, out);\n  out.flush();\n  out.close();\n  if (written == 0) {\n',
        '  // 4.6.3: a short write must never replace the last complete document.\n'
        '  const size_t expected = measureJson(doc);\n'
        '  const size_t written = serializeJson(doc, out);\n'
        '  out.flush();\n  out.close();\n'
        '  if (expected == 0 || written != expected) {\n')
    replace_once(persist,
        '  if (Storage.exists(path) && !Storage.remove(path)) {\n',
        '  // Reopen after flush/close and compare without allocating a JSON string.\n'
        '  // This also catches a stream that reports success but stores fewer bytes.\n'
        '  HalFile verified;\n'
        '  if (!Storage.openFileForRead("PERSIST", tmpPath, verified)) {\n'
        '    Storage.remove(tmpPath.c_str());\n'
        '    LOG_ERR("PERSIST", "Failed to verify temp file for %s", path);\n'
        '    return false;\n'
        '  }\n'
        '  JsonComparePrint verify(verified);\n'
        '  serializeJson(doc, verify);\n'
        '  const bool complete = verify.equalAtEnd();\n'
        '  verified.close();\n'
        '  if (!complete) {\n'
        '    Storage.remove(tmpPath.c_str());\n'
        '    LOG_ERR("PERSIST", "Temp file verification failed for %s", path);\n'
        '    return false;\n'
        '  }\n'
        '  if (Storage.exists(path) && !Storage.remove(path)) {\n')
    replace_once(persist,
        '  Storage.mkdir("/.crosspoint");\n',
        '  // Reject an incomplete in-memory snapshot before touching stored data.\n'
        '  if (doc.overflowed()) {\n'
        '    LOG_ERR("PERSIST", "JSON allocation failed for %s", path);\n'
        '    return false;\n'
        '  }\n'
        '  Storage.mkdir("/.crosspoint");\n')
    print("4.6.3 applied: UI/SDK version and bounded streaming save verification.")


def package():
    # Keep the established application-image validator and source manifest.
    source = (ROOT / '.github/wiki462_package.sh').read_text()
    source = source.replace('4.6.2', '4.6.3')
    source = source.replace("    'src/main.cpp',", "    'src/main.cpp',\n"
        "    '.github/wiki463_finalize.py',\n"
        "    '.github/wiki463_tests.py',\n"
        "    '.github/workflows/wiki463.yml',")
    subprocess.run(['bash', '-euo', 'pipefail', '-c', source], cwd=ROOT, check=True)
    out = ROOT / 'wiki-dist'
    for name in ['wiki463-final-tests.log', 'wiki463-test-report.json']:
        (out/name).write_bytes((ROOT/name).read_bytes())
    notes = '''CrossPoint Wiki 4.6.3 — original Xteink X4 / ESP32-C3 only

This is a compiled application-only firmware, NOT a merged flash image.
Display/SDK version: 1.6.0-wiki-4.6.3. Not for X4 Pro, X4C, or ESP32-S3.
Use the same custom APPLICATION firmware upload method as the previous Wiki builds.
Never write this application image to address 0x0. Its build app0 offset is 0x10000.
No bootloader, partition table or font files are distributed in this package.
Back up your SD card and retain your known-working firmware before testing.

Scope: recovered 4.6.2 integrated feature set, finalized as 4.6.3 with a targeted
JSON short-write/read-back verification fix and read-only final-tree host tests.
The earlier 4.6.3 preparation branches contained no additional feature patch.
Wiki font controls, headings, logo, saved articles, tables, Finished Books and
10 ms low-clock Power Saving input cadence are retained.
Times New Roman is not embedded: the existing user-installed SD font mechanism
is retained. This package includes no font assets and no Wikipedia data pack.

Validated: actual ESP32-C3 compilation and image/partition/version checks;
source hashes before/after final host tests; fault-injected production JSON
writer function; actual Wiki parser/table/heading/decoder host tests.
Not validated: boot/display/input/battery behaviour on a physical X4, the
partition table currently installed on your device, or all real-world articles.
The existing remove-then-rename commit sequence is unchanged. This patch rejects
short/corrupt temporary writes; it does NOT claim power-loss-atomic FAT updates.
See build-manifest.json, image-info.txt and wiki463-test-report.json for evidence.
'''
    (out/'README-4.6.3.txt').write_text(notes)
    manifest_path = out/'build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['release_scope'] = '4.6.2 integration completion; targeted JSON short-write/read-back fix'
    manifest['final_tree_test_report'] = json.loads((ROOT/'wiki463-test-report.json').read_text())
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    sums = [hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name
            for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS.txt']
    (out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['apply', 'package'])
    args = parser.parse_args()
    {'apply': apply, 'package': package}[args.mode]()
