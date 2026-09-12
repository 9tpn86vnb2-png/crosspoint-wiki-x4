#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, io, json, tarfile

ROOT = Path(__file__).resolve().parents[1]
PARTS = ['wiki-beta43-overlay.b64.part00']
OVERLAY_SHA256 = '906fbabd2d3e3e0ecee2cb7860e80879823acba5be26c80659a45351e9782bb7'

BETA42_EXPECTED = {'src/activities/wiki/WikiArchive.cpp': 'ad6631123d29a430262798dffdb2857b1b7316897aadaf5ed9b256c59bb0211f', 'src/activities/wiki/WikiText.cpp': 'dd084174b1c7bb0a9efae3df02706cc8b3c543cea19abf2c1e8338cc9e16b94a', 'src/activities/wiki/WikiText.h': '8416d41ea9c98fbc47f2772991a25d7940ab173c04ede0baa6c286755deedc11', 'src/activities/wiki/WikiActivity.cpp': '4a3f47005af7689028843c681b2dd55f5c7f122971651570d0ca669a2d17639c', 'src/activities/wiki/WikiActivity.h': '5e792a7ecd28c75a851768e8faa53bfb330eb0a445a36a0a1bb3a256fa148f22', 'platformio.local.ini': 'b2c60281af5b7dfdf6733a905e1ae36b6c4b8cc6234d475fed589a6d89c2258d', 'WIKI_BETA42.md': 'dc6e5651d1ed893de73b0df9b1b074840010999ff173f1a904777f591a3d2852'}

BETA43_EXPECTED = {'src/activities/wiki/WikiArchive.cpp': '8010acf4616c44fc2152f5c4bdff3699c4c42015995fd5e89745ea9196c85dcf', 'src/activities/wiki/WikiText.cpp': 'de4ed0bcb8911f309c6c5ab673cd217d505fa3d188a408f2ba34326cef417c90', 'src/activities/wiki/WikiText.h': 'e55928c3eb3b5a90848e2317d61b8fc0424e90a2be64264d7f19640046cbbf81', 'src/activities/wiki/WikiActivity.cpp': '0c3005fac0aa04d93d74c1f1a7d4cbee9417334c6ba81cfb62f318739e47245e', 'platformio.local.ini': '71dbf50953d4398e2941c169affd98d898b7d347629dfc611cb92c09cfd2e028', 'WIKI_BETA43.md': '03a28d5143720a0ff24ca71c22d29f197cf5f87eccc3314d67936b87f20e3e03'}

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
    verify(BETA42_EXPECTED, 'Wiki 4.2 input fingerprint mismatch')
    encoded = ''.join((ROOT / part).read_text().strip() for part in PARTS)
    payload = base64.b64decode(encoded, validate=True)
    actual_overlay = hashlib.sha256(payload).hexdigest()
    if actual_overlay != OVERLAY_SHA256:
        raise SystemExit(f'Wiki 4.3 overlay mismatch: {actual_overlay}')
    allowed = set(BETA43_EXPECTED)
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tar:
        members = [m for m in tar.getmembers() if m.isfile()]
        names = {m.name for m in members}
        if names != allowed:
            raise SystemExit(f'Wiki 4.3 overlay file set mismatch: {sorted(names)}')
        for member in members:
            data = tar.extractfile(member).read()
            dest = ROOT / member.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    verify(BETA43_EXPECTED, 'Wiki 4.3 production fingerprint mismatch')
    (ROOT / 'wiki-beta43-reviewed-source.json').write_text(json.dumps(BETA43_EXPECTED, indent=2) + '\n')
    print('Applied reviewed Wiki 4.3 spacing/link typography overlay and verified', len(BETA43_EXPECTED), 'production fingerprints.')

if __name__ == '__main__':
    main()
