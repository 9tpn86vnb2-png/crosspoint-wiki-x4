#!/usr/bin/env python3
from pathlib import Path
import re

checks = []

def check(label, ok):
    if not ok:
        raise SystemExit(f'FAIL: {label}')
    print(f'PASS: {label}')
    checks.append(label)

ini = Path('platformio.local.ini').read_text()
epub = Path('src/activities/reader/EpubReaderActivity.cpp').read_text()
recent = Path('src/activities/home/RecentBooksActivity.cpp').read_text()
icons = Path('src/components/icons/customListIcons.h').read_text()
reader_h = Path('src/activities/reader/ReaderActivity.h').read_text()
reader_cpp = Path('src/activities/reader/ReaderActivity.cpp').read_text()

check('4.5.2 version', '1.6.0-wiki-4.5.2' in ini and '1.6.0-wiki-4.5.1' not in ini)
check('finished state retained in ReaderActivity', 'bool finishedRecorded = false;' in reader_h)
check('generic completion fallback retained', 'if (isAtEndOfBook() && !finishedRecorded)' in reader_cpp)
check('EPUB owns an explicit completion hook', 'const bool atFinalRenderedPage' in epub and 'RECENT_BOOKS.markFinished(epub->getPath()' in epub)
check('EPUB final-page completion waits for stable pagination', '!section->isBuilding()' in epub and '!section->isPartial()' in epub)
check('EPUB exact last page recognized', 'currentSpineIndex == spineCount - 1' in epub and 'section->currentPage >= static_cast<int>(section->pageCount) - 1' in epub)
check('displayed 100 percent recognized', 'displayedHundredPercent' in epub and 'clampPercent(static_cast<int>(bookProgress + 0.5f)) >= 100' in epub)
check('post-book sentinel remains completion fallback', '(atFinalRenderedPage || displayedHundredPercent || atEndOfBook)' in epub)
check('completion is sticky once recorded', '&& !finishedRecorded' in epub and 'finishedRecorded = true;' in epub)
check('existing recents removal still uses end sentinel only', 'if (atEndOfBook && !recentsEntryRemoved)' in epub)
check('existing move-to-read behavior still uses end sentinel only', 'if (atEndOfBook) {\n    pendingReadFolderMove' in epub)
check('Finished Books uses book-check icon', 'icon_finished_book_32' in recent and 'bitmapFromIcon(icon_finished_book_32)' in recent)
check('Recent Books divider uses standard section heading', 'item.sectionHeading = tr(STR_MENU_RECENT_BOOKS)' in recent)
check('finished icon is hand-maintained custom asset', 'custom: book with lower-right checkmark' in icons)
hexes = re.findall(r'0x[0-9A-Fa-f]{2}', icons.split('icon_finished_book_32_bits[]', 1)[1].split('};', 1)[0])
check('finished icon has complete 32x32 bitmap', len(hexes) == 128)

# Small policy model: fully built last page must complete without requiring a
# page turn past the end. Building/partial pages must not be trusted as final.
def complete(spine, spine_count, page, page_count, building=False, partial=False, shown_pct=0, sentinel=False):
    stable = page_count > 0 and not building and not partial
    final_page = stable and spine_count > 0 and spine == spine_count - 1 and page >= page_count - 1
    shown_100 = stable and shown_pct >= 100
    return final_page or shown_100 or sentinel

check('model final displayed page completes', complete(9, 10, 42, 43))
check('model does not trust partial last-looking page', not complete(9, 10, 10, 11, partial=True))
check('model does not trust actively building page', not complete(9, 10, 10, 11, building=True))
check('model displayed 100 completes', complete(8, 10, 15, 20, shown_pct=100))
check('model ordinary page remains unfinished', not complete(8, 10, 15, 20, shown_pct=83))

print(f'Wiki 4.5.2 contracts passed: {len(checks)}')
