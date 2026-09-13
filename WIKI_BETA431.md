# CrossPoint Wiki 4.3.1 — original X4/X3 only

- Wiki text presets are independent from the native EPUB reader: font family, point size, line spacing, paragraph spacing, alignment, and screen margin are stored under the Wiki `wikibeta` profile.
- Existing independent Wiki orientation and text smoothing remain unchanged.
- Entering Wiki snapshots the native reader text profile; leaving Wiki restores it in RAM. Wiki text-setting changes are persisted only to the Wiki profile, not `/.crosspoint/settings.json`.
- Internal MediaWiki article-reference underlines are now 2 pixels thick for clearer visibility while keeping the same measured text width.
- Section headings receive a solid rule after the final wrapped heading line (2 px for level-2 headings, 1 px for subheadings) with layout spacing after the rule.
- Article chrome is condensed into one themed header banner in `Library: Article` form. The library label uses the small UI font and the article title uses a compact bold UI font, reclaiming the former multiline title area for reading.
- Native themed battery/status behavior remains in the header.
- Wiki 4.3 spacing/justification fixes, bold/italic/bold-italic rendering, XML/WCDB support, saved articles, and independent orientation are preserved.
- `.xml.gz`, `.xml.bz2`, and ZIM are still not native inputs in 4.3.1.
- Application-only ESP32-C3 image; not a full-flash image and not for X4 Pro/X4C.
- Hardware test required; keep the known-good fallback until verified.
