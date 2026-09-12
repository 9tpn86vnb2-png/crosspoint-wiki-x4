# CrossPoint Wiki 4.3 — spacing and internal-link typography

- Builds on Wiki 4.2 typography and keeps native WCDB plus uncompressed MediaWiki XML reading.
- Diagnostic work used the supplied `enwikiversity-2026-09-01-p1p331750.xml.bz2` dump as a real-world MediaWiki markup reference. The sampled source uses ordinary MediaWiki emphasis/link syntax; the major visible spacing inconsistency came from Wiki 4.2's justification policy, not from XML syntax.
- Wiki 4.2 could expand inter-word gaps to as much as 3x the selected font's natural space width. Long bold/italic/link labels made some lines look noticeably looser than neighboring lines.
- Wiki 4.3 keeps justification conservative: at least four words are required, natural spaces are accounted for explicitly, and additional stretch is capped at 75% of the natural total gap width. Lines that would need larger gaps fall back to normal spacing rather than producing typographic “rivers.”
- MediaWiki internal links (`[[Article]]` and `[[Article|label]]`) are now preserved as zero-width inline link spans instead of being flattened to indistinguishable text.
- Internal-link labels are underlined in the article reading view. The underline composes with regular, bold, italic, and bold-italic text without changing the selected font face.
- File/Image/Category inclusions remain non-link presentation content and are not underlined.
- Link-state markers are internal control bytes added only after XML parsing; they are stripped from display-width/prewarm text and preserved across wrapped lines without consuming glyph width.
- Existing 4.2 heading hierarchy, font-family selection, `.cpfont` support, anti-aliasing, independent Wiki orientation, portrait menus, landscape article layout, saved articles, XML indexing, and WCDB behavior remain intact.
- `.xml.gz`, `.xml.bz2`, and ZIM are still not native input formats in this typography-focused build. The supplied `.bz2` file was used as a development/reference corpus after desktop decompression.
- Application-only ESP32-C3 image for original X4/X3. Do not flash as a full image or use on X4 Pro/X4C.
- Hardware test required; keep the last known-good build available as fallback.
