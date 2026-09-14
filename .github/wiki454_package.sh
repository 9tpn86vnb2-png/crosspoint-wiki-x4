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
    'crosspoint-1.6.0-wiki-4.5.0-x4-UNTESTED.bin',
    'crosspoint-1.6.0-wiki-4.5.1-x4-UNTESTED.bin',
    'crosspoint-1.6.0-wiki-4.5.2-x4-UNTESTED.bin',
    'crosspoint-1.6.0-wiki-4.5.3-x4-UNTESTED.bin',
]:
    s = s.replace(old, 'crosspoint-1.6.0-wiki-4.5.4-x4-UNTESTED.bin')
for old in [
    "UI_VERSION = '1.6.0-wiki-beta1'",
    "UI_VERSION = '1.6.0-wiki-4.4.1'",
    "UI_VERSION = '1.6.0-wiki-4.4.2'",
    "UI_VERSION = '1.6.0-wiki-4.5.0'",
    "UI_VERSION = '1.6.0-wiki-4.5.1'",
    "UI_VERSION = '1.6.0-wiki-4.5.2'",
    "UI_VERSION = '1.6.0-wiki-4.5.3'",
]:
    s = s.replace(old, "UI_VERSION = '1.6.0-wiki-4.5.4'")
needle = "    source_hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}\n"
extras = [
    'lib/Epub/Epub/Page.cpp',
    'lib/Epub/Epub/Page.h',
    'lib/Epub/Epub/Section.cpp',
    'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp',
    'lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h',
    'lib/hal/HalPowerManager.cpp',
    'lib/hal/HalPowerManager.h',
    '.github/wiki450_scoped_exceptions.py',
    '.github/wiki451_apply.py',
    '.github/wiki452_apply.py',
    '.github/wiki453_apply.py',
    '.github/wiki453_apply.b64.00',
    '.github/wiki453_apply.b64.01',
    '.github/wiki453_apply.b64.02',
    '.github/wiki453_apply.b64.03',
    '.github/wiki453_apply.b64.04',
    '.github/wiki453_contract_tests.py',
    '.github/wiki453_contract_tests.b64.00',
    '.github/wiki453_contract_tests.b64.01',
    '.github/wiki454_apply.py',
    '.github/wiki454_contract_tests.py',
    'src/CrossPointSettings.cpp',
    'src/CrossPointSettings.h',
    'src/FinishedBooksStore.cpp',
    'src/FinishedBooksStore.h',
    'src/RecentBooksStore.cpp',
    'src/RecentBooksStore.h',
    'src/activities/home/RecentBooksActivity.cpp',
    'src/activities/home/RecentBooksActivity.h',
    'src/activities/reader/ReaderActivity.cpp',
    'src/activities/reader/ReaderActivity.h',
    'src/activities/reader/EpubReaderActivity.cpp',
    'src/activities/reader/EpubReaderActivity.h',
    'src/activities/reader/EpubReaderMenuActivity.cpp',
    'src/activities/reader/EpubReaderMenuActivity.h',
    'src/components/icons/customListIcons.h',
    'src/main.cpp',
]
replacement = "    source_names += " + repr(extras) + "\n" + needle
if needle not in s:
    raise SystemExit('4.5.4 package: source manifest anchor not found')
s = s.replace(needle, replacement, 1)
if "NAME = 'crosspoint-1.6.0-wiki-4.5.4-x4-UNTESTED.bin'" not in s:
    raise SystemExit('4.5.4 package: artifact name replacement failed')
if "UI_VERSION = '1.6.0-wiki-4.5.4'" not in s:
    raise SystemExit('4.5.4 package: UI version replacement failed')
p.write_text(s)
PY
python scripts/wiki_package.py 2>&1 | tee wiki-package.log
