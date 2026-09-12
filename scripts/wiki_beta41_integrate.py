#!/usr/bin/env python3
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]

BETA40_EXPECTED = {
    'src/activities/wiki/WikiActivity.cpp': 'a9f85cfa4421e695df446524b1d53ab45bb9e7e5b7d96fad0366a23be44a07b6',
    'src/activities/wiki/WikiActivity.h': '3d64ec2d0075447911469cffe41239692350a77d21fe0183f46e41f0544701f0',
    'platformio.local.ini': '0b629afe38ec5ee1caf92cf877b8ff416cb07b8e844d1b2b5e65b1072c00e1c6',
    'WIKI_BETA40.md': '6b7bbb9e01cde6e5a55813f829eee21f2270ed1f25cf9bc1c0cf1ed60360465e',
}

BETA41_EXPECTED = {
    'src/activities/wiki/WikiActivity.cpp': '459e1647ebfa6347d1e2576a6c7f7078d631e641d89394cab09e69e3c913b3cb',
    'src/activities/wiki/WikiActivity.h': 'eb0c9b69f670f2196fdf252be03a03f9501c40a91191ae602a788030e403a5d2',
    'platformio.local.ini': 'c38ee16d0eb98962928b4690ea42d05d367203b54b3685e8aeae5af9b0e9f8b2',
    'WIKI_BETA41.md': 'bd5867792571e45effef11309b291147002f929c5557e4e812237f79a0527eff',
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


def verify(mapping: dict[str, str], label: str) -> None:
    for name, digest in mapping.items():
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f'{label}: missing {name}')
        actual = sha(path)
        if actual != digest:
            raise SystemExit(f'{label}: {name} {actual} != {digest}')


