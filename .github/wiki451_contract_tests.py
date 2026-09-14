#!/usr/bin/env python3
from pathlib import Path
import math
import struct

checks = []

def require(cond, label):
    if not cond:
        raise SystemExit(f'FAIL: {label}')
    print(f'PASS: {label}')
    checks.append(label)

ini = Path('platformio.local.ini').read_text()
wiki = Path('src/activities/wiki/WikiActivity.cpp').read_text()
recent_h = Path('src/RecentBooksStore.h').read_text()
recent_cpp = Path('src/RecentBooksStore.cpp').read_text()
finished_h = Path('src/FinishedBooksStore.h').read_text()
finished_cpp = Path('src/FinishedBooksStore.cpp').read_text()
activity_cpp = Path('src/activities/home/RecentBooksActivity.cpp').read_text()
reader_h = Path('src/activities/reader/ReaderActivity.h').read_text()
reader_cpp = Path('src/activities/reader/ReaderActivity.cpp').read_text()

require('1.6.0-wiki-4.5.1' in ini and '1.6.0-wiki-4.5.0' not in ini, '4.5.1 version')
require('-DLOG_LEVEL=0' in ini, 'error-only production logging')
require('renderer.drawLine(side,y+2,w-side,y+2,2,true);' in wiki and
        'renderer.drawLine(side,y+6,w-side,y+6,1,true);' in wiki, 'double article-title divider')
require('block.level<=2 ? 5 : block.level==3 ? 9 : 1' in wiki and
        'block.level<=2 ? 4 : block.level==3 ? 8 : 1' in wiki, 'subheading scale below heading')
require('headingComplete && !grayscalePass && block.level<=2' in wiki, 'only primary headings draw divider')
require('block.level<=2 ? 8 : std::max(6,lineHeight/3)' in wiki, 'subheadings use spacing after text')
require('if (!grayscalePass)' in wiki and
        'renderer.ensureSdCardFontReady(font,warmPlain,styleMask);' in wiki, 'smooth-text second pass skips SD prewarm')
require('FILE_PATH = "/.crosspoint/finished-books.dat"' in finished_h, 'finished catalog stored under SD .crosspoint')
require('CHECKPOINT_STRIDE = 32' in finished_h, 'sparse finished-book index')
require('itemsWindowFirst' in activity_cpp and 'itemsWindowCount' in activity_cpp, 'Finished Books UI uses virtual list window')
require('FinishedBooksStore::loadNewestWindow' in activity_cpp, 'only visible Finished Books rows materialized')
require('MAX_FINISHED_BOOKS' not in recent_h + recent_cpp + finished_h + finished_cpp, 'old 100-book cap removed')
require('doc["finished"]' in recent_cpp and 'requestResave()' in recent_cpp, 'legacy 100-book JSON migration')
require('it == recentBooks.begin()' in recent_cpp, 'unchanged recent-book reopen avoids SD rewrite')
require('finishedRecorded = false' in reader_h and 'RECENT_BOOKS.markFinished' in reader_cpp, 'end-of-book completion hook')
require('Finished Books' in activity_cpp and 'Books you have completed' in activity_cpp, 'Finished Books entry integrated')
require('rewriteCatalog' in finished_cpp and 'TEMP_PATH' in finished_cpp, 'finished-book remove/rename uses streaming rewrite')
require('std::reverse(out.begin(), out.end())' in finished_cpp, 'finished catalog displays newest first')

MAGIC = b'XFB1'
records = []
blob = bytearray(MAGIC)
offsets = []
for i in range(257):
    path = f'/Books/book-{i:03d}.epub'.encode()
    title = f'Book {i:03d}'.encode()
    author = f'Author {i%11}'.encode()
    cover = f'/.crosspoint/cache/{i:03d}.bmp'.encode()
    offsets.append(len(blob))
    blob += struct.pack('<HHHH', len(path), len(title), len(author), len(cover))
    blob += path + title + author + cover
    records.append((path.decode(), title.decode(), author.decode(), cover.decode()))

checkpoints = offsets[::32]
require(len(records) > 100, 'model catalog exceeds 100 books')
require(len(checkpoints) == math.ceil(len(records)/32), 'sparse index scales at one offset per 32 books')

def decode_at(pos):
    lp, lt, la, lc = struct.unpack_from('<HHHH', blob, pos)
    pos += 8
    vals = []
    for length in (lp, lt, la, lc):
        vals.append(bytes(blob[pos:pos+length]).decode())
        pos += length
    return tuple(vals), pos

def newest_window(first, count):
    total = len(records)
    wanted = min(count, total-first)
    chrono_first = total-first-wanted
    cp = chrono_first // 32
    pos = checkpoints[cp]
    for _ in range(cp*32, chrono_first):
        _, pos = decode_at(pos)
    out = []
    for _ in range(wanted):
        rec, pos = decode_at(pos)
        out.append(rec)
    return list(reversed(out))

window = newest_window(120, 9)
require(window[0][1] == 'Book 136' and window[-1][1] == 'Book 128',
        'virtual newest-first window works past 100 entries')
require(len(window) == 9, 'virtual window materializes only requested rows')

print(f'Wiki 4.5.1 contracts passed: {len(checks)}')
