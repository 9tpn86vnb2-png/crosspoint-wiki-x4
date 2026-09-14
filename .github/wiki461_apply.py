#!/usr/bin/env python3
from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text()
    if old not in s:
        raise SystemExit(f"4.6.1 apply: anchor not found for {label}: {path}")
    p.write_text(s.replace(old, new, 1))


# Version only; 4.6.1 is a UI-size hotfix on top of 4.6.0.
p = Path("platformio.local.ini")
s = p.read_text()
if "1.6.0-wiki-4.6.0" not in s:
    raise SystemExit("4.6.1 apply: 4.6.0 version anchor not found")
p.write_text(s.replace("1.6.0-wiki-4.6.0", "1.6.0-wiki-4.6.1"))

p = Path("src/components/themes/BaseTheme.cpp")
s = p.read_text()

old_leaf = r'''constexpr int powerSavingLeafWidth = 9;

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

new_leaf = r'''constexpr int powerSavingLeafWidth = 15;
constexpr int powerSavingLeafHeight = 12;
constexpr int powerSavingLeafGap = 4;

void drawPowerSavingLeaf(const GfxRenderer& renderer, const int x, const int y) {
  // 4.6.1: full battery-sized 15x12 leaf for visibility on the X4 panel.
  // The outline fills the same visual footprint as the 15x12 battery glyph.
  renderer.drawLine(x + 1, y + 9, x + 2, y + 6);
  renderer.drawLine(x + 2, y + 6, x + 5, y + 3);
  renderer.drawLine(x + 5, y + 3, x + 9, y + 1);
  renderer.drawLine(x + 9, y + 1, x + 13, y + 1);
  renderer.drawLine(x + 13, y + 1, x + 14, y + 4);
  renderer.drawLine(x + 14, y + 4, x + 13, y + 7);
  renderer.drawLine(x + 13, y + 7, x + 10, y + 10);
  renderer.drawLine(x + 10, y + 10, x + 6, y + 11);
  renderer.drawLine(x + 6, y + 11, x + 2, y + 10);

  // Main vein + two short branches keep the larger glyph recognizable.
  renderer.drawLine(x + 2, y + 10, x + 12, y + 2);
  renderer.drawLine(x + 6, y + 7, x + 6, y + 4);
  renderer.drawLine(x + 8, y + 6, x + 11, y + 6);
  renderer.drawLine(x + 3, y + 10, x + 3, y + 11);
}
'''

if old_leaf not in s:
    raise SystemExit("4.6.1 apply: old 9px leaf block not found")
s = s.replace(old_leaf, new_leaf, 1)

# Use the same gap constant and align the reader-status leaf to the battery glyph itself.
s = s.replace("rect.x + rect.width + 4", "rect.x + rect.width + powerSavingLeafGap", 1)
s = s.replace("renderer.getTextWidth(SMALL_FONT_ID, percentageText2.c_str()) + 4",
              "renderer.getTextWidth(SMALL_FONT_ID, percentageText2.c_str()) + powerSavingLeafGap", 1)
s = s.replace("drawPowerSavingLeaf(renderer, leafX, rect.y + 2);",
              "drawPowerSavingLeaf(renderer, leafX, y);", 1)

# Reserve the enlarged leaf in the status-bar left cluster so it cannot collide with clock/bookmark/title content.
status_old = "    leftClusterWidth += batteryWidth;\n"
status_new = (
    "    if (SETTINGS.readerPowerSaveMode) {\n"
    "      batteryWidth += powerSavingLeafGap + powerSavingLeafWidth;\n"
    "    }\n"
    "    leftClusterWidth += batteryWidth;\n"
)
if status_old not in s:
    raise SystemExit("4.6.1 apply: status-bar battery width anchor not found")
s = s.replace(status_old, status_new, 1)

# Reserve the enlarged leaf in shared headers too. Battery remains against its edge;
# the leaf occupies the adjacent reserved space on the content side.
header_old = (
    "  if (showBatteryPercentage) {\n"
    "    batteryReserve = static_cast<int16_t>(\n"
    "        batteryReserve + batteryPercentSpacing +\n"
    "        ui.target.measureText(fui::GfxRendererTarget::FONT_SMALL, percentText, tokens.smallText).width);\n"
    "  }\n\n"
    "  fui::HeaderProps props;\n"
)
header_new = (
    "  if (showBatteryPercentage) {\n"
    "    batteryReserve = static_cast<int16_t>(\n"
    "        batteryReserve + batteryPercentSpacing +\n"
    "        ui.target.measureText(fui::GfxRendererTarget::FONT_SMALL, percentText, tokens.smallText).width);\n"
    "  }\n"
    "  const int16_t powerSavingLeafReserve = SETTINGS.readerPowerSaveMode\n"
    "                                             ? static_cast<int16_t>(powerSavingLeafGap + powerSavingLeafWidth)\n"
    "                                             : 0;\n\n"
    "  fui::HeaderProps props;\n"
)
if header_old not in s:
    raise SystemExit("4.6.1 apply: header battery reserve anchor not found")
s = s.replace(header_old, header_new, 1)
s = s.replace("const int16_t reserve = static_cast<int16_t>(batteryReserve + tokens.spaceMd);",
              "const int16_t reserve = static_cast<int16_t>(batteryReserve + powerSavingLeafReserve + tokens.spaceMd);",
              1)

# Align the shared-header leaf with the centered 12px battery glyph.
s = s.replace("batteryX + batteryReserve + 3", "batteryX + batteryReserve + powerSavingLeafGap", 1)
s = s.replace("batteryX - powerSavingLeafWidth - 3", "batteryX - powerSavingLeafWidth - powerSavingLeafGap", 1)
s = s.replace("drawPowerSavingLeaf(renderer, leafX, band.y + 2);",
              "drawPowerSavingLeaf(renderer, leafX, band.y + (batteryH - powerSavingLeafHeight) / 2);", 1)

p.write_text(s)
print("Wiki 4.6.1 battery-sized Power Saving leaf patch applied.")
