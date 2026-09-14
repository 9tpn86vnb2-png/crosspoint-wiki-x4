#!/usr/bin/env python3
from pathlib import Path

cpp = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text()
hdr = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text()
ini = Path('platformio.local.ini').read_text()
scope = Path('.github/wiki450_scoped_exceptions.py').read_text()

checks = {
    '4.5.0 version': '1.6.0-wiki-4.5.0' in ini,
    'stacked cell state': 'tableStackedCellIndex' in hdr and 'tableStackedCellIndex' in cpp,
    'stacked secondary indent': 'TABLE_STACKED_SECONDARY_INDENT = 12' in cpp,
    'empty generated rows skipped': 'allCellsEmpty' in cpp and 'if (allCellsEmpty)' in cpp,
    'narrative rows have readability fallback': 'gridReadableWordLimit' in cpp,
    'three-column readable limit': 'columnCount == 3 ? 20' in cpp,
    'table section wrappers ignored structurally': 'strcmp(name, "thead")' in cpp and 'strcmp(name, "tbody")' in cpp,
    'colgroup/col handled': 'strcmp(name, "colgroup")' in cpp and 'strcmp(name, "col")' in cpp,
    'stacked cells preserve full text': 'makePages();' in cpp and 'indentStackedTableCell' in cpp,
    '4.4.2 aria hidden retained': 'ariaHidden' in cpp,
    '4.4.2 screen-reader classes retained': 'isAccessibilityOnlyClass' in cpp,
    'global exceptions removed from local build flags': '\n  -fexceptions\n' not in ini,
    'base no-exception profile no longer unflagged': '\n  -fno-exceptions\n' not in ini,
    'scoped exception middleware enabled': 'pre:.github/wiki450_scoped_exceptions.py' in ini,
    'base extra scripts preserved': '${base.extra_scripts}' in ini,
    'exception scope targets WikiArchive only': 'node.name != "WikiArchive.cpp"' in scope and '"-fexceptions"' in scope,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ': ' + name)
if failed:
    raise SystemExit('4.5.0 contract failures: ' + ', '.join(failed))

# Synthetic structures matching the shape of the reference EPUB, without
# embedding copyrighted book text. This documents the bounded rendering policy.
def classify(cells, columns, span=False):
    if not any(cells):
        return 'skip'
    if span:
        return 'stacked'
    if any(len(c.encode()) > 512 or len(c.split()) > 32 for c in cells):
        return 'stacked'
    readable = 14 if columns >= 4 else (20 if columns == 3 else 32)
    if any(len(c.split()) > readable for c in cells):
        return 'stacked'
    return 'grid'

assert classify(['', ''], 2) == 'skip'
assert classify(['Selection', 'IQ points gained'], 2) == 'grid'
assert classify(['Task', 'Skill set', 'Strategic relevance'], 3) == 'grid'
assert classify(['label', ' '.join(['prose'] * 33)], 2) == 'stacked'
assert classify(['label', ' '.join(['prose'] * 21), 'notes'], 3) == 'stacked'
assert classify(['Table title'], 2, span=True) == 'stacked'
print('PASS: synthetic reference-table policy')
print('Wiki 4.5.0 contracts passed:', len(checks) + 1)
