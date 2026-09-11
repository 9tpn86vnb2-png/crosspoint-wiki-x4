from pathlib import Path
import hashlib,json

def replace_once(path, old, new):
    p=Path(path); s=p.read_text()
    if s.count(old)!=1:
        raise SystemExit(f'Expected exactly one beta 3.6 pattern in {path}, found {s.count(old)}')
    p.write_text(s.replace(old,new))

# WikiActivity.cpp changes
p='src/activities/wiki/WikiActivity.cpp'
replace_once(p,
'  sdFontSystem.ensureLoaded(renderer);\n  scanLibraries();',
'  sdFontSystem.ensureLoaded(renderer);\n  ReaderUtils::applyOrientation(renderer, SETTINGS.orientation);\n  appliedOrientation_ = SETTINGS.orientation;\n  scanLibraries();')
replace_once(p,
'  archive_.close(); entry_ = {}; matches_.clear();\n  Activity::onExit();',
'  archive_.close(); entry_ = {}; matches_.clear();\n  renderer.setOrientation(GfxRenderer::Orientation::Portrait);\n  appliedOrientation_ = CrossPointSettings::PORTRAIT;\n  Activity::onExit();')
replace_once(p,'  if (screen_ == Screen::Options) return 7;','  if (screen_ == Screen::Options) return 8;')
replace_once(p,
'''void WikiActivity::openTextSettings() {''',
'''const char* WikiActivity::orientationLabel() const {\n  switch (SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT) {\n    case CrossPointSettings::PORTRAIT: return "Portrait";\n    case CrossPointSettings::LANDSCAPE_CW: return "Landscape CW";\n    case CrossPointSettings::INVERTED: return "Inverted";\n    case CrossPointSettings::LANDSCAPE_CCW: return "Landscape CCW";\n    default: return "Portrait";\n  }\n}\nvoid WikiActivity::applyOrientation(uint8_t orientation) {\n  orientation %= CrossPointSettings::ORIENTATION_COUNT;\n  if (SETTINGS.orientation != orientation) {\n    SETTINGS.orientation = orientation;\n    SETTINGS.saveToFile();\n  }\n  ReaderUtils::applyOrientation(renderer, orientation);\n  appliedOrientation_ = orientation;\n  resetPages();\n}\nvoid WikiActivity::openTextSettings() {''')
replace_once(p,
'      case 5: { const auto key = entry_.key; cleanView_ = !cleanView_; openTitle(key); break; }\n      default: screen_ = Screen::Article; break;',
'''      case 5: {\n        const uint8_t next = (SETTINGS.orientation + 1) % CrossPointSettings::ORIENTATION_COUNT;\n        applyOrientation(next);\n        status_ = std::string("Orientation: ") + orientationLabel();\n        screen_ = Screen::Article;\n        break;\n      }\n      case 6: { const auto key = entry_.key; cleanView_ = !cleanView_; openTitle(key); break; }\n      default: screen_ = Screen::Article; break;''')
replace_once(p,
'void WikiActivity::loop() {\n  RenderLock lock;\n  using Button = MappedInputManager::Button;',
'''void WikiActivity::loop() {\n  RenderLock lock;\n  if (appliedOrientation_ != SETTINGS.orientation) {\n    applyOrientation(SETTINGS.orientation);\n    requestUpdate();\n    return;\n  }\n  using Button = MappedInputManager::Button;''')
replace_once(p,
'  const int globeSize = compact ? 64 : 112, logoY = compact ? 8 : 24;\n  WikiLogo::draw(renderer,(w-globeSize)/2,logoY,compact);',
'''  GUI.drawHeader(renderer,Rect{0,m.topPadding,w,m.headerHeight},nullptr);\n  const int globeSize = compact ? 64 : 112;\n  const int logoY = m.topPadding + m.headerHeight + (compact ? 4 : 8);\n  WikiLogo::draw(renderer,(w-globeSize)/2,logoY,compact);''')
replace_once(p,
'  const char* options[] = {bookmarks_.contains(entry_.key) ? "Remove Saved Article" : "Save Article", "Random article", "Search Wikipedia", "Text options", smoothText_ ? "Text smoothing: On" : "Text smoothing: Off", cleanView_ ? "Show original pack text" : "Use clean reading view", "Back to article"};',
'''  std::string orientationOption = std::string("Orientation: ") + orientationLabel();\n  const char* options[] = {bookmarks_.contains(entry_.key) ? "Remove Saved Article" : "Save Article", "Random article", "Search Wikipedia", "Text options", smoothText_ ? "Text smoothing: On" : "Text smoothing: Off", orientationOption.c_str(), cleanView_ ? "Show original pack text" : "Use clean reading view", "Back to article"};''')
replace_once(p,
'''  int y=m.topPadding+8;\n  if (!grayscalePass) {\n    renderer.drawText(SMALL_FONT_ID,side,y,cleanView_ ? "WIKIPEDIA" : "WIKIPEDIA / ORIGINAL PACK TEXT");\n    if (bookmarks_.contains(entry_.key)) {\n      const int savedRight = w-side-m.batteryWidth-14;\n      renderer.drawText(SMALL_FONT_ID,savedRight-renderer.getTextWidth(SMALL_FONT_ID,"Saved"),y,"Saved");\n    }\n  }\n  y+=smallHeight+10;''',
'''  if (!grayscalePass) {\n    GUI.drawHeader(renderer,Rect{0,m.topPadding,w,m.headerHeight},cleanView_ ? "Wikipedia" : "Wikipedia / Original",bookmarks_.contains(entry_.key) ? "Saved" : nullptr);\n  }\n  int y=m.topPadding+m.headerHeight+12;''')
replace_once(p,'    if (!grayscalePass) WikiHeading::draw(renderer,tf,side,y,line.c_str(),4,3,w-side,y+titleHeight);','    WikiHeading::draw(renderer,tf,side,y,line.c_str(),4,3,w-side,y+titleHeight);')
replace_once(p,'      if (!grayscalePass) WikiHeading::draw(renderer,font,side,y,line,6,5,w-side,std::min(bottom,y+lineHeight));','      WikiHeading::draw(renderer,font,side,y,line,6,5,w-side,std::min(bottom,y+lineHeight));')
replace_once(p,
'''  if (!grayscalePass) {\n    char info[96];std::snprintf(info,sizeof(info),"Page %u%s   |   Side keys: page",unsigned(page_)+1,hasNext_ ? "" : " (end)");\n    renderer.drawText(SMALL_FONT_ID,side,bottom+6,info);\n  }\n}\n\nvoid WikiActivity::drawBatteryIndicator() {\n  const auto& m = UITheme::getInstance().getMetrics();\n  const int side = std::max(12,m.contentSidePadding);\n  const int x = renderer.getScreenWidth()-side-m.batteryWidth;\n  GUI.drawBatteryLeft(renderer,Rect{x,m.topPadding,m.batteryWidth,m.batteryHeight},false);\n}''',
'''  char info[96];std::snprintf(info,sizeof(info),"Page %u%s   |   Side keys: page",unsigned(page_)+1,hasNext_ ? "" : " (end)");\n  renderer.drawText(SMALL_FONT_ID,side,bottom+6,info);\n}''')
replace_once(p,'  drawBatteryIndicator();\n  if (!status_.empty()) {','  if (!status_.empty()) {')

