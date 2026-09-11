# CrossPoint + Wiki beta 2 — original Xteink X4

This update adds a search-first Wiki screen, bookmarks, a visible Random action,
and a cleaner text presentation to the integrated CrossPoint 1.6.0 Wiki beta.
It is unofficial, experimental, and not hardware-tested by the build process.
The user's successful beta 1 installation does not certify this new version.

## Upgrade from the working beta 1

Keep a copy of the working beta 1 firmware and back up your SD card/settings.
Use the same compatible original-X4 custom-application update route that worked
for beta 1, selecting only `crosspoint-1.6.0-wiki-beta2-x4-UNTESTED.bin`.
Do not select the ZIP, erase the flash, change the partition table, or write the
application at address zero. This package has no bootloader or dualboot data.
It is not for the ESP32-S3 X4 Pro or X4 Classic. Unknown or USB-locked recovery
configurations still require separate verification before experimenting.

Keep your existing tested `wikipedia.cdb` in place. No data migration, replacement
encyclopedia download, or coding is required. All UI changes are in the firmware.

## The new Wiki start screen

The home-menu icon is an original circle-grid globe, drawn without adding a
font file. It is wired for Classic, Lyra and Rounded Raff themes.
Opening Wiki now shows a focused `Search Wikipedia...` field, a visible
`Random article` action, and `Bookmarks`. It does not open an article first.

Select Search with Confirm to open the existing CrossPoint on-screen keyboard.
After submitting a title, choose a match from a results list. The list keeps at
most 16 matches (and a bounded string budget); refine the query when it says
there are more. This is prefix title search, not full-text search or live search
while typing. Multiword input such as `Albert Einstein` also matches the
published pack's hyphenated title keys; matching is ASCII case-insensitive.
This is a WikiReader-inspired workflow, not a pixel-perfect recreation.

## Controls

On the Wiki start screen, results, bookmark list or article options:
Left/Right or side Up/Down moves the selection, Confirm opens it, Back returns.

While reading:
- Side Up/Down: previous/next page in the same article.
- Front Left/Right: previous/next archive entry, as in beta 1.
- Tap Confirm: open Article options.
- Hold Confirm: save/remove this article's bookmark (changed from beta 1).
- Tap Back: return to the Wiki start screen; Back again returns to CrossPoint.
- Hold Back: cycle three body-text sizes.

Article options contains Save/Remove bookmark, Random article, Search Wikipedia,
Change text size, Show original pack text/Use clean reading view, and Back.
Shortcuts follow CrossPoint's mapped logical buttons. Hold threshold is 600 ms.
Random selects a block then an entry, so it is not a uniform sample of all titles.

## Bookmarks

Bookmarks save immediately on the SD card and are loaded when Wiki opens again.
They save article titles, not a page position or a second copy of the article.
There is a 64-bookmark ceiling and a 16 KiB serialized-title budget; unusually
long titles may reach the byte limit first. Remove an old bookmark to make room.
Opening a saved article starts it at the beginning.

Two alternating, CRC-checked snapshots are used:
`/.crosspoint/wiki/bookmarks.a` and `/.crosspoint/wiki/bookmarks.b`.
Back up the whole `/.crosspoint/wiki/` folder to preserve them. The firmware
creates this folder automatically; it does not modify wikipedia.cdb.
A detected failed write retains the prior accepted snapshot; damaged new data
falls back to the older one. This is not a guarantee against every SD-card or
power-loss failure. If both files are damaged, saving is disabled rather than
silently replacing them. Keep the damaged files for recovery before resetting.

## Reading appearance and the image limitation

Clean reading view is on by default. It uses a serif article title, a separator,
sans-serif body text, wider margins, and paragraph spacing. It strips repeated
leading titles and recognizable image-display switches such as `thumb|` and
`250px|`, while retaining following captions and prose. Numeric references are
smaller; explicit headings and identifiable short caption/reference blocks use
different styles when the pack actually contains those markers.

The tested WCDB pack contains flattened plain-text excerpts, including leftover
image markup, but no embedded picture payloads. Beta 2 therefore does not render
images. Captions are not pictures. Image support needs a separate data format or
image pack plus a tested decoder path; renaming a file does not add it.

Many original Wikipedia paragraphs, sections, formulas, links and full article
bodies were already lost or shortened when this pack was generated. The firmware
cannot reconstruct them. Long flattened excerpts get visual paragraph breaks
at sentence boundaries; these are layout choices, not original Wikipedia
paragraph boundaries. A caption without an explicit ending cannot reliably be
separated from adjacent prose, so the entire remaining article is not shrunk.
Use `Show original pack text` to disable cleanup and compare with the stored
text. The clean-view preference and selected text size persist on normal exit.

There is still no native ZIM, online article download, selectable article link,
full-text search, or image rendering. CrossPoint's normal book renderer is
retained; Microreader is not included. Global history and resume-page bookmarks
are not implemented in this iteration.

## Compatible Wikipedia data and attribution

The existing reference pack remains unchanged:
https://github.com/Sparkadium/crosspoint-reader-almanac/releases/download/v1.1.0-almanac/wikipedia.cdb

Size: 48,523,777 bytes.
SHA-256: c994f024322352de9e8ec96092834b2296f2304400337a016dc7a8eedf0e2b30

Place it at `/wikipedia.cdb` or `/Wikipedia/wikipedia.cdb`; the root file wins.
This is Simple English Wikipedia, not all of English Wikipedia. The 267,396
indexed records include redirects and are not all full-length articles.
Content credit: Simple English Wikipedia contributors, applicable CC BY-SA;
WCDB compilation by Sparkadium / CrossInk Almanac. See the source release and
its licensing information. The firmware's MIT license does not relicense
Wikipedia content. No external font files or image assets are bundled.

## Build and test boundary

CrossPoint base: 54337e6d73fc628f4ba523ddc89a743ca8c6e4c5 (1.6.0).
Branch: wiki-x4-beta; develop remains unchanged.
The successful artifact, not this source file, establishes compilation status.
The workflow retains the beta 1 native InflateReader/uzlib sanitizer tests and
all-block comparison with the pinned published pack. Additional host tests run
the real beta 2 UI, text, archive and bookmark C++ against simulated storage,
keyboard and fonts, including short-write/corruption recovery and malformed
UTF-8. These are not a display emulator, measured ESP32 heap test or hardware
validation. The actual ESP32-C3 build and image/partition checks run separately.

Inspect the included build manifest and logs for exact identities and results.
Device testing should cover entry/search/cancel, save/restart/remove, Random,
page turns, original-text toggle, all themes, sleep/wake and ordinary EPUBs.
Stop using the beta if it freezes or restarts repeatedly; use only your already
established recovery/update route, not guessed flash-erasing instructions.
