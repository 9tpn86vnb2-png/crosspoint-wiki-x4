#!/usr/bin/env python3
'''Integrate Noto Sans Symbols v2.003 as a Unicode symbol fallback for CrossPoint X4.

Run after the Wiki 4.3 integration steps. It verifies the supplied symbol
TTFs, generates compact reader-size fallback fonts, registers them, extends
the shared renderer's fallback resolver for general Unicode symbols while
preserving the SD-card CJK UI path, and maps SD reader fonts to the nearest
symbol fallback size.
'''

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "lib/EpdFont/builtinFonts"
FONT_SOURCE_DIR = Path(os.environ.get(
    "NOTO_SYMBOLS_DIR",
    str(FONT_DIR / "source/NotoSansSymbols"),
))

REGULAR = FONT_SOURCE_DIR / "NotoSansSymbols-Regular.ttf"
BOLD = FONT_SOURCE_DIR / "NotoSansSymbols-Bold.ttf"

EXPECTED_SHA256 = {
    "NotoSansSymbols-Regular.ttf": "aedeec1cd0514930aeeafc4a88a6deff83cda1e6b58086f0b9bb9c7dd0157578",
    "NotoSansSymbols-Bold.ttf": "5682f6c88d6199623edf026f67a8722697e8c5f409e5249477594e409d657eb0",
}
EXPECTED_VERSION = "Version 2.003"
SIZES = (12, 14, 16, 18)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_font(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"Missing uploaded-equivalent source font: {path}")
    got = sha256(path)
    expected = EXPECTED_SHA256[path.name]
    if got != expected:
        raise RuntimeError(
            f"{path.name} SHA-256 mismatch: expected {expected}, got {got}. "
            "Refusing to build from a different Unicode source."
        )
    tt = TTFont(path)
    versions = {rec.toUnicode() for rec in tt["name"].names if rec.nameID == 5}
    tt.close()
    if EXPECTED_VERSION not in versions:
        raise RuntimeError(
            f"{path.name} is not {EXPECTED_VERSION}; got {sorted(versions)}"
        )


def contiguous_cmap_intervals(path: Path) -> list[tuple[int, int]]:
    tt = TTFont(path)
    cmap = sorted((tt.getBestCmap() or {}).keys())
    tt.close()
    if not cmap:
        raise RuntimeError(f"No Unicode cmap in {path}")
    ranges: list[tuple[int, int]] = []
    start = prev = cmap[0]
    for cp in cmap[1:]:
        if cp == prev + 1:
            prev = cp
            continue
        ranges.append((start, prev))
        start = prev = cp
    ranges.append((start, prev))
    return ranges


def generate_fonts() -> None:
    converter = ROOT / "lib/EpdFont/scripts/fontconvert.py"
    symbol_ranges = contiguous_cmap_intervals(REGULAR)
    range_args: list[str] = []
    for lo, hi in symbol_ranges:
        range_args += ["--additional-intervals", f"0x{lo:X},0x{hi:X}"]

    for size in SIZES:
        for style, src in (("regular", REGULAR), ("bold", BOLD)):
            name = f"notosymbols_{size}_{style}"
            out = FONT_DIR / f"{name}.h"
            cmd = [
                sys.executable,
                str(converter),
                name,
                str(size),
                str(src),
                "--compress",
                *range_args,
            ]
            print("Generating", out.relative_to(ROOT))
            with out.open("w", encoding="utf-8", newline="\n") as f:
                subprocess.run(cmd, cwd=converter.parent, stdout=f, check=True)


def family_id(size: int) -> int:
    total = 0
    for style in ("regular", "bold"):
        p = FONT_DIR / f"notosymbols_{size}_{style}.h"
        total += int(hashlib.sha256(p.read_bytes()).hexdigest(), 16)
    return total % (2**32) - (2**31)


