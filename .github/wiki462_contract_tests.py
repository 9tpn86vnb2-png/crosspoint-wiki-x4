#!/usr/bin/env python3
from pathlib import Path

checks = []

def expect(label, condition):
    if not condition:
        raise SystemExit(f"FAIL: {label}")
    print(f"PASS: {label}")
    checks.append(label)

pio = Path("platformio.local.ini").read_text()
hal = Path("lib/hal/HalPowerManager.h").read_text()
main = Path("src/main.cpp").read_text()
reader = Path("src/activities/reader/ReaderActivity.cpp").read_text()
utils = Path("src/activities/reader/ReaderUtils.h").read_text()

expect("4.6.2 version", "1.6.0-wiki-4.6.2" in pio and "1.6.0-wiki-4.6.1" not in pio)
expect("Power Saving input poll restored to 10 ms",
       "READER_POWER_SAVE_POLL_MS = 10;" in hal)
expect("old 100 ms reader poll removed",
       "READER_POWER_SAVE_POLL_MS = 100;" not in hal)
expect("low-clock Power Saving retained",
       "powerManager.setPowerSaving(true);" in main)
expect("responsive poll constant is used",
       "delay(HalPowerManager::READER_POWER_SAVE_POLL_MS);" in main)
expect("global content Power Saving retained",
       "activityManager.isPowerSavingContentActivity()" in main)
expect("explicit ESP light sleep remains disabled",
       "esp_light_sleep_start" not in main)
expect("10-turn deferred EPUB checkpoint retained",
       "POWER_SAVE_PAGE_TURN_CHECKPOINT = 10" in reader)
expect("adaptive Power Saving refresh retained",
       "effectiveRefreshFrequency" in utils)
expect("4.6.2 comment documents first-click debounce reliability",
       "retaining 10 ms input sampling" in main and "first ordinary page-turn click reliably" in main)

# Model the SDK's debounce rule: a raw transition commits only after a second
# matching sample more than 5 ms later. This is intentionally small and
# deterministic; it demonstrates why the former 100 ms cadence could eat a
# normal quick click and why the restored 10 ms cadence avoids that class of
# miss for ordinary >=30 ms mechanical presses.
def recognized(poll_ms, press_start_ms, press_duration_ms, debounce_ms=5):
    current = False
    last = False
    last_debounce = 0
    saw_press = False
    end_ms = press_start_ms + press_duration_ms + poll_ms * 3
    t = 0
    while t <= end_ms:
        raw = press_start_ms <= t < press_start_ms + press_duration_ms
        if raw != last:
            last_debounce = t
            last = raw
        if (t - last_debounce) > debounce_ms and raw != current:
            current = raw
            if current:
                saw_press = True
        t += poll_ms
    return saw_press

expect("model: old 100 ms cadence can drop an 80 ms click",
       not recognized(100, 1, 80))
expect("model: 10 ms cadence captures 30 ms clicks at every phase",
       all(recognized(10, phase, 30) for phase in range(1, 11)))

print(f"Wiki 4.6.2 input contracts passed: {len(checks)}")
