#!/usr/bin/env python3
"""Static validation for the Wiki 4.3 Unicode-symbol integration."""
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "lib/EpdFont/builtinFonts"
SOURCE = FONT_DIR / "source/NotoSansSymbols"

REQUIRED = {
    0x00A9, 0x00AE, 0x00D7, 0x00F7,
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D,
    0x2022, 0x2026, 0x20AC, 0x2122,
    0x2190, 0x2192, 0x2212, 0x2460,
    0x260E, 0x2660, 0x2665, 0x26A0, 0x271D,
    0x1F610, 0x1F700,
}

for label in ("Regular", "Bold"):
    path = SOURCE / f"NotoSansSymbols-{label}.ttf"
    assert path.exists(), path
    tt = TTFont(path)
    cmap = set((tt.getBestCmap() or {}).keys())
    versions = {r.toUnicode() for r in tt["name"].names if r.nameID == 5}
    tt.close()
    assert "Version 2.003" in versions, versions
    assert len(cmap) == 1107, len(cmap)
    missing = sorted(REQUIRED - cmap)
    assert not missing, [f"U+{cp:04X}" for cp in missing]

all_h = (FONT_DIR / "all.h").read_text(encoding="utf-8")
ids = (ROOT / "src/fontIds.h").read_text(encoding="utf-8")
main = (ROOT / "src/main.cpp").read_text(encoding="utf-8")
gfx = (ROOT / "lib/GfxRenderer/GfxRenderer.cpp").read_text(encoding="utf-8")
sd = (ROOT / "src/SdCardFontSystem.cpp").read_text(encoding="utf-8")
entities = (ROOT / "lib/Epub/Epub/htmlEntities.cpp").read_text(encoding="utf-8")

for size in (12, 14, 16, 18):
    for style in ("regular", "bold"):
        name = f"notosymbols_{size}_{style}"
        header = FONT_DIR / f"{name}.h"
        assert header.exists(), header
        data = header.read_text(encoding="utf-8", errors="ignore")
        assert name in data
        assert f"builtinFonts/{name}.h" in all_h
    assert f"NOTOSYMBOLS_{size}_FONT_ID" in ids
    assert f"notosymbols{size}FontFamily" in main
    assert f"renderer.insertFont(NOTOSYMBOLS_{size}_FONT_ID" in main
    assert f"renderer.setFallbackFont(NOTOSERIF_{size}_FONT_ID, NOTOSYMBOLS_{size}_FONT_ID);" in main
    assert f"renderer.setFallbackFont(NOTOSANS_{size}_FONT_ID, NOTOSYMBOLS_{size}_FONT_ID);" in main

assert "Built-in fallback fonts are used for general Unicode coverage" in gfx
assert "isSdCardFont(fallbackFontId)" in gfx
assert "primaryMissing ? fallbackFontId : fontId" in gfx
assert "Reader-size Unicode/symbol fallback" in sd
assert "symbolFallbackForPointSize" in sd

for entity in (
    "&copy;", "&reg;", "&times;", "&divide;", "&bull;", "&hellip;",
    "&ndash;", "&mdash;", "&lsquo;", "&rsquo;", "&ldquo;", "&rdquo;",
    "&euro;", "&larr;", "&rarr;", "&hearts;", "&spades;",
):
    assert entity in entities, entity

print("Wiki 4.3 Unicode-symbol integration tests passed.")