def main() -> None:
    verify(BETA40_EXPECTED, 'Wiki 4.0 input fingerprint mismatch')

    header_path = ROOT / 'src/activities/wiki/WikiActivity.h'
    header = header_path.read_text()
    header = replace_once(
        header,
        '  uint8_t appliedOrientation_ = 0;\n',
        '  uint8_t wikiOrientation_ = 0;\n  uint8_t appliedOrientation_ = 0;\n',
        'Wiki orientation member')
    header_path.write_text(header)

    cpp_path = ROOT / 'src/activities/wiki/WikiActivity.cpp'
    cpp = cpp_path.read_text()
    cpp = replace_once(
        cpp,
        'const char* WikiActivity::orientationLabel() const {\n  switch (SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT) {',
        'const char* WikiActivity::orientationLabel() const {\n  switch (wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT) {',
        'orientation label')
    cpp = replace_once(
        cpp,
        '  const uint8_t orientation = SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT;\n  return orientation == CrossPointSettings::LANDSCAPE_CW || orientation == CrossPointSettings::LANDSCAPE_CCW;',
        '  const uint8_t orientation = wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT;\n  return orientation == CrossPointSettings::LANDSCAPE_CW || orientation == CrossPointSettings::LANDSCAPE_CCW;',
        'landscape state')
    cpp = replace_once(
        cpp,
        '  const uint8_t desired = screen_ == Screen::Article\n      ? SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT;',
        '  const uint8_t desired = screen_ == Screen::Article\n      ? wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT;',
        'screen orientation sync')
    cpp = replace_once(
        cpp,
        '''void WikiActivity::applyOrientation(uint8_t orientation) {\n  orientation %= CrossPointSettings::ORIENTATION_COUNT;\n  const bool changed = SETTINGS.orientation != orientation;\n  if (changed) {\n    SETTINGS.orientation = orientation;\n    SETTINGS.saveToFile();\n    resetPages();\n  }\n  // Orientation is a reader preference. Menus remain portrait even when the\n  // selected article orientation is landscape or inverted.\n  syncOrientationForScreen();\n}''',
        '''void WikiActivity::applyOrientation(uint8_t orientation) {\n  orientation %= CrossPointSettings::ORIENTATION_COUNT;\n  const bool changed = wikiOrientation_ != orientation;\n  if (changed) {\n    wikiOrientation_ = orientation;\n    Preferences preferences;\n    if (preferences.begin("wikibeta", false)) {\n      preferences.putUChar("orient", wikiOrientation_);\n      preferences.end();\n    }\n    resetPages();\n  }\n  // Wiki keeps its own reading orientation. Native book-reader orientation is\n  // neither modified nor followed; Wiki navigation/menu screens stay portrait.\n  syncOrientationForScreen();\n}''',
        'orientation persistence')
    cpp = replace_once(
        cpp,
        '''  std::string savedLibrary;\n  Preferences preferences;\n  if (preferences.begin("wikibeta", true)) {\n    cleanView_ = preferences.getBool("clean", true);\n    smoothText_ = preferences.getBool("smooth", false);\n    const String saved = preferences.getString("library", "");\n    savedLibrary = saved.c_str();\n    preferences.end();\n  }\n  sdFontSystem.ensureLoaded(renderer);''',
        '''  std::string savedLibrary;\n  uint8_t savedWikiOrientation = 0xff;\n  Preferences preferences;\n  if (preferences.begin("wikibeta", true)) {\n    cleanView_ = preferences.getBool("clean", true);\n    smoothText_ = preferences.getBool("smooth", false);\n    savedWikiOrientation = preferences.getUChar("orient", 0xff);\n    const String saved = preferences.getString("library", "");\n    savedLibrary = saved.c_str();\n    preferences.end();\n  }\n  // One-time 4.0 -> 4.1 migration: preserve the orientation the user last saw\n  // in Wiki, then keep the Wiki preference independent from the native reader.\n  if (savedWikiOrientation < CrossPointSettings::ORIENTATION_COUNT) {\n    wikiOrientation_ = savedWikiOrientation;\n  } else {\n    wikiOrientation_ = SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT;\n    Preferences migration;\n    if (migration.begin("wikibeta", false)) {\n      migration.putUChar("orient", wikiOrientation_);\n      migration.end();\n    }\n  }\n  sdFontSystem.ensureLoaded(renderer);''',
        'Wiki orientation load/migration')
    cpp = replace_once(
        cpp,
        '        selection_ = SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT;',
        '        selection_ = wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT;',
        'orientation submenu focus')
    cpp = replace_once(
        cpp,
        '  const uint8_t desiredOrientation = screen_ == Screen::Article\n      ? SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT;',
        '  const uint8_t desiredOrientation = screen_ == Screen::Article\n      ? wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT;',
        'loop orientation sync')
    cpp = replace_once(
        cpp,
        'screen_ == Screen::Orientation ? ((i == SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT ? std::string("* ") : std::string("  ")) + orientations[i]) : options[i];',
        'screen_ == Screen::Orientation ? ((i == wikiOrientation_ % CrossPointSettings::ORIENTATION_COUNT ? std::string("* ") : std::string("  ")) + orientations[i]) : options[i];',
        'orientation submenu marker')
    cpp_path.write_text(cpp)

    platform_path = ROOT / 'platformio.local.ini'
    platform = platform_path.read_text()
    platform = platform.replace('1.6.0-wiki-4.0', '1.6.0-wiki-4.1')
    if platform.count('1.6.0-wiki-4.1') != 2 or '1.6.0-wiki-4.0' in platform:
        raise SystemExit('version patch failed')
    platform_path.write_text(platform)

    (ROOT / 'WIKI_BETA41.md').write_text('''# CrossPoint Wiki 4.1 — original X4/X3 only\n\n- Wiki reading orientation is now independent from the native CrossPoint EPUB/TXT reader orientation.\n- Wiki keeps its own Portrait, Landscape CW, Inverted, or Landscape CCW preference in the existing `wikibeta` preferences namespace.\n- Upgrading from 4.0 performs a one-time migration from the current reader orientation so the Wiki view does not unexpectedly rotate on first launch; after that, changes are independent in both directions.\n- The dedicated Wiki Reading orientation submenu remains portrait and changes only the Wiki article orientation.\n- Wiki navigation/menu screens remain portrait. Landscape CW/CCW article views still hide the button-guide tabs and reclaim the space for article text.\n- All Wiki 4.0 MediaWiki XML and WCDB functionality is preserved.\n- Native reader font/size/alignment settings remain shared by design; only orientation is separated in 4.1.\n- Application-only ESP32-C3 image; not a full-flash image and not for X4 Pro/X4C.\n- Hardware test still required for 4.1; keep the working 4.0 image available until verified.\n''')

    verify(BETA41_EXPECTED, 'Wiki 4.1 production fingerprint mismatch')
    (ROOT / 'wiki-beta41-reviewed-source.json').write_text(json.dumps(BETA41_EXPECTED, indent=2) + '\n')
    print('Applied Wiki 4.1 independent-orientation patch and verified', len(BETA41_EXPECTED), 'production fingerprints.')


if __name__ == '__main__':
    main()