# Header
p='src/activities/wiki/WikiActivity.h'
replace_once(p,'  void drawBatteryIndicator();','  void applyOrientation(uint8_t orientation);\n  const char* orientationLabel() const;')
replace_once(p,'  bool smoothText_ = false;','  bool smoothText_ = false;\n  uint8_t appliedOrientation_ = 0;')

# Heading grayscale planes
p='src/activities/wiki/WikiHeading.cpp'
replace_once(p,
'''      const bool ink = data->is2Bit ? ((pixels[pos/4] >> ((3-pos%4)*2)) & 3u) != 0\n                                  : (pixels[pos/8] & (0x80u >> (pos%8))) != 0;\n      if (!ink) continue;\n      const int x0 = x+scaled(cursor+g->left+gx,num,den);\n      const int x1 = x+scaled(cursor+g->left+gx+1,num,den);\n      for (int yy=std::max(y,y0); yy<std::min(bottom,y1); ++yy)\n        for (int xx=std::max(x,x0); xx<std::min(right,x1); ++xx) r.drawPixel(xx,yy,true);''',
'''      uint8_t raw = 0;\n      if (data->is2Bit) raw = (pixels[pos/4] >> ((3-pos%4)*2)) & 3u;\n      else raw = (pixels[pos/8] & (0x80u >> (pos%8))) ? 3u : 0u;\n      const auto mode = r.getRenderMode();\n      const bool ink = mode == GfxRenderer::BW ? raw != 0\n          : mode == GfxRenderer::GRAYSCALE_MSB ? (raw == 1 || raw == 2)\n          : raw == 2;\n      if (!ink) continue;\n      const bool state = mode == GfxRenderer::BW;\n      const int x0 = x+scaled(cursor+g->left+gx,num,den);\n      const int x1 = x+scaled(cursor+g->left+gx+1,num,den);\n      for (int yy=std::max(y,y0); yy<std::min(bottom,y1); ++yy)\n        for (int xx=std::max(x,x0); xx<std::min(right,x1); ++xx) r.drawPixel(xx,yy,state);''')

