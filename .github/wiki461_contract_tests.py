#!/usr/bin/env python3
from pathlib import Path

checks = []

def expect(label, condition):
    if not condition:
        raise SystemExit(f"FAIL: {label}")
    print(f"PASS: {label}")
    checks.append(label)

pio = Path("platformio.local.ini").read_text()
base = Path("src/components/themes/BaseTheme.cpp").read_text()
main = Path("src/main.cpp").read_text()

expect("4.6.1 version", "1.6.0-wiki-4.6.1" in pio and "1.6.0-wiki-4.6.0" not in pio)
expect("leaf matches battery width", "constexpr int powerSavingLeafWidth = 15;" in base)
expect("leaf matches battery height", "constexpr int powerSavingLeafHeight = 12;" in base)
expect("leaf uses visible full-size outline", "full battery-sized 15x12 leaf" in base)
expect("leaf has main vein", "renderer.drawLine(x + 2, y + 10, x + 12, y + 2);" in base)
expect("reader-status leaf aligns with battery", "drawPowerSavingLeaf(renderer, leafX, y);" in base)
expect("shared-header leaf centers to battery height",
       "band.y + (batteryH - powerSavingLeafHeight) / 2" in base)
expect("status bar reserves enlarged leaf", "batteryWidth += powerSavingLeafGap + powerSavingLeafWidth;" in base)
expect("header reserves enlarged leaf", "powerSavingLeafReserve + tokens.spaceMd" in base)
expect("leaf still gated by Power Saving Mode", base.count("if (SETTINGS.readerPowerSaveMode)") >= 2)
expect("safe-idle policy unchanged", "esp_light_sleep_start" not in main)

print(f"Wiki 4.6.1 leaf contracts passed: {len(checks)}")
