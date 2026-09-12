#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, io, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PARTS = ['wiki-beta42-overlay.b64.part00', 'wiki-beta42-overlay.b64.part01']
OVERLAY_SHA256 = 'fe1299e3d8fe6f5720d05666f9a466bccc17117039f943bee1bd9c3ec8f00713'

BETA41_EXPECTED = {
    'src/activities/wiki/WikiArchive.cpp': '7114b7e411d963bf3f80408d73b71f040781d1bb6d599e6289f483fecd4542cc',
    'src/activities/wiki/WikiText.cpp': '99b0286c4819c2b91173548e9cfe438f37eccf9267fdadb3ee4cc9487016b50e',
    'src/activities/wiki/WikiText.h': '457a1aae1865732ef074bbec9b428eac37a4b1d0bc5be6a0fbbe9a746c465590',
    'src/activities/wiki/WikiActivity.cpp': '459e1647ebfa6347d1e2576a6c7f7078d631e641d89394cab09e69e3c913b3cb',
    'src/activities/wiki/WikiActivity.h': 'eb0c9b69f670f2196fdf252be03a03f9501c40a91191ae602a788030e403a5d2',
    'platformio.local.ini': 'c38ee16d0eb98962928b4690ea42d05d367203b54b3685e8aeae5af9b0e9f8b2',
}

BETA42_EXPECTED = {
    'src/activities/wiki/WikiArchive.cpp': 'ad6631123d29a430262798dffdb2857b1b7316897aadaf5ed9b256c59bb0211f',
    'src/activities/wiki/WikiText.cpp': 'dd084174b1c7bb0a9efae3df02706cc8b3c543cea19abf2c1e8338cc9e16b94a',
    'src/activities/wiki/WikiText.h': '8416d41ea9c98fbc47f2772991a25d7940ab173c04ede0baa6c286755deedc11',
    'src/activities/wiki/WikiActivity.cpp': '4a3f47005af7689028843c681b2dd55f5c7f122971651570d0ca669a2d17639c',
    'src/activities/wiki/WikiActivity.h': '5e792a7ecd28c75a851768e8faa53bfb330eb0a445a36a0a1bb3a256fa148f22',
    'platformio.local.ini': 'b2c60281af5b7dfdf6733a905e1ae36b6c4b8cc6234d475fed589a6d89c2258d',
    'WIKI_BETA42.md': 'dc6e5651d1ed893de73b0df9b1b074840010999ff173f1a904777f591a3d2852',
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(mapping, label):
    for name, expected in mapping.items():
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f'{label}: missing {name}')
        actual = sha(path)
        if actual != expected:
            raise SystemExit(f'{label}: {name} {actual} != {expected}')

def main():
    verify(BETA41_EXPECTED, 'Wiki 4.1 input fingerprint mismatch')
    encoded = ''.join((ROOT / part).read_text().strip() for part in PARTS)
    payload = base64.b64decode(encoded, validate=True)
    actual_overlay = hashlib.sha256(payload).hexdigest()
    if actual_overlay != OVERLAY_SHA256:
        raise SystemExit(f'Wiki 4.2 overlay mismatch: {actual_overlay}')
    allowed = set(BETA42_EXPECTED)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        names = {m.name for m in members}
        if names != allowed:
            raise SystemExit(f'Wiki 4.2 overlay file set mismatch: {sorted(names)}')
        for member in members:
            data = tar.extractfile(member).read()
            dest = ROOT / member.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    verify(BETA42_EXPECTED, 'Wiki 4.2 production fingerprint mismatch')
    (ROOT / 'wiki-beta42-reviewed-source.json').write_text(json.dumps(BETA42_EXPECTED, indent=2) + '\n')
    print('Applied reviewed Wiki 4.2 typography overlay and verified', len(BETA42_EXPECTED), 'production fingerprints.')

if __name__ == '__main__':
    main()
