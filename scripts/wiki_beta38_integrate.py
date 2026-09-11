from pathlib import Path
import hashlib, json

BETA37_EXPECTED = {
    'src/activities/wiki/WikiActivity.cpp': '0d84728e7a705a5811525ca188b071bd671dda47c0758f7e510dd7dfb590c2dc',
    'src/activities/wiki/WikiActivity.h': 'c0aa38553223808d116e74fcfeb72e98df5b691206c97fb009ff3e1dfaa3db05',
    'platformio.local.ini': '885e80ff8bcedbce8d73ca6de986ba99cb118eb9968b375ce96320a3dc144cf6',
}

BETA38_EXPECTED = {
    'src/activities/wiki/WikiActivity.cpp': '943f82d2fe1f7089a411ed3ebd8ffe0f8420d60a197018550af3b7b0cd86ae1e',
    'src/activities/wiki/WikiActivity.h': 'cd9488d83936e4f7b27bf66932334bcd10a8f5387cd9a97a46975fe2bfa95925',
    'platformio.local.ini': 'ecacc39f1d9a50c5677e7f47de83e701111ad34d4ac5dc47eb6cc2c72746e83d',
}


def sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Expected exactly one beta 3.7 pattern in {path}, found {count}')
    p.write_text(text.replace(old, new))


for name, digest in BETA37_EXPECTED.items():
    actual = sha(name)
    if actual != digest:
        raise SystemExit(f'Beta 3.7 input fingerprint mismatch: {name} {actual}')

p = 'src/activities/wiki/WikiActivity.cpp'
replace_once(
    p,
    '''  if (!entry_.found) { screen_ = Screen::Home; selection_ = 0; status_ = "Article unavailable or damaged"; return; }''',
    '''  if (!entry_.found) {\n    screen_ = Screen::Home; selection_ = 0; status_ = "Article unavailable or damaged";\n    syncOrientationForScreen();\n    return;\n  }''',
)
replace_once(
    p,
    '''  document_.build(entry_.text, cleanView_);\n  screen_ = Screen::Article;\n}''',
    '''  document_.build(entry_.text, cleanView_);\n  screen_ = Screen::Article;\n  syncOrientationForScreen();\n}''',
)
replace_once(
    p,
    '''  sdFontSystem.ensureLoaded(renderer);\n  ReaderUtils::applyOrientation(renderer, SETTINGS.orientation);\n  appliedOrientation_ = SETTINGS.orientation;\n  scanLibraries();''',
    '''  sdFontSystem.ensureLoaded(renderer);\n  // Wiki navigation screens are UI surfaces, so always enter them in portrait.\n  // This does not alter the shared CrossPoint reader orientation setting.\n  renderer.setOrientation(GfxRenderer::Orientation::Portrait);\n  appliedOrientation_ = CrossPointSettings::PORTRAIT;\n  scanLibraries();''',
)
replace_once(
    p,
    '''void WikiActivity::goWikiHome() {\n  screen_ = Screen::Home; selection_ = 0; status_.clear(); matches_.clear(); resetKeys(); requestUpdate();\n}''',
    '''void WikiActivity::goWikiHome() {\n  screen_ = Screen::Home; selection_ = 0; status_.clear(); matches_.clear(); resetKeys();\n  syncOrientationForScreen();\n  requestUpdate();\n}''',
)
replace_once(
    p,
    '''void WikiActivity::applyOrientation(uint8_t orientation) {\n  orientation %= CrossPointSettings::ORIENTATION_COUNT;\n  if (SETTINGS.orientation != orientation) {\n    SETTINGS.orientation = orientation;\n    SETTINGS.saveToFile();\n  }\n  ReaderUtils::applyOrientation(renderer, orientation);\n  appliedOrientation_ = orientation;\n  resetPages();\n}\nvoid WikiActivity::openTextSettings() {''',
    '''void WikiActivity::syncOrientationForScreen() {\n  const uint8_t desired = screen_ == Screen::Article\n      ? SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT;\n  if (appliedOrientation_ == desired) return;\n  if (screen_ == Screen::Article) ReaderUtils::applyOrientation(renderer, desired);\n  else renderer.setOrientation(GfxRenderer::Orientation::Portrait);\n  appliedOrientation_ = desired;\n}\nvoid WikiActivity::applyOrientation(uint8_t orientation) {\n  orientation %= CrossPointSettings::ORIENTATION_COUNT;\n  const bool changed = SETTINGS.orientation != orientation;\n  if (changed) {\n    SETTINGS.orientation = orientation;\n    SETTINGS.saveToFile();\n    resetPages();\n  }\n  // Orientation is a reader preference. Menus remain portrait even when the\n  // selected article orientation is landscape or inverted.\n  syncOrientationForScreen();\n}\nvoid WikiActivity::openTextSettings() {''',
)
replace_once(
    p,
    '''  else if (screen_ == Screen::Article) { screen_ = Screen::Options; selection_ = 0; requestUpdate(); }''',
    '''  else if (screen_ == Screen::Article) { screen_ = Screen::Options; selection_ = 0; syncOrientationForScreen(); requestUpdate(); }''',
)
replace_once(
    p,
    '''      case 0: saveBookmark(); screen_ = Screen::Article; break;''',
    '''      case 0: saveBookmark(); screen_ = Screen::Article; syncOrientationForScreen(); break;''',
)
replace_once(
    p,
    '''        status_ = smoothText_ ? "Text smoothing enabled" : "Text smoothing disabled";\n        screen_ = Screen::Article;\n        break;''',
    '''        status_ = smoothText_ ? "Text smoothing enabled" : "Text smoothing disabled";\n        screen_ = Screen::Article;\n        syncOrientationForScreen();\n        break;''',
)
replace_once(
    p,
    '''        applyOrientation(next);\n        status_ = std::string("Orientation: ") + orientationLabel();\n        screen_ = Screen::Article;\n        break;''',
    '''        applyOrientation(next);\n        status_ = std::string("Orientation: ") + orientationLabel();\n        screen_ = Screen::Article;\n        syncOrientationForScreen();\n        break;''',
)
replace_once(
    p,
    '''      default: screen_ = Screen::Article; break;''',
    '''      default: screen_ = Screen::Article; syncOrientationForScreen(); break;''',
)
replace_once(
    p,
    '''  if (appliedOrientation_ != SETTINGS.orientation) {\n    applyOrientation(SETTINGS.orientation);\n    requestUpdate();\n    return;\n  }''',
    '''  const uint8_t desiredOrientation = screen_ == Screen::Article\n      ? SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT;\n  if (appliedOrientation_ != desiredOrientation) {\n    syncOrientationForScreen();\n    requestUpdate();\n    return;\n  }''',
)
replace_once(
    p,
    '''      else if (screen_ == Screen::Options) { screen_ = Screen::Article; requestUpdate(); }''',
    '''      else if (screen_ == Screen::Options) { screen_ = Screen::Article; syncOrientationForScreen(); requestUpdate(); }''',
)

