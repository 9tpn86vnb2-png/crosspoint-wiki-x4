#!/usr/bin/env python3
"""Generate and integrate Noto Sans Symbols fallback fonts into the Wiki 4.3 X4 build."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "lib/EpdFont/builtinFonts"
SOURCE_DIR = FONT_DIR / "source/NotoSansSymbols"
REGULAR = SOURCE_DIR / "NotoSansSymbols-Regular.ttf"
BOLD = SOURCE_DIR / "NotoSansSymbols-Bold.ttf"
SIZES = (12, 14, 16, 18)


def cmap_ranges(path: Path) -> list[tuple[int, int]]:
    tt = TTFont(path)
    cps = sorted(cp for cp in (tt.getBestCmap() or {}).keys() if cp >= 0x20 and cp != 0x7F)
    tt.close()
    if not cps:
        raise RuntimeError(f"No printable cmap in {path}")
    out = []
    start = prev = cps[0]
    for cp in cps[1:]:
        if cp == prev + 1:
            prev = cp
        else:
            out.append((start, prev))
            start = prev = cp
    out.append((start, prev))
    return out


def generate() -> None:
    converter = ROOT / "lib/EpdFont/scripts/fontconvert.py"
    interval_args: list[str] = []
    for lo, hi in cmap_ranges(REGULAR):
        interval_args += ["--additional-intervals", f"0x{lo:X},0x{hi:X}"]
    for size in SIZES:
        for style, source in (("regular", REGULAR), ("bold", BOLD)):
            name = f"notosymbols_{size}_{style}"
            target = FONT_DIR / f"{name}.h"
            # Keep the symbol fallback 1-bit. CrossPoint's byte-aligned font
            # compression requires 2-bit input; for this fallback family a
            # raw 1-bit bitmap is both simpler and flash-conscious.
            cmd = [sys.executable, str(converter), name, str(size), str(source), *interval_args]
            print("Generating", target.relative_to(ROOT))
            with target.open("w", encoding="utf-8", newline="\n") as f:
                subprocess.run(cmd, cwd=converter.parent, stdout=f, check=True)


def family_id(size: int) -> int:
    total = 0
    for style in ("regular", "bold"):
        raw = (FONT_DIR / f"notosymbols_{size}_{style}.h").read_bytes()
        total += int(hashlib.sha256(raw).hexdigest(), 16)
    return total % (2**32) - (2**31)


def patch_all_h() -> None:
    path = FONT_DIR / "all.h"
    text = path.read_text(encoding="utf-8")
    if "notosymbols_12_regular.h" in text:
        return
    includes = "".join(
        f"#include <builtinFonts/notosymbols_{size}_{style}.h>\n"
        for size in SIZES for style in ("regular", "bold")
    )
    path.write_text(text.rstrip() + "\n" + includes, encoding="utf-8")


def patch_font_ids() -> None:
    path = ROOT / "src/fontIds.h"
    text = path.read_text(encoding="utf-8")
    if "NOTOSYMBOLS_12_FONT_ID" in text:
        return
    anchor = "#define SMALL_FONT_ID (1465627787)\n"
    if anchor not in text:
        raise RuntimeError("src/fontIds.h SMALL_FONT_ID anchor changed")
    defs = "".join(f"#define NOTOSYMBOLS_{s}_FONT_ID ({family_id(s)})\n" for s in SIZES)
    text = text.replace(anchor, anchor + defs, 1)
    assert_anchor = 'static_assert(SMALL_FONT_ID != 0, "Font ID collision with sentinel");\n'
    if assert_anchor not in text:
        raise RuntimeError("src/fontIds.h static_assert anchor changed")
    checks = "".join(
        f'static_assert(NOTOSYMBOLS_{s}_FONT_ID != 0, "Font ID collision with sentinel");\n'
        for s in SIZES
    )
    path.write_text(text.replace(assert_anchor, assert_anchor + checks, 1), encoding="utf-8")


def patch_main() -> None:
    path = ROOT / "src/main.cpp"
    text = path.read_text(encoding="utf-8")
    if "notosymbols12FontFamily" not in text:
        anchor = """EpdFontFamily notosans18FontFamily(&notosans18RegularFont, &notosans18BoldFont, &notosans18ItalicFont,
                                   &notosans18BoldItalicFont);

#endif  // OMIT_FONTS
"""
        if anchor not in text:
            raise RuntimeError("src/main.cpp family anchor changed")
        lines = []
        for s in SIZES:
            lines += [
                f"EpdFont notosymbols{s}RegularFont(&notosymbols_{s}_regular);",
                f"EpdFont notosymbols{s}BoldFont(&notosymbols_{s}_bold);",
                f"EpdFontFamily notosymbols{s}FontFamily(&notosymbols{s}RegularFont, &notosymbols{s}BoldFont);",
            ]
        text = text.replace(anchor, anchor.replace("\n#endif", "\n" + "\n".join(lines) + "\n\n#endif"), 1)

    if "renderer.insertFont(NOTOSYMBOLS_12_FONT_ID" not in text:
        anchor = """  renderer.insertFont(NOTOSANS_18_FONT_ID, notosans18FontFamily);