def patch_all_h() -> None:
    path = FONT_DIR / "all.h"
    text = path.read_text(encoding="utf-8")
    if "#include <builtinFonts/notosymbols_12_regular.h>" in text:
        return
    additions = "\n".join(
        f"#include <builtinFonts/notosymbols_{size}_{style}.h>"
        for size in SIZES
        for style in ("regular", "bold")
    )
    path.write_text(text.rstrip() + "\n" + additions + "\n", encoding="utf-8")


def patch_font_ids() -> None:
    path = ROOT / "src/fontIds.h"
    text = path.read_text(encoding="utf-8")
    if "NOTOSYMBOLS_12_FONT_ID" in text:
        return

    define_anchor = "#define SMALL_FONT_ID (1465627787)\n"
    if define_anchor not in text:
        raise RuntimeError("src/fontIds.h: SMALL_FONT_ID anchor changed")
    defs = "".join(
        f"#define NOTOSYMBOLS_{size}_FONT_ID ({family_id(size)})\n"
        for size in SIZES
    )
    text = text.replace(define_anchor, define_anchor + defs, 1)

    assert_anchor = 'static_assert(SMALL_FONT_ID != 0, "Font ID collision with sentinel");\n'
    if assert_anchor not in text:
        raise RuntimeError("src/fontIds.h: static_assert anchor changed")
    asserts = "".join(
        f'static_assert(NOTOSYMBOLS_{size}_FONT_ID != 0, "Font ID collision with sentinel");\n'
        for size in SIZES
    )
    text = text.replace(assert_anchor, assert_anchor + asserts, 1)
    path.write_text(text, encoding="utf-8")


