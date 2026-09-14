#!/usr/bin/env python3
from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"4.6.2 apply: anchor not found for {label}: {path}")
    p.write_text(s.replace(old, new, 1))


# 4.6.2 is an input-responsiveness hotfix on top of 4.6.1. The build profile
# carries the version in more than one place, so update every 4.6.1 occurrence.
p = Path("platformio.local.ini")
s = p.read_text()
if "1.6.0-wiki-4.6.1" not in s:
    raise SystemExit("4.6.2 apply: 4.6.1 version anchor not found")
p.write_text(s.replace("1.6.0-wiki-4.6.1", "1.6.0-wiki-4.6.2"))

# The original X4 navigation keys are ADC ladders and InputManager debounces a
# raw transition only after it survives a second matching sample. At 100 ms,
# a quick page-turn click can fit between samples or disappear before the
# confirming sample. Keep the proven 10 MHz idle clock, but restore the normal
# 10 ms input cadence while Power Saving is active.
replace_once(
    "lib/hal/HalPowerManager.h",
    "  static constexpr unsigned long READER_POWER_SAVE_POLL_MS = 100;       // ms\n",
    "  static constexpr unsigned long READER_POWER_SAVE_POLL_MS = 10;        // ms; preserve ADC-ladder debounce responsiveness\n",
    "Power Saving input poll interval",
)

p = Path("src/main.cpp")
s = p.read_text()
s = s.replace(
    "      // 4.6.0 global safe-idle policy: original X4 navigation keys share ADC ladders,\n"
    "      // so Power Saving deliberately avoids ESP light sleep. EPUB/TXT/XTC/Wiki race\n"
    "      // to the proven 10 MHz state and poll less often without suspending the ADC.\n",
    "      // 4.6.2 safe-idle policy: original X4 navigation keys share ADC ladders, so\n"
    "      // Power Saving deliberately avoids ESP light sleep. EPUB/TXT/XTC/Wiki stay\n"
    "      // at the proven 10 MHz idle state while retaining 10 ms input sampling; the\n"
    "      // debounce path therefore sees the first ordinary page-turn click reliably.\n",
    1,
)
p.write_text(s)

print("Wiki 4.6.2 responsive Power Saving input hotfix applied.")
