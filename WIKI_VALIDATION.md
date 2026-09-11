# Wiki beta validation notes

These notes supplement WIKI_BETA.md. A firmware artifact is produced only after
its build and verification jobs succeed. The artifact's own build-manifest.json
and logs identify the exact source revision and results. Hardware testing is
not claimed.

## Corrections made during development

The first complete firmware compilation stopped because the Almanac reference
used a Bitter font identifier absent from CrossPoint 1.6.0. WikiActivity now
uses the actual NOTOSERIF_16_FONT_ID declared by CrossPoint's fontIds.h.
No failed build's firmware is offered as a working candidate.

Additional random-input testing of CrossPoint's existing uzlib decoder found
an out-of-bounds read: a negative error returned by tinf_decode_symbol could
be used as an index into the distance tables. The guarded wiki_harden.py script
adds two checks: reject negative literal symbols and negative distance symbols.
It refuses an unreviewed dependency revision. The original notices in uzlib
remain, and the modifications are marked in the generated C source.

The packaging step refuses an image when the working source lacks that exact
fix. This is a build-process check, not a claim of formally verified software.
The modified decoder source is included in wiki-changed-source.tar.gz with its
SHA-256 in the manifest. The complete upstream sources and dependencies remain
available through this repository and its pinned submodules.

## Host verification

The original archive suite uses the real WikiArchive.cpp with host storage and
Arduino adapters and a zlib reference decoder. The native verification suite
then recompiles with the actual CrossPoint InflateReader.cpp and uzlib C code.
Both use AddressSanitizer and UndefinedBehaviorSanitizer.

The native suite repeats exact/prefix lookup, navigation, redirect, bounds and
corrupted-file assertions; adds 50,000 seeded random compressed inputs; and
compares every block of the SHA-pinned published Wikipedia pack byte for byte
against host zlib. The expected reference pack has 267,396 entries in 3,808
blocks, totaling 123,306,325 uncompressed bytes. Those are database records,
not a guarantee of that many complete, unabridged Wikipedia articles.

Separate local tests exercised the exact single-line wrapping function with
six deterministic cases and 10,000 seeded malformed-text/pagination cases,
using synthetic font widths. The generated menu mapping was tested with and
without OPDS and with constrained menu windows. Those are not real-screen or
physical-button tests.

## Build reproduction update

On a clean checkout, run `python scripts/wiki_harden.py` before the integration
and build steps in WIKI_BETA.md. For the complete host verification, use
`python scripts/wiki_native_verify.py` in place of the older zlib-only command.
The GitHub workflow performs both steps automatically. Read that workflow for
the actual dependency versions; the toolchain and external dependencies are
not all immutable, so byte-for-byte reproducibility is not promised.

## What still needs an original X4

Real boot/recovery behavior, available heap, e-ink layout and refresh, font
appearance, button responsiveness, SD-card removal, sleep/wake, and normal book
reading alongside the Wiki activity all require hardware testing. The candidate
is experimental even when the compiler, host tests and image checks pass.
It is not for an ESP32-S3 X4 Pro/X4C or an unverified locked/dualboot setup.
