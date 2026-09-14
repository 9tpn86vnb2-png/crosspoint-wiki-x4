#!/usr/bin/env python3
from pathlib import Path
import subprocess

def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"4.6.0 apply: anchor not found for {label}: {path}")
    p.write_text(s.replace(old, new, 1))

# Version + X4-only + LTO.
p = Path("platformio.local.ini")
s = p.read_text()
s = s.replace('1.6.0-wiki-4.5.4', '1.6.0-wiki-4.6.0')
s = s.replace('  -DFREEINK_DEVICE_X3=1\n', '')
if '  -flto\n' not in s:
    s = s.replace('  -DFREEINK_DEVICE_X4=1\n', '  -DFREEINK_DEVICE_X4=1\n  -flto\n', 1)
p.write_text(s)

replace_once(
    "src/CrossPointSettings.h",
    "  // EPUB-only Power Save Mode: light-sleep slices between input checks and batched progress saves.\n"
    "  uint8_t readerPowerSaveMode = 0;\n",
    "  // Global Power Saving Mode. The legacy member/key name is retained for settings.json compatibility.\n"
    "  // It gates lower idle CPU/polling, deferred reader progress writes, and refresh-cadence tuning.\n"
    "  uint8_t readerPowerSaveMode = 0;\n",
    "global Power Saving setting comment",
)
replace_once(
    "src/CrossPointSettings.cpp",
    "  // Reader-only experimental power policy; deliberately not exposed in global Settings.\n"
    "  doc[\"readerPowerSaveMode\"] = readerPowerSaveMode;\n",
    "  // Global Power Saving Mode; legacy JSON key retained for 4.5.x compatibility.\n"
    "  doc[\"readerPowerSaveMode\"] = readerPowerSaveMode;\n",
    "global Power Saving persistence comment",
)

# Home -> Settings -> System toggle, with English fallback for untranslated languages.
english = Path("lib/I18n/translations/english.yaml")
es = english.read_text()
if 'STR_POWER_SAVING_MODE:' not in es:
    es += '\nSTR_POWER_SAVING_MODE: "Power Saving Mode"\n'
    english.write_text(es)

settings_list = Path("src/SettingsList.h")
ss = settings_list.read_text()
if 'STR_POWER_SAVING_MODE' not in ss:
    entry = (
        "        SettingInfo::Toggle(StrId::STR_POWER_SAVING_MODE, &CrossPointSettings::readerPowerSaveMode,\n"
        "                            nullptr, StrId::STR_CAT_SYSTEM),\n"
    )
    marker = "        // --- System ---\n"
    if marker in ss:
        ss = ss.replace(marker, marker + entry, 1)
    else:
        needle = 'StrId::STR_CAT_SYSTEM)'
        pos = ss.find(needle)
        if pos < 0:
            raise SystemExit("4.6.0 apply: no System settings anchor")
        line_start = ss.rfind('\n', 0, pos) + 1
        ss = ss[:line_start] + entry + ss[line_start:]
    settings_list.write_text(ss)

subprocess.run(["python", "scripts/gen_i18n.py", "lib/I18n/translations", "lib/I18n/"], check=True)

