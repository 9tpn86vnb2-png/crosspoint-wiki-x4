#!/usr/bin/env python3
from pathlib import Path


def replace(path, old, new):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f'4.5.4 anchor missing in {path}')
    p.write_text(s.replace(old, new, 1))

replace('platformio.local.ini', '1.6.0-wiki-4.5.3', '1.6.0-wiki-4.5.4')
replace('platformio.local.ini', '1.6.0-wiki-4.5.3', '1.6.0-wiki-4.5.4')

h = Path('lib/hal/HalPowerManager.h')
s = h.read_text()
s = s.replace('  static constexpr unsigned long READER_LIGHT_SLEEP_IDLE_MS = 1500;           // ms\n'
              '  static constexpr uint64_t READER_LIGHT_SLEEP_SLICE_US = 40000;               // 40 ms\n',
              '  static constexpr unsigned long READER_POWER_SAVE_IDLE_MS = 1500;      // ms\n'
              '  static constexpr unsigned long READER_POWER_SAVE_POLL_MS = 100;       // ms\n')
s = s.replace('\n  // Reader-only explicit light-sleep slice. RAM and panel contents remain live;\n'
              '  // the original X4\'s ADC ladder is polled on the timer wake, while the power\n'
              '  // button can wake immediately through GPIO.\n'
              '  bool lightSleepReaderSlice(uint64_t sleepUs = READER_LIGHT_SLEEP_SLICE_US) const;\n', '\n')
h.write_text(s)

cpp = Path('lib/hal/HalPowerManager.cpp')
s = cpp.read_text()
s = s.replace('#include <esp_sleep.h>\n#include <esp_sleep.h>\n', '')
start = s.find('bool HalPowerManager::lightSleepReaderSlice(')
end = s.find('\nuint16_t HalPowerManager::getBatteryPercentage()', start)
if start < 0 or end < 0:
    raise SystemExit('4.5.4 light-sleep implementation anchor missing')
s = s[:start] + s[end+1:]
cpp.write_text(s)

main = Path('src/main.cpp')
s = main.read_text()
old = '''    const bool readerLightSleep = SETTINGS.readerPowerSaveMode && activityManager.isReaderActivity() &&
                                  idleMs >= HalPowerManager::READER_LIGHT_SLEEP_IDLE_MS && !RenderLock::peek();
    if (readerLightSleep) {
      // The X4 navigation keys are ADC ladders, so a short timer-sliced light
      // sleep preserves every button while actually stopping the CPU between polls.
      // Power has a direct GPIO wake path inside lightSleepReaderSlice().
      powerManager.setPowerSaving(true);
      if (!powerManager.lightSleepReaderSlice()) delay(50);
    } else if (idleMs >= HalPowerManager::IDLE_POWER_SAVING_MS) {
'''
new = '''    const bool readerPowerSaveIdle = SETTINGS.readerPowerSaveMode && activityManager.isReaderActivity() &&
                                     idleMs >= HalPowerManager::READER_POWER_SAVE_IDLE_MS && !RenderLock::peek();
    if (readerPowerSaveIdle) {
      // 4.5.4 safety hotfix: the original X4 navigation keys share ADC ladders.
      // Explicit ESP light sleep can leave that reader input path unresponsive on
      // real hardware, so Power Save now races to the proven 10 MHz idle state and
      // polls less often without suspending/restarting the ADC peripheral.
      powerManager.setPowerSaving(true);
      delay(HalPowerManager::READER_POWER_SAVE_POLL_MS);
    } else if (idleMs >= HalPowerManager::IDLE_POWER_SAVING_MS) {
'''
if old not in s:
    raise SystemExit('4.5.4 main light-sleep anchor missing')
s = s.replace(old, new, 1)
main.write_text(s)

menu = Path('src/activities/reader/EpubReaderMenuActivity.cpp')
s = menu.read_text()
s = s.replace('Power Save Mode - sleeps reader between inputs',
              'Power Save Mode - lower idle CPU and fewer SD writes')
menu.write_text(s)

print('Wiki 4.5.4 safe Power Save hotfix applied.')
