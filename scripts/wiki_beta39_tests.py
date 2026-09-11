#!/usr/bin/env python3
"""Source-contract tests for beta 3.9 orientation submenu and landscape article chrome."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cpp = (ROOT/'src/activities/wiki/WikiActivity.cpp').read_text()
hdr = (ROOT/'src/activities/wiki/WikiActivity.h').read_text()
pio = (ROOT/'platformio.local.ini').read_text()

checks = []
def check(cond, message):
    if not cond:
        raise SystemExit('FAILED: '+message)
    checks.append(message)

check('Screen { Home, Results, Bookmarks, Libraries, Article, Options, Orientation }' in hdr,
      'dedicated Orientation screen exists')
check('if (screen_ == Screen::Orientation) return CrossPointSettings::ORIENTATION_COUNT;' in cpp,
      'orientation submenu exposes all native orientations')
check('"Reading orientation"' in cpp and '"Portrait", "Landscape CW", "Inverted", "Landscape CCW"' in cpp,
      'submenu lists all four CrossPoint reader orientations')
check('"Orientation >"' in cpp and 'const uint8_t next = (SETTINGS.orientation + 1)' not in cpp,
      'Article Options opens a submenu instead of cycling orientation')
check('screen_ = Screen::Orientation;\n        selection_ = SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT;' in cpp,
      'submenu opens focused on the saved orientation')
check('else if (screen_ == Screen::Orientation) {\n    applyOrientation(static_cast<uint8_t>(selection_));' in cpp,
      'confirming submenu applies selected orientation')
check('else if (screen_ == Screen::Orientation) { screen_ = Screen::Options; selection_ = 5;' in cpp,
      'Back from submenu returns to Article Options without applying')
check('orientation == CrossPointSettings::LANDSCAPE_CW || orientation == CrossPointSettings::LANDSCAPE_CCW' in cpp,
      'only the two horizontal orientations qualify for landscape chrome removal')
check('const int hintsHeight = articleLandscape() ? 0 : m.buttonHintsHeight;' in cpp,
      'landscape pagination reclaims button-hint height')
check('const bool hideArticleHints = articleLandscape();' in cpp and 'if (!hideArticleHints)' in cpp,
      'button guide tabs are not painted in horizontal article modes')
check(cpp.count('GUI.drawButtonHints(') == 1,
      'there is no second unconditional Wiki button-guide draw path')
check('screen_ == Screen::Article\n      ? SETTINGS.orientation % CrossPointSettings::ORIENTATION_COUNT\n      : CrossPointSettings::PORTRAIT' in cpp,
      'beta 3.8 portrait-menu behavior remains intact')
check('ReaderUtils::renderAntiAliased' in cpp and 'smoothText_' in cpp,
      'whole-article smoothing path remains present')
check('1.6.0-wiki-beta3.9' in pio and '1.6.0-wiki-beta3.8' not in pio,
      'firmware version advanced to beta 3.9')

print(f'{len(checks)} beta 3.9 source-contract checks passed.')