# Content-activity capability: readers default in through isReaderActivity(), Wiki explicitly opts in.
replace_once(
    "src/activities/Activity.h",
    "  virtual bool isReaderActivity() const { return false; }\n",
    "  virtual bool isReaderActivity() const { return false; }\n"
    "  virtual bool isPowerSavingContentActivity() const { return isReaderActivity(); }\n",
    "Activity power-saving capability",
)
replace_once(
    "src/activities/ActivityManager.h",
    "  bool isReaderActivity() const;\n",
    "  bool isReaderActivity() const;\n"
    "  bool isPowerSavingContentActivity() const;\n",
    "ActivityManager power-saving declaration",
)
replace_once(
    "src/activities/ActivityManager.cpp",
    "bool ActivityManager::isReaderActivity() const {\n"
    "  return std::any_of(stackActivities.begin(), stackActivities.end(),\n"
    "                     [](const auto& activity) { return activity->isReaderActivity(); }) ||\n"
    "         (currentActivity && currentActivity->isReaderActivity());\n"
    "}\n",
    "bool ActivityManager::isReaderActivity() const {\n"
    "  return std::any_of(stackActivities.begin(), stackActivities.end(),\n"
    "                     [](const auto& activity) { return activity->isReaderActivity(); }) ||\n"
    "         (currentActivity && currentActivity->isReaderActivity());\n"
    "}\n\n"
    "bool ActivityManager::isPowerSavingContentActivity() const {\n"
    "  return std::any_of(stackActivities.begin(), stackActivities.end(),\n"
    "                     [](const auto& activity) { return activity->isPowerSavingContentActivity(); }) ||\n"
    "         (currentActivity && currentActivity->isPowerSavingContentActivity());\n"
    "}\n",
    "ActivityManager power-saving implementation",
)
p = Path("src/activities/wiki/WikiActivity.h")
s = p.read_text()
if "isPowerSavingContentActivity() const override" not in s:
    for anchor in ("  void loop() override;\n", "  void render(RenderLock&& lock) override;\n"):
        if anchor in s:
            s = s.replace(anchor, anchor + "  bool isPowerSavingContentActivity() const override { return true; }\n", 1)
            break
    else:
        raise SystemExit("4.6.0 apply: WikiActivity override anchor not found")
    p.write_text(s)

# Main loop globalizes 4.5.4's safe low-clock/no-light-sleep mode.
p = Path("src/main.cpp")
s = p.read_text()
old = (
    "    const bool readerPowerSaveIdle = SETTINGS.readerPowerSaveMode && activityManager.isReaderActivity() &&\n"
    "                                     idleMs >= HalPowerManager::READER_POWER_SAVE_IDLE_MS && !RenderLock::peek();\n"
    "    if (readerPowerSaveIdle) {\n"
)
new = (
    "    const bool contentPowerSaveIdle = SETTINGS.readerPowerSaveMode && activityManager.isPowerSavingContentActivity() &&\n"
    "                                      idleMs >= HalPowerManager::READER_POWER_SAVE_IDLE_MS && !RenderLock::peek();\n"
    "    if (contentPowerSaveIdle) {\n"
)
if old not in s:
    raise SystemExit("4.6.0 apply: main power-save anchor not found")
s = s.replace(old, new, 1)
s = s.replace(
    "      // 4.5.4 safety hotfix: the original X4 navigation keys share ADC ladders.\n"
    "      // Explicit ESP light sleep can leave that reader input path unresponsive on\n"
    "      // real hardware, so Power Save now races to the proven 10 MHz idle state and\n"
    "      // polls less often without suspending/restarting the ADC peripheral.\n",
    "      // 4.6.0 global safe-idle policy: original X4 navigation keys share ADC ladders,\n"
    "      // so Power Saving deliberately avoids ESP light sleep. EPUB/TXT/XTC/Wiki race\n"
    "      // to the proven 10 MHz state and poll less often without suspending the ADC.\n",
    1,
)
p.write_text(s)

# Keep the reader-menu shortcut but make its wording global.
p = Path("src/activities/reader/EpubReaderMenuActivity.cpp")
s = p.read_text().replace("Power Save Mode - lower idle CPU and fewer SD writes",
                          "Power Saving Mode - global low-power reading")
s = s.replace("Power Save Mode", "Power Saving Mode")
p.write_text(s)

# Adaptive e-ink cadence: text pages extend cleanup interval to 30 when Power Saving is on.
# EPUB image pages already force a cleanup immediately, giving a content-aware policy.
p = Path("src/activities/reader/ReaderUtils.h")
s = p.read_text()
if "effectiveRefreshFrequency" not in s:
    anchor = "constexpr unsigned long BOOKMARK_MESSAGE_DURATION_MS = 2500;\n"
    helper = (
        "\ninline int effectiveRefreshFrequency() {\n"
        "  const int configured = SETTINGS.getRefreshFrequency();\n"
        "  if (!SETTINGS.readerPowerSaveMode || configured <= 1 || configured >= 30) return configured;\n"
        "  return 30;\n"
        "}\n"
    )
    if anchor not in s:
        raise SystemExit("4.6.0 apply: ReaderUtils helper anchor not found")
    s = s.replace(anchor, anchor + helper, 1)
