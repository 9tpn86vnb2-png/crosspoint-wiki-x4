#!/usr/bin/env python3
from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'4.5.2: {label} anchor not found')
    return text.replace(old, new, 1)

# EPUB completion: EpubReaderActivity owns its own loop(), so the generic
# ReaderActivity 4.5.1 completion hook never runs for EPUBs. Record completion
# when the real final page is fully known/displayed, with the existing
# post-book sentinel retained as a fallback. Also honor the reader's displayed
# rounded 100% once pagination is complete so UI and Finished Books agree.
epub = Path('src/activities/reader/EpubReaderActivity.cpp')
s = epub.read_text()
old = '''  const bool atEndOfBook = currentSpineIndex > 0 && currentSpineIndex >= epub->getSpineItemsCount();
  clearEndOfBookOptionsIfNeeded();
'''
new = '''  const int spineCount = epub->getSpineItemsCount();
  const bool atEndOfBook = currentSpineIndex > 0 && currentSpineIndex >= spineCount;
  const bool paginationComplete = section && !section->isBuilding() && !section->isPartial() &&
                                  section->pageCount > 0;
  const bool atFinalRenderedPage = paginationComplete && spineCount > 0 &&
                                   currentSpineIndex == spineCount - 1 &&
                                   section->currentPage >= static_cast<int>(section->pageCount) - 1;
  bool displayedHundredPercent = false;
  if (!atEndOfBook && paginationComplete && epub->getBookSize() > 0 && section->estimatedTotalPages() > 0) {
    const float chapterProgress = static_cast<float>(section->currentPage) /
                                  static_cast<float>(section->estimatedTotalPages());
    const float bookProgress = epub->calculateProgress(currentSpineIndex, chapterProgress) * 100.0f;
    displayedHundredPercent = clampPercent(static_cast<int>(bookProgress + 0.5f)) >= 100;
  }
  if ((atFinalRenderedPage || displayedHundredPercent || atEndOfBook) && !finishedRecorded) {
    RECENT_BOOKS.markFinished(epub->getPath(), epub->getTitle(), epub->getAuthor(), epub->getThumbBmpPath());
    finishedRecorded = true;
  }
  clearEndOfBookOptionsIfNeeded();
'''
s = replace_once(s, old, new, 'EPUB completion hook')
epub.write_text(s)

# Finished Books UI: use a dedicated book-with-check icon and insert the
# existing section-heading/underline treatment before the first recent book.
recent = Path('src/activities/home/RecentBooksActivity.cpp')
r = recent.read_text()
r = replace_once(
    r,
    '  finished.icon = listIconFor(Book, 32);\n',
    '  finished.icon = freeink::ui::bitmapFromIcon(icon_finished_book_32);\n',
    'Finished Books checkmark icon',
)
r = replace_once(
    r,
    '''    item.icon = listIconFor(UITheme::getFileIcon(book.path), 32);
    item.actionValue = static_cast<int16_t>(rowItems.size());
    rowItems.push_back(item);
''',
    '''    item.icon = listIconFor(UITheme::getFileIcon(book.path), 32);
    // Visually separate the Finished Books shortcut from the recent-book list.
    // FreeInkUI renders sectionHeading with its standard underline divider.
    if (rowItems.size() == 1) item.sectionHeading = tr(STR_MENU_RECENT_BOOKS);
    item.actionValue = static_cast<int16_t>(rowItems.size());
    rowItems.push_back(item);
''',
    'Recent Books divider',
)
recent.write_text(r)

# Hand-maintained 32px monochrome icon: book outline with a checkmark crossing
# the lower-right corner. 1 bits are white and 0 bits are ink, matching the
# generated/custom list icon format already used by CrossPoint.
icons = Path('src/components/icons/customListIcons.h')
i = icons.read_text()
if 'icon_finished_book_32' in i:
    raise SystemExit('4.5.2: Finished Books icon already present')
icon_block = r'''

// finished-book  (custom: book with lower-right checkmark)
static const uint8_t icon_finished_book_32_bits[] = {
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    0xF8, 0x00, 0x00, 0x7F, 0xF8, 0x00, 0x00, 0x7F, 0xF9, 0xBF, 0xFE, 0x7F, 0xF9, 0xBF, 0xFE, 0x7F,
    0xF9, 0xBF, 0xFE, 0x7F, 0xF9, 0xA0, 0x06, 0x7F, 0xF9, 0xBF, 0xFE, 0x7F, 0xF9, 0xBF, 0xFE, 0x7F,
    0xF9, 0xBF, 0xFE, 0x7F, 0xF9, 0xA0, 0x06, 0x7F, 0xF9, 0xBF, 0xFE, 0x7F, 0xF9, 0xBF, 0xFE, 0x7F,
    0xF9, 0xBF, 0xFE, 0x7F, 0xF9, 0xBF, 0xFF, 0xF9, 0xF9, 0xBF, 0xFF, 0xF1, 0xF9, 0xBF, 0xFF, 0xE3,
    0xF9, 0xBF, 0xFF, 0xE7, 0xF9, 0xBF, 0xFF, 0xC7, 0xF9, 0xBF, 0xCF, 0x8F, 0xF9, 0xBF, 0xC7, 0x1F,
    0xF9, 0xBF, 0xE3, 0x3F, 0xF9, 0xBF, 0xF0, 0x3F, 0xF8, 0x00, 0x78, 0x7F, 0xF8, 0x00, 0x7C, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static const freeink::Icon icon_finished_book_32 = {32, 32, 16, icon_finished_book_32_bits};
'''
icons.write_text(i + icon_block)

# Version bump.
ini = Path('platformio.local.ini')
p = ini.read_text()
if '1.6.0-wiki-4.5.1' not in p:
    raise SystemExit('4.5.2: expected 4.5.1 version not found')
p = p.replace('1.6.0-wiki-4.5.1', '1.6.0-wiki-4.5.2')
ini.write_text(p)

print('Wiki 4.5.2 EPUB completion + Finished Books UI patch applied.')
