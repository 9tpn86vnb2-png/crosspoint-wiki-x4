#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from pathlib import Path
p = Path('scripts/wiki_package.py')
s = p.read_text()
for old in [
    'crosspoint-1.6.0-wiki-beta1-x4-UNTESTED.bin',
    'crosspoint-1.6.0-wiki-4.4.1-x4-UNTESTED.bin',
    'crosspoint-1.6.0-wiki-4.4.2-x4-UNTESTED.bin',
]:
    s = s.replace(old, 'crosspoint-1.6.0-wiki-4.5.0-x4-UNTESTED.bin')
for old in [
    "UI_VERSION = '1.6.0-wiki-beta1'",
    "UI_VERSION = '1.6.0-wiki-4.4.1'",
    "UI_VERSION = '1.6.0-wiki-4.4.2'",
]:
    s = s.replace(old, "UI_VERSION = '1.6.0-wiki-4.5.0'")
needle = "    source_hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}\n"
replacement = "    source_names += ['lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp', 'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h', '.github/wiki450_scoped_exceptions.py']\n" + needle
if needle not in s:
    raise SystemExit('4.5.0 package: source manifest anchor not found')
s = s.replace(needle, replacement, 1)
if "NAME = 'crosspoint-1.6.0-wiki-4.5.0-x4-UNTESTED.bin'" not in s:
    raise SystemExit('4.5.0 package: artifact name replacement failed')
if "UI_VERSION = '1.6.0-wiki-4.5.0'" not in s:
    raise SystemExit('4.5.0 package: UI version replacement failed')
p.write_text(s)
PY
python scripts/wiki_package.py 2>&1 | tee wiki-package.log