# version
p=Path('platformio.local.ini'); s=p.read_text();
if s.count('1.6.0-wiki-beta3.6') != 2: raise SystemExit('Unexpected beta 3.6 version count')
p.write_text(s.replace('1.6.0-wiki-beta3.6','1.6.0-wiki-beta3.7'))

# Create minimal build-facing release note + reviewed hash manifest
Path('WIKI_BETA37.md').write_text('''# CrossPoint Wiki beta 3.7 — original X4/X3 only\n\n- Uses CrossPoint native themed header battery/percentage instead of the beta 3.6 Wiki-only battery icon.\n- Text smoothing includes article titles and recognized section headings as well as body/reference/footer text.\n- Wiki article options can cycle CrossPoint orientation: Portrait, Landscape CW, Inverted, Landscape CCW.\n- Orientation is shared with normal CrossPoint reading; Wiki reflows on changes and restores UI rendering to portrait when leaving.\n- WCDB `.cdb` only; ZIM is not supported.\n- Application-only ESP32-C3 image; not a full-flash image and not for X4 Pro/X4C.\n- Hardware test still required; keep a known-good firmware image.\n''')
expected={
 'src/activities/wiki/WikiActivity.cpp':'0d84728e7a705a5811525ca188b071bd671dda47c0758f7e510dd7dfb590c2dc',
 'src/activities/wiki/WikiActivity.h':'c0aa38553223808d116e74fcfeb72e98df5b691206c97fb009ff3e1dfaa3db05',
 'src/activities/wiki/WikiHeading.cpp':'e69447ec304e3545bff6f8966097e507dabcfbd05eb206b65d92aedd84c6ff75',
 'platformio.local.ini':'885e80ff8bcedbce8d73ca6de986ba99cb118eb9968b375ce96320a3dc144cf6',
}
for name,digest in expected.items():
    actual=hashlib.sha256(Path(name).read_bytes()).hexdigest()
    if actual!=digest: raise SystemExit(f'Beta 3.7 fingerprint mismatch: {name} {actual}')
Path('wiki-beta37-reviewed-source.json').write_text(json.dumps(expected,indent=2)+'\n')
print('Applied beta 3.7 deterministic patch and verified',len(expected),'production fingerprints.')
