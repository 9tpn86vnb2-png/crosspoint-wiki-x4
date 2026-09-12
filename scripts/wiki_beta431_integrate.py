#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, io, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PARTS = ['wiki-beta431-overlay.b64.part00']
OVERLAY_SHA256 = '6acb6a8fbb7d9d43cbd26fe27199b0cca531bcb7985a0f32a28e0e5347fb99da'

INPUT = {
    'src/activities/wiki/WikiActivity.cpp': '0c3005fac0aa04d93d74c1f1a7d4cbee9417334c6ba81cfb62f318739e47245e',
    'src/activities/wiki/WikiActivity.h': '5e792a7ecd28c75a851768e8faa53bfb330eb0a445a36a0a1bb3a256fa148f22',
    'src/activities/settings/TextSettingsActivity.cpp': 'c669c887d477dd1d66b0770a1ca42b9c87d84a0b38f98ab7058889651fd4b02a',
    'src/activities/settings/TextSettingsActivity.h': '24a92683c71fa2937b003fb351cfd2555d6335b9f2991e36cba0f134852d97a1',
    'platformio.local.ini': '71dbf50953d4398e2941c169affd98d898b7d347629dfc611cb92c09cfd2e028',
}

OUTPUT = {
    'src/activities/wiki/WikiActivity.cpp': 'b6169192284a820ba917db591848c09d7eb21b04aaeb4c1d5fe9155a94b8531e',
    'src/activities/wiki/WikiActivity.h': 'f158c20b63830475bd91e8fc4961c8a7a52729264e9f9404e17854ac98511e9a',
    'src/activities/settings/TextSettingsActivity.cpp': '3d79c64033846ea271cba92832b9cd1614efc89a35c655f4d70d6754c57bf97b',
    'src/activities/settings/TextSettingsActivity.h': 'e1f5e8aea8d9c5e39ce28b2ab6bb2bfc51e1dc8ef8d4009ac46fcb5b74c368d4',
    'platformio.local.ini': 'c56b295e5ae32ee6163105ff59bea9e68c39318a4b48709f5e5b2e713a538648',
    'WIKI_BETA431.md': '483909d31425de797d4bb6c50c2ae730bc461915255224956bdb41ff8fef28cd',
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(mapping, label):
    for name, expected in mapping.items():
        p = ROOT / name
        if not p.is_file():
            raise SystemExit(f'{label}: missing {name}')
        actual = sha(p)
        if actual != expected:
            raise SystemExit(f'{label}: {name} {actual} != {expected}')

def main():
    verify(INPUT, 'Wiki 4.3.1 input fingerprint mismatch')
    encoded = ''.join(''.join((ROOT / p).read_text().split()) for p in PARTS)
    payload = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != OVERLAY_SHA256:
        raise SystemExit(f'Wiki 4.3.1 overlay mismatch: {actual}')
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tf:
        files = [m for m in tf.getmembers() if m.isfile()]
        names = {m.name for m in files}
        if names != set(OUTPUT):
            raise SystemExit(f'Wiki 4.3.1 overlay file set mismatch: {sorted(names)}')
        for member in files:
            data = tf.extractfile(member).read()
            dest = ROOT / member.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    verify(OUTPUT, 'Wiki 4.3.1 production fingerprint mismatch')
    (ROOT / 'wiki-beta431-reviewed-source.json').write_text(json.dumps(OUTPUT, indent=2) + '\n')
    print('Applied reviewed Wiki 4.3.1 settings/chrome overlay and verified', len(OUTPUT), 'fingerprints.')

if __name__ == '__main__':
    main()