def patch_main() -> None:
    path = ROOT / "src/main.cpp"
    text = path.read_text(encoding="utf-8")

    if "notosymbols12FontFamily" not in text:
        anchor = '''EpdFontFamily notosans18FontFamily(&notosans18RegularFont, &notosans18BoldFont, &notosans18ItalicFont,
                                   &notosans18BoldItalicFont);

#endif  // OMIT_FONTS
'''
        block_lines = []
        for size in SIZES:
            block_lines += [
                f"EpdFont notosymbols{size}RegularFont(&notosymbols_{size}_regular);",
                f"EpdFont notosymbols{size}BoldFont(&notosymbols_{size}_bold);",
                f"EpdFontFamily notosymbols{size}FontFamily(&notosymbols{size}RegularFont, &notosymbols{size}BoldFont);",
            ]
        block = "\n".join(block_lines) + "\n\n"
        if anchor not in text:
            raise RuntimeError("src/main.cpp: reader-family anchor changed")
        text = text.replace(
            anchor,
            anchor.replace("\n#endif", "\n" + block + "#endif"),
            1,
        )

    if "renderer.insertFont(NOTOSYMBOLS_12_FONT_ID" not in text:
        anchor = '''  renderer.insertFont(NOTOSANS_18_FONT_ID, notosans18FontFamily);
#endif  // OMIT_FONTS
'''
        lines = []
        for size in SIZES:
            lines.append(
                f"  renderer.insertFont(NOTOSYMBOLS_{size}_FONT_ID, notosymbols{size}FontFamily);"
            )
        for family in ("NOTOSERIF", "NOTOSANS"):
            for size in SIZES:
                lines.append(
                    f"  renderer.setFallbackFont({family}_{size}_FONT_ID, NOTOSYMBOLS_{size}_FONT_ID);"
                )
        block = "\n".join(lines) + "\n"
        if anchor not in text:
            raise RuntimeError("src/main.cpp: font registration anchor changed")
        text = text.replace(
            anchor,
            "  renderer.insertFont(NOTOSANS_18_FONT_ID, notosans18FontFamily);\n"
            + block
            + "#endif  // OMIT_FONTS\n",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_gfx_renderer() -> None:
    cpp = ROOT / "lib/GfxRenderer/GfxRenderer.cpp"
    text = cpp.read_text(encoding="utf-8")
    if "Built-in fallback fonts are used for general Unicode coverage" not in text:
        old = r'''int GfxRenderer::resolveTextFontId(const int fontId, const char* text, const EpdFontFamily::Style style) const {
  if (fallbackFontMap_.empty() || text == nullptr || *text == '\0') {
    return fontId;
  }
  const auto fbIt = fallbackFontMap_.find(fontId);
  if (fbIt == fallbackFontMap_.end()) {
    return fontId;  // no fallback registered for this font
  }
  const int fallbackFontId = fbIt->second;
  const auto fontIt = fontMap.find(fontId);
  const auto fallbackIt = fontMap.find(fallbackFontId);
  if (fontIt == fontMap.end() || fallbackIt == fontMap.end()) {
    return fontId;  // unknown primary or fallback not loaded — let the caller handle it
  }
  const EpdFontFamily& primary = fontIt->second;
  const EpdFontFamily& fallback = fallbackIt->second;
  const char* cursor = text;
  uint32_t cp;
  while ((cp = utf8NextCodepoint(reinterpret_cast<const uint8_t**>(&cursor)))) {
    // Only redirect for CJK the primary font cannot draw but the fallback can.
    // Latin/symbol strings the built-in UI fonts already cover are left
    // untouched, and a partial-coverage fallback (e.g. kana-only) is not worth
    // dragging the whole string into for glyphs it would also miss.
    if (utf8IsCjkCodepoint(cp) && !primary.hasCodepoint(cp, style) && fallback.hasCodepoint(cp, style)) {
      return fallbackFontId;
    }
  }
  return fontId;
}
'''
        new = r'''int GfxRenderer::resolveTextFontId(const int fontId, const char* text, const EpdFontFamily::Style style) const {
  if (fallbackFontMap_.empty() || text == nullptr || *text == '\0') {
    return fontId;
  }
  const auto fbIt = fallbackFontMap_.find(fontId);
  if (fbIt == fallbackFontMap_.end()) {
    return fontId;  // no fallback registered for this font
  }
  const int fallbackFontId = fbIt->second;
  const auto fontIt = fontMap.find(fontId);
  const auto fallbackIt = fontMap.find(fallbackFontId);
  if (fontIt == fontMap.end() || fallbackIt == fontMap.end()) {
    return fontId;  // unknown primary or fallback not loaded — let the caller handle it
  }
  const EpdFontFamily& primary = fontIt->second;
  const EpdFontFamily& fallback = fallbackIt->second;

  // SD-card fallbacks are the existing size-matched CJK UI path. Preserve its
  // intentionally narrow behavior.
  if (isSdCardFont(fallbackFontId)) {
    const char* cursor = text;
    uint32_t cp;
    while ((cp = utf8NextCodepoint(reinterpret_cast<const uint8_t**>(&cursor)))) {
      if (utf8IsCjkCodepoint(cp) && !primary.hasCodepoint(cp, style) && fallback.hasCodepoint(cp, style)) {
        return fallbackFontId;
      }
    }
    return fontId;
  }

  // Built-in fallback fonts are used for general Unicode coverage (notably the
  // Noto Sans Symbols family). A whole draw/measure call still uses one font,
  // so redirect only when the primary misses at least one codepoint and the
  // fallback can render the complete token/string.
  bool primaryMissing = false;
  const char* cursor = text;
  uint32_t cp;
  while ((cp = utf8NextCodepoint(reinterpret_cast<const uint8_t**>(&cursor)))) {
    if (primary.hasCodepoint(cp, style)) {
      continue;
    }
    primaryMissing = true;
    if (!fallback.hasCodepoint(cp, style)) {
      return fontId;
    }
  }
  return primaryMissing ? fallbackFontId : fontId;
}
'''
        if text.count(old) != 1:
            raise RuntimeError(
                "lib/GfxRenderer/GfxRenderer.cpp: resolveTextFontId anchor changed"
            )
        cpp.write_text(text.replace(old, new, 1), encoding="utf-8")

    hdr = ROOT / "lib/GfxRenderer/GfxRenderer.h"
    h = hdr.read_text(encoding="utf-8")
    old_comment = '''  // CJK UI font fallback map: primary (built-in, Latin-only) UI font id -> a
  // size-matched SD-card font id that carries CJK glyphs. When a string drawn
  // or measured with a mapped primary font contains a CJK codepoint the primary
  // cannot render, the whole string is routed to the mapped fallback so it
  // appears at the same point size as the surrounding UI text. Populated by the
  // app-level SD font setup when an SD family is loaded. See resolveTextFontId().
'''
    new_comment = '''  // Single-font fallback map. Existing UI entries point to size-matched SD-card
  // CJK fonts; reader entries may point to built-in Unicode/symbol families.
  // resolveTextFontId() keeps each draw/measure call on one font so layout and
  // rendering use identical metrics.
'''
    if old_comment in h:
        h = h.replace(old_comment, new_comment, 1)
    hdr.write_text(h, encoding="utf-8")


def patch_sd_font_system() -> None:
    path = ROOT / "src/SdCardFontSystem.cpp"
    text = path.read_text(encoding="utf-8")

    if "symbolFallbackForPointSize" not in text:
        anchor = '''constexpr UiFontSize kUiFontSizes[] = {
    {SMALL_FONT_ID, 8},
    {UI_10_FONT_ID, 10},
    {UI_12_FONT_ID, 12},
};

}  // namespace
'''
        helper = '''constexpr int symbolFallbackForPointSize(const uint8_t pointSize) {
  if (pointSize <= 13) return NOTOSYMBOLS_12_FONT_ID;
  if (pointSize <= 15) return NOTOSYMBOLS_14_FONT_ID;
  if (pointSize <= 17) return NOTOSYMBOLS_16_FONT_ID;
  return NOTOSYMBOLS_18_FONT_ID;
}

'''
        if anchor not in text:
            raise RuntimeError("src/SdCardFontSystem.cpp: namespace anchor changed")
        text = text.replace(
            anchor,
            anchor.replace("\n}  // namespace", "\n" + helper + "}  // namespace"),
            1,
        )

    if "Reader-size Unicode/symbol fallback" not in text:
        anchor = '''  const auto* family = registry_.findFamily(familyName);
  if (!family) return;

  // Probe the already-loaded reader-size font before paying for the UI sizes:
'''
        replacement = '''  const auto* family = registry_.findFamily(familyName);
  if (!family) return;

  // Reader-size Unicode/symbol fallback. The SD family remains primary; only
  // tokens containing glyphs it lacks, and which the built-in symbol font can
  // fully cover, are redirected by GfxRenderer::resolveTextFontId().
  const int readerFontId = manager_.getFontId(familyName);
  if (readerFontId != 0) {
    renderer.setFallbackFont(readerFontId, symbolFallbackForPointSize(manager_.currentPointSize()));
  }

  // Probe the already-loaded reader-size font before paying for the UI sizes:
'''
        if anchor not in text:
            raise RuntimeError(
                "src/SdCardFontSystem.cpp: setupUiFallbacks anchor changed"
            )
        text = text.replace(anchor, replacement, 1)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    verify_font(REGULAR)
    verify_font(BOLD)
    generate_fonts()
    patch_all_h()
    patch_font_ids()
    patch_main()
    patch_gfx_renderer()
    patch_sd_font_system()
    print("Unicode symbol fallback integration complete.")
    for size in SIZES:
        print(
            f"  {size} pt ID={family_id(size)} "
            f"regular={sha256(FONT_DIR / f'notosymbols_{size}_regular.h')[:12]} "
            f"bold={sha256(FONT_DIR / f'notosymbols_{size}_bold.h')[:12]}"
        )


if __name__ == "__main__":
    main()