#endif  // OMIT_FONTS
"""
        if anchor not in text:
            raise RuntimeError("src/main.cpp registration anchor changed")
        lines = []
        for s in SIZES:
            lines.append(f"  renderer.insertFont(NOTOSYMBOLS_{s}_FONT_ID, notosymbols{s}FontFamily);")
        for family in ("NOTOSERIF", "NOTOSANS"):
            for s in SIZES:
                lines.append(f"  renderer.setFallbackFont({family}_{s}_FONT_ID, NOTOSYMBOLS_{s}_FONT_ID);")
        text = text.replace(anchor, "  renderer.insertFont(NOTOSANS_18_FONT_ID, notosans18FontFamily);\n" + "\n".join(lines) + "\n#endif  // OMIT_FONTS\n", 1)
    path.write_text(text, encoding="utf-8")


def patch_renderer() -> None:
    path = ROOT / "lib/GfxRenderer/GfxRenderer.cpp"
    text = path.read_text(encoding="utf-8")
    if "Built-in fallback fonts are used for general Unicode coverage" in text:
        return
    old = '''int GfxRenderer::resolveTextFontId(const int fontId, const char* text, const EpdFontFamily::Style style) const {
  if (fallbackFontMap_.empty() || text == nullptr || *text == '\\0') {
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
    new = '''int GfxRenderer::resolveTextFontId(const int fontId, const char* text, const EpdFontFamily::Style style) const {
  if (fallbackFontMap_.empty() || text == nullptr || *text == '\\0') return fontId;
  const auto fbIt = fallbackFontMap_.find(fontId);
  if (fbIt == fallbackFontMap_.end()) return fontId;
  const int fallbackFontId = fbIt->second;
  const auto fontIt = fontMap.find(fontId);
  const auto fallbackIt = fontMap.find(fallbackFontId);
  if (fontIt == fontMap.end() || fallbackIt == fontMap.end()) return fontId;
  const EpdFontFamily& primary = fontIt->second;
  const EpdFontFamily& fallback = fallbackIt->second;

  // SD-card fallbacks remain the existing CJK-only UI path.
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

  // Built-in fallback fonts are used for general Unicode coverage. Keep each
  // measure/draw call on one font: redirect only when the primary misses at
  // least one codepoint AND the fallback can render the complete token/string.
  bool primaryMissing = false;
  const char* cursor = text;
  uint32_t cp;
  while ((cp = utf8NextCodepoint(reinterpret_cast<const uint8_t**>(&cursor)))) {
    if (primary.hasCodepoint(cp, style)) continue;
    primaryMissing = true;
    if (!fallback.hasCodepoint(cp, style)) return fontId;
  }
  return primaryMissing ? fallbackFontId : fontId;
}
'''
    if text.count(old) != 1:
        raise RuntimeError("GfxRenderer::resolveTextFontId anchor changed")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_sd_fonts() -> None:
    path = ROOT / "src/SdCardFontSystem.cpp"
    text = path.read_text(encoding="utf-8")
    if "symbolFallbackForPointSize" not in text:
        anchor = """constexpr UiFontSize kUiFontSizes[] = {
    {SMALL_FONT_ID, 8},
    {UI_10_FONT_ID, 10},
    {UI_12_FONT_ID, 12},
};

}  // namespace
"""
        if anchor not in text:
            raise RuntimeError("SdCardFontSystem namespace anchor changed")
        helper = '''constexpr int symbolFallbackForPointSize(const uint8_t pointSize) {
  if (pointSize <= 13) return NOTOSYMBOLS_12_FONT_ID;
  if (pointSize <= 15) return NOTOSYMBOLS_14_FONT_ID;
  if (pointSize <= 17) return NOTOSYMBOLS_16_FONT_ID;
  return NOTOSYMBOLS_18_FONT_ID;
}

'''
        text = text.replace(anchor, anchor.replace("\n}  // namespace", "\n" + helper + "}  // namespace"), 1)
    if "Reader-size Unicode/symbol fallback" not in text:
        anchor = """  const auto* family = registry_.findFamily(familyName);
  if (!family) return;

  // Probe the already-loaded reader-size font before paying for the UI sizes:
"""
        replacement = """  const auto* family = registry_.findFamily(familyName);
  if (!family) return;

  // Reader-size Unicode/symbol fallback for custom SD-card reader fonts.
  const int readerFontId = manager_.getFontId(familyName);
  if (readerFontId != 0) {
    renderer.setFallbackFont(readerFontId, symbolFallbackForPointSize(manager_.currentPointSize()));
  }

  // Probe the already-loaded reader-size font before paying for the UI sizes:
"""
        if anchor not in text:
            raise RuntimeError("SdCardFontSystem setupUiFallbacks anchor changed")
        text = text.replace(anchor, replacement, 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    if not REGULAR.exists() or not BOLD.exists():
        raise RuntimeError("Run scripts/prepare_unicode_symbols.py first")
    generate()
    patch_all_h()
    patch_font_ids()
    patch_main()
    patch_renderer()
    patch_sd_fonts()
    print("Unicode symbol compatibility integrated into Wiki 4.3 build.")
    for s in SIZES:
        print(f"  {s} pt symbol family ID: {family_id(s)}")


if __name__ == "__main__":
    main()