p = 'src/activities/wiki/WikiActivity.h'
replace_once(
    p,
    '''  void applyOrientation(uint8_t orientation);\n  const char* orientationLabel() const;''',
    '''  void syncOrientationForScreen();\n  void applyOrientation(uint8_t orientation);\n  const char* orientationLabel() const;''',
)

p = Path('platformio.local.ini')
text = p.read_text()
if text.count('1.6.0-wiki-beta3.7') != 2:
    raise SystemExit('Unexpected beta 3.7 version count in platformio.local.ini')
p.write_text(text.replace('1.6.0-wiki-beta3.7', '1.6.0-wiki-beta3.8'))

Path('WIKI_BETA38.md').write_text('''# CrossPoint Wiki beta 3.8 — original X4/X3 only\n\n- Wiki navigation and menu screens always render in portrait.\n- The shared CrossPoint reader orientation is preserved and is applied only when an article is open.\n- Returning from an article to Wiki Home, Search results, Saved articles, Choose library, or Article options returns the UI to portrait without changing the saved reader orientation.\n- Opening or returning to an article reapplies the selected CrossPoint reading orientation.\n- Includes the full beta 3.7 feature set: native CrossPoint battery/percentage, full-text grayscale smoothing, and shared reader orientation controls.\n- WCDB `.cdb` only; ZIM is not supported.\n- Application-only ESP32-C3 image; not a full-flash image and not for X4 Pro/X4C.\n- Hardware test still required; keep a known-good firmware image.\n''')

for name, digest in BETA38_EXPECTED.items():
    actual = sha(name)
    if actual != digest:
        raise SystemExit(f'Beta 3.8 output fingerprint mismatch: {name} {actual}')

Path('wiki-beta38-reviewed-source.json').write_text(json.dumps(BETA38_EXPECTED, indent=2) + '\n')
print('Applied beta 3.8 portrait-menu patch and verified', len(BETA38_EXPECTED), 'production fingerprints.')
