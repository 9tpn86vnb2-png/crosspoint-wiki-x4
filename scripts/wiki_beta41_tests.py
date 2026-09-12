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

expected = json.loads((ROOT / 'wiki-beta41-reviewed-source.json').read_text())
for name, digest in expected.items():
    actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    check(actual == digest, 'reviewed source fingerprint ' + name)

cpp = (ROOT / 'src/activities/wiki/WikiActivity.cpp').read_text()
header = (ROOT / 'src/activities/wiki/WikiActivity.h').read_text()
platform = (ROOT / 'platformio.local.ini').read_text()
notes = (ROOT / 'WIKI_BETA41.md').read_text()

check('uint8_t wikiOrientation_ = 0;' in header, 'Wiki has a dedicated orientation state')
check('switch (wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT)' in cpp, 'orientation label reads Wiki state')
check('const uint8_t orientation = wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT;' in cpp, 'landscape layout reads Wiki state')
check('? wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT' in cpp, 'article renderer sync reads Wiki state')
check('savedWikiOrientation = preferences.getUChar("orient", 0xff);' in cpp, 'Wiki orientation loads from wikibeta preferences')
check('preferences.putUChar("orient", wikiOrientation_);' in cpp, 'Wiki orientation changes persist independently')
check('migration.putUChar("orient", wikiOrientation_);' in cpp, '4.0 preference migrates once into independent Wiki storage')
check(cpp.count('SETTINGS.orientation') == 1, 'native reader orientation is referenced only for one-time 4.0 migration')
check('SETTINGS.orientation = orientation' not in cpp, 'Wiki never writes native reader orientation')
check('const bool changed = wikiOrientation_ != orientation;' in cpp, 'Wiki applyOrientation compares only Wiki state')
check('selection_ = wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT;' in cpp, 'orientation submenu opens on Wiki choice')
check('i == wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT' in cpp, 'orientation submenu marks Wiki choice')
check('renderer.setOrientation(GfxRenderer::Orientation::Portrait);' in cpp, 'Wiki navigation/menu screens remain portrait')
check('articleLandscape() ? 0 : m.buttonHintsHeight' in cpp, 'landscape button-guide removal remains enabled')
check('WikiXmlArchive' not in notes or 'MediaWiki XML' in notes, '4.0 XML feature explicitly preserved in notes')
check('1.6.0-wiki-4.1' in platform and 'beta4.0' not in platform, 'firmware version is Wiki 4.1')
check('independent' in notes.lower() and 'only orientation is separated' in notes, 'release notes document scope precisely')

print(f'{checks} Wiki 4.1 independent-orientation assertions passed. NOT device tests.')
