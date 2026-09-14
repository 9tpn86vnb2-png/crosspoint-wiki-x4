#!/usr/bin/env python3
from pathlib import Path
import subprocess

parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp').read_text()
header = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h').read_text()
ini = Path('platformio.local.ini').read_text()

checks = {
    'HTML hidden suppression': 'strcmp(atts[i], "hidden") == 0' in parser and 'htmlHidden = true;' in parser,
    'ARIA hidden suppression': 'strcmp(atts[i], "aria-hidden") == 0' in parser and 'ariaHidden = true;' in parser,
    'screen reader class suppression': 'screen-reader-only' in parser and 'visually-hidden' in parser and 'sr-only' in parser,
    'inline display none suppression': 'compact.find("display:none")' in parser,
    'inline visibility hidden suppression': 'compact.find("visibility:hidden")' in parser,
    'inline visibility collapse suppression': 'compact.find("visibility:collapse")' in parser,
    'hidden text excluded from position counter': '!(self->skipUntilDepth < self->depth)' in parser,
    'existing table structural parser retained': 'isTableStructuralTag' in parser and 'finishTableRow()' in parser,
    'bounded table columns retained': 'MAX_GRID_TABLE_COLUMNS = 4' in header,
    'bounded table cell words retained': 'MAX_GRID_TABLE_CELL_WORDS = 32' in header,
    'bounded table cell bytes retained': 'MAX_GRID_TABLE_CELL_BYTES = 512' in header,
    '4.4.2 build flag': '-DCROSSPOINT_VERSION=\\"1.6.0-wiki-4.4.2\\"' in ini,
    '4.4.2 app descriptor': 'CONFIG_APP_PROJECT_VER="1.6.0-wiki-4.4.2"' in ini,
    '4.4.1 version removed from build profile': '1.6.0-wiki-4.4.1' not in ini,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL') + ': ' + name)
if failed:
    raise SystemExit('4.4.2 contract failures: ' + ', '.join(failed))

subprocess.run(['git', 'diff', '--check'], check=True)
subprocess.run(['git', '-C', 'freeink-sdk', 'diff', '--check'], check=True)
print(f'{len(checks)} Wiki 4.4.2 EPUB contracts passed.')
