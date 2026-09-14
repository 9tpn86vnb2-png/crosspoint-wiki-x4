#!/usr/bin/env python3
from pathlib import Path


def text(path):
    return Path(path).read_text()

checks = []
def check(name, condition):
    if not condition:
        raise SystemExit(f'FAIL: {name}')
    print(f'PASS: {name}')
    checks.append(name)

pio = text('platformio.local.ini')
main = text('src/main.cpp')
pwrh = text('lib/hal/HalPowerManager.h')
pwrc = text('lib/hal/HalPowerManager.cpp')
epub = text('src/activities/reader/EpubReaderActivity.cpp')
menu = text('src/activities/reader/EpubReaderMenuActivity.cpp')

check('4.5.4 version', '1.6.0-wiki-4.5.4' in pio and '1.6.0-wiki-4.5.3' not in pio)
check('explicit ESP reader light sleep removed', 'esp_light_sleep_start' not in pwrc)
check('reader light-sleep helper removed', 'lightSleepReaderSlice' not in pwrc and 'lightSleepReaderSlice' not in pwrh)
check('safe reader idle threshold', 'READER_POWER_SAVE_IDLE_MS = 1500' in pwrh)
check('safe reader polling interval', 'READER_POWER_SAVE_POLL_MS = 100' in pwrh)
check('reader Power Save still gated by setting', 'SETTINGS.readerPowerSaveMode && activityManager.isReaderActivity()' in main)
check('reader Power Save uses low CPU mode', 'powerManager.setPowerSaving(true);' in main)
check('reader Power Save uses safe delay', 'delay(HalPowerManager::READER_POWER_SAVE_POLL_MS);' in main)
check('normal idle behavior retained', 'idleMs >= HalPowerManager::IDLE_POWER_SAVING_MS' in main and 'delay(50);' in main)
check('Power Save default remains off', 'readerPowerSaveMode = 0' in text('src/CrossPointSettings.h'))
check('10-turn checkpoint retained', 'POWER_SAVE_PROGRESS_TURN_INTERVAL = 10' in text('src/activities/reader/EpubReaderActivity.h'))
check('exit flush retained', 'flushProgressIfDirty()' in epub and 'onExit' in epub)
check('manual Finished Books path retained', 'Mark as Finished' in menu and 'RECENT_BOOKS.markFinished' in epub)
check('automatic Finished Books path retained', epub.count('RECENT_BOOKS.markFinished') >= 2)
check('menu describes safe behavior', 'Power Save Mode - lower idle CPU and fewer SD writes' in menu)
check('old sleep-between-inputs label removed', 'sleeps reader between inputs' not in menu)

print(f'Wiki 4.5.4 contracts passed: {len(checks)}')