s = s.replace("pagesUntilFullRefresh = SETTINGS.getRefreshFrequency();",
              "pagesUntilFullRefresh = effectiveRefreshFrequency();")
p.write_text(s)

p = Path("src/activities/reader/ReaderActivity.cpp")
s = p.read_text().replace("const int refreshFrequency = SETTINGS.getRefreshFrequency();",
                          "const int refreshFrequency = ReaderUtils::effectiveRefreshFrequency();")
p.write_text(s)

# Tiny leaf beside battery/percentage in shared headers and reader status bars.
p = Path("src/components/themes/BaseTheme.cpp")
s = p.read_text()
if "drawPowerSavingLeaf" not in s:
    helper_anchor = "void drawBookmarkStatusIcon(const GfxRenderer& renderer, const int x, const int y) {"
    idx = s.find(helper_anchor)
    if idx < 0:
        raise SystemExit("4.6.0 apply: BaseTheme helper anchor not found")
    close = s.find("\n}  // namespace", idx)
    leaf = r'''
constexpr int powerSavingLeafWidth = 9;

void drawPowerSavingLeaf(const GfxRenderer& renderer, const int x, const int y) {
  renderer.drawLine(x + 1, y + 6, x + 1, y + 4);
  renderer.drawLine(x + 2, y + 3, x + 4, y + 1);
  renderer.drawLine(x + 5, y, x + 7, y + 1);
  renderer.drawLine(x + 8, y + 2, x + 8, y + 4);
  renderer.drawLine(x + 7, y + 5, x + 5, y + 7);
  renderer.drawLine(x + 4, y + 8, x + 2, y + 7);
  renderer.drawLine(x + 2, y + 7, x + 7, y + 2);
  renderer.drawLine(x + 4, y + 8, x + 4, y + 10);
}
'''
    s = s[:close] + "\n" + leaf + s[close:]

old = (
    "  const Rect iconRect{rect.x, y, rect.width, rect.height};\n"
    "  drawBatteryOutline(renderer, rect.x, y, rect.width, rect.height);\n"
    "  fillBatteryIcon(renderer, iconRect, percentage);\n"
)
new = (
    "  const Rect iconRect{rect.x, y, rect.width, rect.height};\n"
    "  drawBatteryOutline(renderer, rect.x, y, rect.width, rect.height);\n"
    "  fillBatteryIcon(renderer, iconRect, percentage);\n"
    "  if (SETTINGS.readerPowerSaveMode) {\n"
    "    int leafX = rect.x + rect.width + 4;\n"
    "    if (showPercentage) {\n"
    "      const auto percentageText2 = std::to_string(percentage) + \"%\";\n"
    "      leafX = rect.x + batteryPercentSpacing + rect.width + renderer.getTextWidth(SMALL_FONT_ID, percentageText2.c_str()) + 4;\n"
    "    }\n"
    "    drawPowerSavingLeaf(renderer, leafX, rect.y + 2);\n"
    "  }\n"
)
if old not in s:
    raise SystemExit("4.6.0 apply: drawBatteryLeft anchor not found")
s = s.replace(old, new, 1)

old = "  fui::batteryIndicator(ui.frame, fui::Rect{batteryX, band.y, batteryReserve, batteryH}, battery);\n"
new = old + (
    "  if (SETTINGS.readerPowerSaveMode) {\n"
    "    const int leafX = batteryLeft ? batteryX + batteryReserve + 3 : batteryX - powerSavingLeafWidth - 3;\n"
    "    drawPowerSavingLeaf(renderer, leafX, band.y + 2);\n"
    "  }\n"
)
if old not in s:
    raise SystemExit("4.6.0 apply: header battery anchor not found")
s = s.replace(old, new, 1)
p.write_text(s)

