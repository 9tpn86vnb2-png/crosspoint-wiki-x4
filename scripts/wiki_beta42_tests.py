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

expected = json.loads((ROOT / 'wiki-beta42-reviewed-source.json').read_text())
for name, digest in expected.items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    check(actual == digest, 'reviewed source fingerprint ' + name)

archive = (ROOT / 'src/activities/wiki/WikiArchive.cpp').read_text()
text_h = (ROOT / 'src/activities/wiki/WikiText.h').read_text()
text_cpp = (ROOT / 'src/activities/wiki/WikiText.cpp').read_text()
activity = (ROOT / 'src/activities/wiki/WikiActivity.cpp').read_text()
activity_h = (ROOT / 'src/activities/wiki/WikiActivity.h').read_text()
platform = (ROOT / 'platformio.local.ini').read_text()
notes = (ROOT / 'WIKI_BETA42.md').read_text()

check("appendText(\"'''\")" in archive and "appendText(\"''\")" in archive, 'XML simplifier preserves/normalizes emphasis markers')
check('boldOpen' in archive and 'italicOpen' in archive, 'basic HTML bold/italic tags normalize into emphasis markers')
check('enum InlineStyle' in text_h and 'Bold = 1' in text_h and 'Italic = 2' in text_h, 'WikiText exposes compact inline style state')
check('inlineStyleMarker' in text_cpp and 'inlineStyleMask' in text_cpp and 'stripInlineStyles' in text_cpp, 'WikiText implements style parsing, font prewarm mask, and marker stripping')
check('uint8_t level = 0' in text_h and 'level = uint8_t(std::min<size_t>(6, lead - pos))' in text_cpp, 'heading level hierarchy is retained')
check('uint8_t style = Regular' in text_h, 'pagination cursor persists inline style across wrapped lines')
check('renderer.getTextWidth(font,line+begin,fontStyle(style))' in activity, 'styled runs use style-specific font metrics for wrapping')
check('renderer.drawText(font,x,y,line+begin,true,fontStyle(style))' in activity, 'styled runs render with bold/italic font variants')
check('WikiText::inlineStyleMask(warm,n,cursor.style)' in activity, 'SD font prewarm is style-aware')
check('renderer.ensureSdCardFontReady(tf,title_.c_str(),0x02)' in activity, 'article title bold face is prewarmed')
check('block.level<=2 ? 5 : block.level==3 ? 6 : 1' in activity, 'heading levels map to distinct visual scales')
check('XML reading view (typeset)' in activity and 'bold/italic typesetting is always enabled' in activity, 'XML UI describes typeset reading mode')
check('measureRichLine' in activity_h and 'startStyle' in activity_h, 'rich-line API carries style state explicitly')
check('1.6.0-wiki-4.2' in platform and '1.6.0-wiki-4.1' not in platform, 'firmware version is Wiki 4.2')
check('.xml.gz' in notes and 'not added' in notes, 'release scope excludes compressed XML from typography build')
check('bold italic' in notes.lower() and '.cpfont' in notes, 'release notes document emphasis and font-family behavior')

print(f'{checks} Wiki 4.2 typography assertions passed. NOT device tests.')
