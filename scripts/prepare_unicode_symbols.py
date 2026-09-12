#!/usr/bin/env python3
"""Prepare pinned Noto Sans Symbols v2.003 static faces for the Unicode X4 build."""
from __future__ import annotations

import hashlib
import struct
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "lib/EpdFont/builtinFonts/source/NotoSansSymbols"
GOOGLE_FONTS_COMMIT = "809e4d8b8d7e9364a914909bb777679606c178b8"
URL = (
    "https://raw.githubusercontent.com/google/fonts/"
    + GOOGLE_FONTS_COMMIT
    + "/ofl/notosanssymbols/NotoSansSymbols%5Bwght%5D.ttf"
)
OFL_URL = (
    "https://raw.githubusercontent.com/google/fonts/"
    + GOOGLE_FONTS_COMMIT
    + "/ofl/notosanssymbols/OFL.txt"
)
EXPECTED_GIT_BLOB = "a0061bfbcbbec27bf2b280fc8c49ea42cf7cb7ab"
EXPECTED_CMAP_SHA256 = "52909156e74919f23c52ded660da993a46c3540daa399dd5e3ea1ef11ef2d9f6"
EXPECTED_CMAP_COUNT = 1107
EXPECTED_VERSION = "Version 2.003"


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def cmap_digest(font: TTFont) -> tuple[int, str]:
    cps = sorted((font.getBestCmap() or {}).keys())
    payload = b"".join(struct.pack(">I", cp) for cp in cps)
    return len(cps), hashlib.sha256(payload).hexdigest()


def verify(font: TTFont, label: str) -> None:
    versions = {r.toUnicode() for r in font["name"].names if r.nameID == 5}
    if EXPECTED_VERSION not in versions:
        raise RuntimeError(f"{label}: expected {EXPECTED_VERSION}, got {sorted(versions)}")
    count, digest = cmap_digest(font)
    if count != EXPECTED_CMAP_COUNT or digest != EXPECTED_CMAP_SHA256:
        raise RuntimeError(
            f"{label}: cmap differs from uploaded v2.003 source: count={count}, sha256={digest}"
        )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    variable_path = OUT / "NotoSansSymbols-VariableFont_wght.ttf"
    data = urllib.request.urlopen(URL, timeout=60).read()
    blob = git_blob_sha1(data)
    if blob != EXPECTED_GIT_BLOB:
        raise RuntimeError(f"Pinned Google Fonts blob mismatch: {blob}")
    variable_path.write_bytes(data)

    variable = TTFont(variable_path)
    verify(variable, "variable source")
    for weight, label in ((400, "Regular"), (700, "Bold")):
        instance = instantiateVariableFont(variable, {"wght": weight}, inplace=False)
        verify(instance, label)
        path = OUT / f"NotoSansSymbols-{label}.ttf"
        instance.save(path)
        print(f"Prepared {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")
    variable.close()

    ofl = urllib.request.urlopen(OFL_URL, timeout=60).read()
    (OUT / "OFL.txt").write_bytes(ofl)
    print("Noto Sans Symbols source verified against uploaded v2.003 cmap.")


if __name__ == "__main__":
    main()
