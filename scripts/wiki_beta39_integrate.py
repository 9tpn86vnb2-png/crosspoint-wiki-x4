from pathlib import Path
import hashlib, json

BETA38_EXPECTED = {
    'src/activities/wiki/WikiActivity.cpp': '943f82d2fe1f7089a411ed3ebd8ffe0f8420d60a197018550af3b7b0cd86ae1e',
    'src/activities/wiki/WikiActivity.h': 'cd9488d83936e4f7b27bf66932334bcd10a8f5387cd9a97a46975fe2bfa95925',
    'platformio.local.ini': 'ecacc39f1d9a50c5677e7f47de83e701111ad34d4ac5dc47eb6cc2c72746e83d',
}

BETA39_EXPECTED = {
    'src/activities/wiki/WikiActivity.cpp': '97cfcfef0b14f2eb6a75c8a384e0cadcf516e4b31a2e8d64df8023286b1b6341',
    'src/activities/wiki/WikiActivity.h': '6f9d1d5ce5653a89b0f150eb14b5afc12de64cc051ddd718570c8cb2c72c8729',
    'platformio.local.ini': 'c03d4b6dd1126dbd5e57037709a7e2b46e8fb9ff5eeb0be841152dcae52958ea',
    'WIKI_BETA39.md': '828633f9798fc6c6876fc4ad028af7657d1021c2ab11513d8678a29cce642500',
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def replace_once(path, old, new):
    p=Path(path); s=p.read_text(); n=s.count(old)
    if n != 1:
        raise SystemExit(f'Expected exactly one beta 3.8 pattern in {path}, found {n}')
    p.write_text(s.replace(old,new))

for name,digest in BETA38_EXPECTED.items():
    actual=sha(name)
    if actual != digest:
        raise SystemExit(f'Beta 3.8 input fingerprint mismatch: {name} {actual}')

p='src/activities/wiki/WikiActivity.h'
replace_once(p,
'  enum class Screen { Home, Results, Bookmarks, Libraries, Article, Options };',
'  enum class Screen { Home, Results, Bookmarks, Libraries, Article, Options, Orientation };')
replace_once(p,
'  const char* orientationLabel() const;\n',
'  const char* orientationLabel() const;\n  bool articleLandscape() const;\n')

p='src/activities/wiki/WikiActivity.cpp'
replace_once(p,
'  if (screen_ == Screen::Options) return 8;\n',
'  if (screen_ == Screen::Options) return 8;\n  if (screen_ == Screen::Orientation) return CrossPointSettings::ORIENTATION_COUNT;\n')
replace_once(p,
'''const char* WikiActivity::orientationLabel() const {\n  switch (SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT) {\n    case CrossPointSettings::PORTRAIT: return "Portrait";\n    case CrossPointSettings::LANDSCAPE_CW: return "Landscape CW";\n    case CrossPointSettings::INVERTED: return "Inverted";\n    case CrossPointSettings::LANDSCAPE_CCW: return "Landscape CCW";\n    default: return "Portrait";\n  }\n}\n''',
'''const char* WikiActivity::orientationLabel() const {\n  switch (SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT) {\n    case CrossPointSettings::PORTRAIT: return "Portrait";\n    case CrossPointSettings::LANDSCAPE_CW: return "Landscape CW";\n    case CrossPointSettings::INVERTED: return "Inverted";\n    case CrossPointSettings::LANDSCAPE_CCW: return "Landscape CCW";\n    default: return "Portrait";\n  }\n}\nbool WikiActivity::articleLandscape() const {\n  if (screen_ != Screen::Article) return false;\n  const uint8_t orientation = SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT;\n  return orientation == CrossPointSettings::LANDSCAPE_CW || orientation == CrossPointSettings::LANDSCAPE_CCW;\n}\n''')
replace_once(p,
'''      case 5: {\n        const uint8_t next = (SETTINGS.orientation + 1) % CrossPointSettings::ORIENTATION_COUNT;\n        applyOrientation(next);\n        status_ = std::string("Orientation: ") + orientationLabel();\n        screen_ = Screen::Article;\n        syncOrientationForScreen();\n        break;\n      }''',
'''      case 5:\n        screen_ = Screen::Orientation;\n        selection_ = SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT;\n        status_.clear();\n        syncOrientationForScreen();\n        break;''')
replace_once(p,
'''  else if (screen_ == Screen::Options) {\n    switch (selection_) {''',
'''  else if (screen_ == Screen::Orientation) {\n    applyOrientation(static_cast<uint8_t>(selection_));\n    status_ = std::string("Orientation: ") + orientationLabel();\n    screen_ = Screen::Article;\n    syncOrientationForScreen();\n    requestUpdate();\n  }\n  else if (screen_ == Screen::Options) {\n    switch (selection_) {''')
replace_once(p,
'''      else if (screen_ == Screen::Options) { screen_ = Screen::Article; syncOrientationForScreen(); requestUpdate(); }\n      else goWikiHome();''',
'''      else if (screen_ == Screen::Orientation) { screen_ = Screen::Options; selection_ = 5; syncOrientationForScreen(); requestUpdate(); }\n      else if (screen_ == Screen::Options) { screen_ = Screen::Article; syncOrientationForScreen(); requestUpdate(); }\n      else goWikiHome();''')
replace_once(p,
'''  const char* heading = screen_ == Screen::Results ? "Search results" : screen_ == Screen::Bookmarks ? "Saved articles" : screen_ == Screen::Libraries ? "Choose library" : "Article options";''',
'''  const char* heading = screen_ == Screen::Results ? "Search results" : screen_ == Screen::Bookmarks ? "Saved articles" : screen_ == Screen::Libraries ? "Choose library" : screen_ == Screen::Orientation ? "Reading orientation" : "Article options";''')
replace_once(p,
'''  const auto subtitle = renderer.truncatedText(SMALL_FONT_ID,(screen_ == Screen::Results ? query_ : screen_ == Screen::Options ? title_ : screen_ == Screen::Libraries ? std::string("Current: ")+libraryName_ : "Saved on your SD card").c_str(),w-2*side);''',
'''  const auto subtitle = renderer.truncatedText(SMALL_FONT_ID,(screen_ == Screen::Results ? query_ : screen_ == Screen::Options ? title_ : screen_ == Screen::Orientation ? std::string("Current: ")+orientationLabel() : screen_ == Screen::Libraries ? std::string("Current: ")+libraryName_ : "Saved on your SD card").c_str(),w-2*side);''')
replace_once(p,
'''  std::string orientationOption = std::string("Orientation: ") + orientationLabel();\n  const char* options[] = {bookmarks_.contains(entry_.key) ? "Remove Saved Article" : "Save Article", "Random article", "Search Wikipedia", "Text options", smoothText_ ? "Text smoothing: On" : "Text smoothing: Off", orientationOption.c_str(), cleanView_ ? "Show original pack text" : "Use clean reading view", "Back to article"};''',
'''  const char* options[] = {bookmarks_.contains(entry_.key) ? "Remove Saved Article" : "Save Article", "Random article", "Search Wikipedia", "Text options", smoothText_ ? "Text smoothing: On" : "Text smoothing: Off", "Orientation >", cleanView_ ? "Show original pack text" : "Use clean reading view", "Back to article"};\n  const char* orientations[] = {"Portrait", "Landscape CW", "Inverted", "Landscape CCW"};\n  static_assert(sizeof(orientations) / sizeof(orientations[0]) == CrossPointSettings::ORIENTATION_COUNT, "orientation menu");''')
replace_once(p,
'''    const std::string label = screen_ == Screen::Results ? matches_[i].label : screen_ == Screen::Bookmarks ? bookmarks_.items()[i].title :\n        screen_ == Screen::Libraries ? ((size_t(i) == libraryIndex_ ? std::string("* ") : std::string("  ")) + libraries_[i].label) : options[i];''',
'''    const std::string label = screen_ == Screen::Results ? matches_[i].label : screen_ == Screen::Bookmarks ? bookmarks_.items()[i].title :\n        screen_ == Screen::Libraries ? ((size_t(i) == libraryIndex_ ? std::string("* ") : std::string("  ")) + libraries_[i].label) :\n        screen_ == Screen::Orientation ? ((i == SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT ? std::string("* ") : std::string("  ")) + orientations[i]) : options[i];''')
replace_once(p,
'''  const int top=y,bottom=h-m.buttonHintsHeight-2*smallHeight-18;''',
'''  const int hintsHeight = articleLandscape() ? 0 : m.buttonHintsHeight;\n  const int top=y,bottom=h-hintsHeight-2*smallHeight-18;''')
replace_once(p,
'''  if (!status_.empty()) {\n    const auto text = renderer.truncatedText(SMALL_FONT_ID,status_.c_str(),renderer.getScreenWidth()-48);\n    renderer.drawText(SMALL_FONT_ID,24,renderer.getScreenHeight()-m.buttonHintsHeight-renderer.getLineHeight(SMALL_FONT_ID)-6,text.c_str());\n  }\n  const auto labels = mappedInput.mapLabels(screen_ == Screen::Home ? "Home" : "Back",loadError_ ? "" : screen_ == Screen::Article ? "Options" : screen_ == Screen::Home && selection_ == 0 ? "Search" : "Open",loadError_ ? "" : "Prev",loadError_ ? "" : "Next");\n  GUI.drawButtonHints(renderer,labels.btn1,labels.btn2,labels.btn3,labels.btn4);''',
'''  const bool hideArticleHints = articleLandscape();\n  if (!status_.empty()) {\n    const auto text = renderer.truncatedText(SMALL_FONT_ID,status_.c_str(),renderer.getScreenWidth()-48);\n    const int hintsHeight = hideArticleHints ? 0 : m.buttonHintsHeight;\n    renderer.drawText(SMALL_FONT_ID,24,renderer.getScreenHeight()-hintsHeight-renderer.getLineHeight(SMALL_FONT_ID)-6,text.c_str());\n  }\n  if (!hideArticleHints) {\n    const auto labels = mappedInput.mapLabels(screen_ == Screen::Home ? "Home" : "Back",loadError_ ? "" : screen_ == Screen::Article ? "Options" : screen_ == Screen::Home && selection_ == 0 ? "Search" : "Open",loadError_ ? "" : "Prev",loadError_ ? "" : "Next");\n    GUI.drawButtonHints(renderer,labels.btn1,labels.btn2,labels.btn3,labels.btn4);\n  }''')

p=Path('platformio.local.ini'); s=p.read_text()
if s.count('1.6.0-wiki-beta3.8') != 2:
    raise SystemExit('Unexpected beta 3.8 version count in platformio.local.ini')
p.write_text(s.replace('1.6.0-wiki-beta3.8','1.6.0-wiki-beta3.9'))

Path('WIKI_BETA39.md').write_text('''# CrossPoint Wiki beta 3.9 — original X4/X3 only\n\n- Article Options now opens a dedicated Reading orientation submenu instead of cycling orientations one press at a time.\n- The submenu lists Portrait, Landscape CW, Inverted, and Landscape CCW, marks the current choice, and applies the selected orientation when confirmed.\n- Back from Reading orientation returns to Article Options without changing the saved orientation.\n- Wiki navigation/menu screens remain portrait as in beta 3.8.\n- In Landscape CW and Landscape CCW article views, the four bottom button-guide tabs are hidden and the reclaimed height is used for article pagination.\n- Portrait and Inverted article views keep the normal button-guide tabs.\n- Includes beta 3.8 native CrossPoint battery/status display and whole-article text smoothing.\n- WCDB `.cdb` only; ZIM is not supported.\n- Application-only ESP32-C3 image; not a full-flash image and not for X4 Pro/X4C.\n- Hardware test still required; keep a known-good firmware image.\n''')

for name,digest in BETA39_EXPECTED.items():
    actual=sha(name)
    if actual != digest:
        raise SystemExit(f'Beta 3.9 output fingerprint mismatch: {name} {actual}')
Path('wiki-beta39-reviewed-source.json').write_text(json.dumps(BETA39_EXPECTED, indent=2) + '\n')
print('Applied beta 3.9 orientation-menu/landscape patch and verified', len(BETA39_EXPECTED), 'production fingerprints.')
