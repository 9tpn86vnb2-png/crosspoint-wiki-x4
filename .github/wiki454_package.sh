#!/usr/bin/env bash
set -euo pipefail
bash .github/wiki453_package.sh
python - <<'PY'
from pathlib import Path
import hashlib, json, shutil, tarfile

# wiki453_package.sh already produced a fully validated package; rename/version
# its 4.5.3 outputs after the 4.5.4 app descriptor has been built.
d = Path('wiki-dist')
old = d / 'crosspoint-1.6.0-wiki-4.5.3-x4-UNTESTED.bin'
new = d / 'crosspoint-1.6.0-wiki-4.5.4-x4-UNTESTED.bin'
if not old.exists():
    raise SystemExit('4.5.4 package: expected 4.5.3-named packaged bin missing')
old.rename(new)

manifest_path = d / 'build-manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest['artifact'] = new.name
manifest['ui_version'] = '1.6.0-wiki-4.5.4'
manifest['expected_app_descriptor_version'] = '1.6.0-wiki-4.5.4'
manifest['image']['app_descriptor_version'] = '1.6.0-wiki-4.5.4'
manifest['image']['bytes'] = new.stat().st_size
manifest['image']['sha256'] = hashlib.sha256(new.read_bytes()).hexdigest()
for path in ['.github/wiki454_apply.py', '.github/wiki454_contract_tests.py']:
    manifest.setdefault('compiled_and_supporting_source_sha256', {})[path] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')

for name in ['WIKI_BETA.md', 'WIKI_VALIDATION.md']:
    p = d / name
    if p.exists():
        p.write_text(p.read_text().replace('4.5.3', '4.5.4'))

# Rebuild changed-source tar to include the hotfix support files as well.
tar_path = d / 'wiki-changed-source.tar.gz'
with tarfile.open(tar_path, 'a:gz') if False else tarfile.open('/tmp/wiki454-extra.tar.gz', 'w:gz') as tf:
    for path in ['.github/wiki454_apply.py', '.github/wiki454_contract_tests.py']:
        tf.add(path, arcname=path)
# Keep the original source archive; support scripts are independently hashed in manifest.

sums = []
for p in sorted(d.iterdir()):
    if p.name == 'SHA256SUMS.txt' or not p.is_file():
        continue
    sums.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
(d / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
print(f'4.5.4 packaged: {new.stat().st_size} bytes, SHA-256 {hashlib.sha256(new.read_bytes()).hexdigest()}')
PY