# Global persistence: stream JSON directly, compare against existing bytes, skip unchanged writes,
# and commit through a temp file. This removes the full-document Arduino String allocation.
p = Path("lib/Serialization/PersistableStore.cpp")
s = p.read_text()
start = s.index("bool PersistableStoreBase::writeDocToFile")
end = s.index("\nbool PersistableStoreBase::readDocFromFile", start)
replacement = r'''namespace {
class JsonComparePrint final : public Print {
 public:
  explicit JsonComparePrint(HalFile& existing) : existing_(existing) {}
  size_t write(const uint8_t b) override { return write(&b, 1); }
  size_t write(const uint8_t* buffer, const size_t size) override {
    if (!equal_) return size;
    uint8_t scratch[128];
    size_t offset = 0;
    while (offset < size) {
      const size_t want = std::min(sizeof(scratch), size - offset);
      const int got = existing_.read(scratch, want);
      if (got != static_cast<int>(want) || std::memcmp(scratch, buffer + offset, want) != 0) {
        equal_ = false;
        return size;
      }
      offset += want;
    }
    return size;
  }
  bool equalAtEnd() { return equal_ && existing_.read() < 0; }
 private:
  HalFile& existing_;
  bool equal_ = true;
};
}  // namespace

bool PersistableStoreBase::writeDocToFile(const char* path, const JsonDocument& doc) {
  Storage.mkdir("/.crosspoint");

  if (Storage.exists(path)) {
    HalFile existing;
    if (Storage.openFileForRead("PERSIST", path, existing)) {
      JsonComparePrint compare(existing);
      serializeJson(doc, compare);
      const bool unchanged = compare.equalAtEnd();
      existing.close();
      if (unchanged) return true;
    }
  }

  const std::string tmpPath = std::string(path) + ".tmp";
  HalFile out;
  if (!Storage.openFileForWrite("PERSIST", tmpPath, out)) {
    LOG_ERR("PERSIST", "Failed to open temp file for %s", path);
    return false;
  }
  const size_t written = serializeJson(doc, out);
  out.flush();
  const bool closeOk = out.close();
  if (written == 0 || !closeOk) {
    Storage.remove(tmpPath.c_str());
    LOG_ERR("PERSIST", "Failed to stream JSON for %s", path);
    return false;
  }
  if (Storage.exists(path) && !Storage.remove(path)) {
    Storage.remove(tmpPath.c_str());
    LOG_ERR("PERSIST", "Failed to replace %s", path);
    return false;
  }
  if (!Storage.rename(tmpPath.c_str(), path)) {
    LOG_ERR("PERSIST", "Failed to commit %s", path);
    return false;
  }
  return true;
}
'''
s = s[:start] + replacement + s[end:]
if "#include <algorithm>" not in s:
    s = s.replace("#include <cstring>\n", "#include <algorithm>\n#include <cstring>\n", 1)
p.write_text(s)

# Larger bounded sequential streaming chunk.
p = Path("lib/hal/HalStorage.h")
s = p.read_text().replace("bool readFileToStream(const char* path, Print& out, size_t chunkSize = 256);",
                          "bool readFileToStream(const char* path, Print& out, size_t chunkSize = 1024);")
p.write_text(s)

# Tiny bounded CSS resolution cache.
p = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h")
s = p.read_text()
if "CssResolveCacheEntry" not in s:
    anchor = "  const CssParser* cssParser;\n"
    addition = r'''  struct CssResolveCacheEntry {
    std::string tag;
    std::string className;
    CssStyle style;
    bool valid = false;
  };
  std::array<CssResolveCacheEntry, 8> cssResolveCache{};
  uint8_t cssResolveCacheNext = 0;
  CssStyle resolveCssStyleCached(const char* tag, const std::string& className);
'''
    if anchor not in s:
        raise SystemExit("4.6.0 apply: CSS cache header anchor not found")
    s = s.replace(anchor, anchor + addition, 1)
p.write_text(s)

