#!/usr/bin/env python3
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
checks = 0

def check(ok: bool, label: str) -> None:
    global checks
    checks += 1
    if not ok:
        raise SystemExit('FAILED: ' + label)
    print('PASS:', label)

expected = json.loads((ROOT / 'wiki-beta43-reviewed-source.json').read_text())
for name, digest in expected.items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    check(actual == digest, 'reviewed source fingerprint ' + name)

archive = (ROOT / 'src/activities/wiki/WikiArchive.cpp').read_text()
text_h = (ROOT / 'src/activities/wiki/WikiText.h').read_text()
text_cpp = (ROOT / 'src/activities/wiki/WikiText.cpp').read_text()
activity = (ROOT / 'src/activities/wiki/WikiActivity.cpp').read_text()
platform = (ROOT / 'platformio.local.ini').read_text()
notes = (ROOT / 'WIKI_BETA43.md').read_text()

check('Link = 4' in text_h and 'LINK_MARKER = 0x1d' in text_h, 'WikiText defines zero-width internal-link state')
check('c != LINK_MARKER' in text_h, 'wrapping preserves the internal-link marker instead of converting it to a space')
check('toggleMask = Link' in text_cpp, 'inline parser toggles link state')
check("style & (Bold | Italic)" in text_cpp, 'font prewarm mask ignores underline-only link state')
check('append(char(WikiText::LINK_MARKER))' in archive, 'MediaWiki internal-link labels are retained as marked spans')
check('file:' in archive.lower() and 'category:' in archive.lower(), 'non-article media/category markup remains excluded from link spans')
check('(style & WikiText::Link)' in activity and 'renderer.drawLine(x,underlineY' in activity, 'internal-link spans render an underline')
check('fontStyle(style)' in activity, 'underline composes with existing bold/italic face selection')
check('naturalGaps' in activity and 'stretch=width-wordWidth-naturalGaps' in activity, 'justification separates natural spacing from extra stretch')
check('count>=4' in activity, 'short lines are not aggressively justified')
check('stretch*4<=naturalGaps*3' in activity, 'additional justification stretch is capped at 75 percent of natural gaps')
check('space*3' not in activity, 'Wiki 4.2 three-times-space justification limit is removed')
check('1.6.0-wiki-4.3' in platform and '1.6.0-wiki-4.2' not in platform, 'firmware version is Wiki 4.3')
check('supplied `enwikiversity-2026-09-01-p1p331750.xml.bz2`' in notes, 'release notes record the real dump used for diagnosis')
check('underlined' in notes.lower() and '75%' in notes, 'release notes document link underline and spacing fix')
print(f'{checks} Wiki 4.3 typography assertions passed. NOT device tests.')
