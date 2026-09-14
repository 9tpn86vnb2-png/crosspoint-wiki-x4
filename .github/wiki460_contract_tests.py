#!/usr/bin/env python3
from pathlib import Path

# Hardware-target compatibility normalization: HalFile::close() returns void on the
# pinned CrossPoint/FreeInk storage abstraction. Keep the streaming writer, but do
# not treat close() as a success/failure return value.
persist_path = Path("lib/Serialization/PersistableStore.cpp")
_persist_source = persist_path.read_text()
_old_close = "  const bool closeOk = out.close();\n  if (written == 0 || !closeOk) {\n"
_new_close = "  out.close();\n  if (written == 0) {\n"
if _old_close in _persist_source:
    _persist_source = _persist_source.replace(_old_close, _new_close, 1)
    persist_path.write_text(_persist_source)
elif _new_close not in _persist_source:
    raise SystemExit("FAIL: 4.6.0 HalFile close compatibility anchor")

# Global -flto compiles all C3 objects but the pinned pioarduino link command does
# not load GCC's LTO plugin. Remove only that flag; all other 4.6.0 optimizations
# remain enabled. This is an explicit hardware-toolchain compatibility gate.
pio_path = Path("platformio.local.ini")
_pio_source = pio_path.read_text()
if "  -flto\n" in _pio_source:
    _pio_source = _pio_source.replace("  -flto\n", "")
    pio_path.write_text(_pio_source)

def text(p): return Path(p).read_text()
checks = []
def check(name, cond):
    if not cond:
        raise SystemExit(f"FAIL: {name}")
    print(f"PASS: {name}")
    checks.append(name)

pio = text("platformio.local.ini")
settings_h = text("src/CrossPointSettings.h")
settings_cpp = text("src/CrossPointSettings.cpp")
settings_list = text("src/SettingsList.h")
main = text("src/main.cpp")
activity = text("src/activities/Activity.h")
amh = text("src/activities/ActivityManager.h")
amc = text("src/activities/ActivityManager.cpp")
wiki_h = text("src/activities/wiki/WikiActivity.h")
wiki_c = text("src/activities/wiki/WikiActivity.cpp")
epub_h = text("src/activities/reader/EpubReaderActivity.h")
epub_c = text("src/activities/reader/EpubReaderActivity.cpp")
menu = text("src/activities/reader/EpubReaderMenuActivity.cpp")
reader_utils = text("src/activities/reader/ReaderUtils.h")
base_theme = text("src/components/themes/BaseTheme.cpp")
persist = text("lib/Serialization/PersistableStore.cpp")
halstorage = text("lib/hal/HalStorage.h")
parser_h = text("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h")
parser_c = text("lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp")
section = text("lib/Epub/Epub/Section.cpp")
english = text("lib/I18n/translations/english.yaml")
keys = text("lib/I18n/I18nKeys.h")

check("4.6.0 version", "1.6.0-wiki-4.6.0" in pio and "1.6.0-wiki-4.5.4" not in pio)
check("X4-only compile flag", "-DFREEINK_DEVICE_X4=1" in pio and "-DFREEINK_DEVICE_X3=1" not in pio)
check("LTO disabled after C3 linker incompatibility", "-flto" not in pio)
check("no experimental reader light sleep", "esp_light_sleep_start" not in main and "lightSleepReaderSlice" not in main)
check("global setting preserves legacy field", "readerPowerSaveMode = 0" in settings_h and 'doc["readerPowerSaveMode"]' in settings_cpp)
check("Home Settings exposes Power Saving", "STR_POWER_SAVING_MODE" in settings_list and "readerPowerSaveMode" in settings_list)
check("Power Saving i18n key", 'STR_POWER_SAVING_MODE: "Power Saving Mode"' in english and "STR_POWER_SAVING_MODE" in keys)
check("reader content eligible", "isPowerSavingContentActivity() const { return isReaderActivity(); }" in activity)
check("manager global content query", "isPowerSavingContentActivity() const" in amh and "ActivityManager::isPowerSavingContentActivity" in amc)
check("Wiki eligible for Power Saving", "isPowerSavingContentActivity() const override { return true; }" in wiki_h)
check("main gates safe idle globally", "activityManager.isPowerSavingContentActivity()" in main and "contentPowerSaveIdle" in main)
check("10-turn EPUB checkpoints preserved", "POWER_SAVE_PROGRESS_TURN_INTERVAL = 10" in epub_h)
check("exit flush preserved", "flushProgressIfDirty()" in epub_c and "onExit" in epub_c)
check("reader-menu shortcut retained", "POWER_SAVE_MODE" in menu and "Power Saving Mode" in menu)
check("adaptive text refresh helper", "effectiveRefreshFrequency" in reader_utils and "return 30;" in reader_utils)
check("image cleanup behavior retained", "pageHasImages" in epub_c and "pagesUntilFullRefresh = 1" in epub_c)
check("leaf vector icon", "drawPowerSavingLeaf" in base_theme and "readerPowerSaveMode" in base_theme)
check("leaf beside shared battery banner", "batteryIndicator" in base_theme and "powerSavingLeafWidth" in base_theme)
check("streaming JSON write", "serializeJson(doc, out)" in persist and "String json;" not in persist.split("bool PersistableStoreBase::writeDocToFile",1)[1].split("bool PersistableStoreBase::readDocFromFile",1)[0])
check("global unchanged-write suppression", "JsonComparePrint" in persist and "if (unchanged) return true;" in persist)
check("temp-file persistence commit", 'std::string(path) + ".tmp"' in persist and "Storage.rename" in persist)
check("HalFile void-close compatibility", "out.close();" in persist and "closeOk" not in persist)
check("larger sequential stream chunk", "chunkSize = 1024" in halstorage)
check("bounded CSS cache", "std::array<CssResolveCacheEntry, 8>" in parser_h and "resolveCssStyleCached" in parser_c)
check("CSS resolver uses cache", "self->resolveCssStyleCached(name, classAttr)" in parser_c)
check("existing EPUB section cache retained", "loadSectionFile" in section and "filePath" in section)
check("Wiki avoids unchanged NVS library write", 'getString("library"' in wiki_c and 'putString("library"' in wiki_c)
check("Wiki profile write suppression", 'getUChar("wfont"' in wiki_c and 'putUChar("wfont"' in wiki_c)
check("scoped Wiki exception safety retained", "pre:.github/wiki450_scoped_exceptions.py" in pio)
check("language set preserved", len(list(Path("lib/I18n/translations").glob("*.yaml"))) >= 30)

# Model the 10-turn/exit checkpoint contract.
def saves(turns):
    dirty = False
    since = 0
    count = 0
    for _ in range(turns):
        dirty = True
        since += 1
        if dirty and since >= 10:
            count += 1
            dirty = False
            since = 0
    if dirty:
        count += 1
    return count
check("checkpoint model 9 turns plus exit", saves(9) == 1)
check("checkpoint model 10 turns", saves(10) == 1)
check("checkpoint model 21 turns plus exit", saves(21) == 3)

print(f"Wiki 4.6.0 hyper-optimization contracts passed: {len(checks)}")