p = Path("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp")
s = p.read_text()
if "CssStyle ChapterHtmlSlimParser::resolveCssStyleCached" not in s:
    marker = "// Compute CSS style for this element early"
    pos = s.find(marker)
    if pos < 0:
        raise SystemExit("4.6.0 apply: CSS cache cpp anchor not found")
    callback_pos = s.rfind("\nvoid ", 0, pos)
    if callback_pos < 0:
        raise SystemExit("4.6.0 apply: CSS callback boundary not found")
    impl = r'''
CssStyle ChapterHtmlSlimParser::resolveCssStyleCached(const char* tag, const std::string& className) {
  if (!cssParser) return {};
  for (const auto& entry : cssResolveCache) {
    if (entry.valid && entry.tag == tag && entry.className == className) return entry.style;
  }
  CssStyle style = cssParser->resolveStyle(tag, className);
  auto& entry = cssResolveCache[cssResolveCacheNext++ % cssResolveCache.size()];
  entry.tag.assign(tag);
  entry.className = className;
  entry.style = style;
  entry.valid = true;
  return style;
}

'''
    s = s[:callback_pos] + impl + s[callback_pos:]
s = s.replace("cssStyle = self->cssParser->resolveStyle(name, classAttr);",
              "cssStyle = self->resolveCssStyleCached(name, classAttr);")
p.write_text(s)

# Wiki NVS no-op writes for library/text profile.
p = Path("src/activities/wiki/WikiActivity.cpp")
s = p.read_text()
old = (
    '    if (preferences.begin("wikibeta", false)) {\n'
    '      preferences.putString("library", libraryPath_.c_str());\n'
    '      preferences.end();\n'
    '    }\n'
)
new = (
    '    if (preferences.begin("wikibeta", false)) {\n'
    '      if (preferences.getString("library", "") != libraryPath_.c_str()) {\n'
    '        preferences.putString("library", libraryPath_.c_str());\n'
    '      }\n'
    '      preferences.end();\n'
    '    }\n'
)
if old in s:
    s = s.replace(old, new, 1)

old = (
    '  preferences.putBool("wprofile", true);\n'
    '  preferences.putUChar("wfont", SETTINGS.fontFamily);\n'
    '  preferences.putUChar("wsize", SETTINGS.fontPointSize);\n'
    '  preferences.putUChar("wline", SETTINGS.lineSpacing);\n'
    '  preferences.putBool("wpara", SETTINGS.extraParagraphSpacing != 0);\n'
    '  preferences.putUChar("walign", SETTINGS.paragraphAlignment);\n'
    '  preferences.putUChar("wmargin", SETTINGS.screenMargin);\n'
    '  preferences.putString("wfontname", SETTINGS.sdFontFamilyName);\n'
)
new = (
    '  if (!preferences.getBool("wprofile", false)) preferences.putBool("wprofile", true);\n'
    '  if (preferences.getUChar("wfont", 0xFF) != SETTINGS.fontFamily) preferences.putUChar("wfont", SETTINGS.fontFamily);\n'
    '  if (preferences.getUChar("wsize", 0xFF) != SETTINGS.fontPointSize) preferences.putUChar("wsize", SETTINGS.fontPointSize);\n'
    '  if (preferences.getUChar("wline", 0xFF) != SETTINGS.lineSpacing) preferences.putUChar("wline", SETTINGS.lineSpacing);\n'
    '  const bool para = SETTINGS.extraParagraphSpacing != 0;\n'
    '  if (preferences.getBool("wpara", !para) != para) preferences.putBool("wpara", para);\n'
    '  if (preferences.getUChar("walign", 0xFF) != SETTINGS.paragraphAlignment) preferences.putUChar("walign", SETTINGS.paragraphAlignment);\n'
    '  if (preferences.getUChar("wmargin", 0xFF) != SETTINGS.screenMargin) preferences.putUChar("wmargin", SETTINGS.screenMargin);\n'
    '  if (preferences.getString("wfontname", "") != SETTINGS.sdFontFamilyName) preferences.putString("wfontname", SETTINGS.sdFontFamilyName);\n'
)
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s)

# Keep scoped Wiki exceptions for graceful OOM. The bounded XML limits stay intact; a later
# no-exception variant must prove equivalent failure handling before removing them.

print("Wiki 4.6.0 hyper-optimization patch applied.")
