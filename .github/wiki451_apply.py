#!/usr/bin/env python3
from pathlib import Path
import shutil

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'4.5.1: {label} anchor not found')
    return text.replace(old, new, 1)

templates = {
    '.github/wiki451/FinishedBooksStore.h': 'src/FinishedBooksStore.h',
    '.github/wiki451/FinishedBooksStore.cpp': 'src/FinishedBooksStore.cpp',
    '.github/wiki451/RecentBooksStore.h': 'src/RecentBooksStore.h',
    '.github/wiki451/RecentBooksStore.cpp': 'src/RecentBooksStore.cpp',
    '.github/wiki451/RecentBooksActivity.h': 'src/activities/home/RecentBooksActivity.h',
    '.github/wiki451/RecentBooksActivity.cpp': 'src/activities/home/RecentBooksActivity.cpp',
}
for src, dst in templates.items():
    p = Path(dst)
    p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

header = Path('src/activities/reader/ReaderActivity.h')
h = header.read_text()
h = replace_once(
    h,
    '  bool forcedRefreshPending = false;\n',
    '  bool forcedRefreshPending = false;\n  bool finishedRecorded = false;\n',
    'reader finished state',
)
header.write_text(h)

reader = Path('src/activities/reader/ReaderActivity.cpp')
r = reader.read_text()
r = replace_once(
    r,
    '''void ReaderActivity::loop() {
  clearEndOfBookOptionsIfNeeded();
''',
    '''void ReaderActivity::loop() {
  if (isAtEndOfBook() && !finishedRecorded) {
    RECENT_BOOKS.markFinished(bookPath, getBookTitle(), getBookAuthor(), getBookThumbBmpPath());
    finishedRecorded = true;
  }

  clearEndOfBookOptionsIfNeeded();
''',
    'reader end-of-book hook',
)
reader.write_text(r)

wiki = Path('src/activities/wiki/WikiActivity.cpp')
w = wiki.read_text()
w = replace_once(
    w,
    '''    if (!grayscalePass && titleLines>0 && y+3<bottom) renderer.drawLine(side,y+2,w-side,y+2,2,true);
    if (titleLines>0) y+=10;
''',
    '''    if (!grayscalePass && titleLines>0 && y+7<bottom) {
      renderer.drawLine(side,y+2,w-side,y+2,2,true);
      renderer.drawLine(side,y+6,w-side,y+6,1,true);
    }
    if (titleLines>0) y+=14;
''',
    'double article title rule',
)
w = replace_once(
    w,
    '''    const int headingNum=block.level<=2 ? 5 : block.level==3 ? 6 : 1;
    const int headingDen=block.level<=2 ? 4 : block.level==3 ? 5 : 1;
''',
    '''    // Primary headings stay prominent. Subheadings are bold through WikiHeading,
    // slightly smaller, and rely on paragraph spacing rather than divider rules.
    const int headingNum=block.level<=2 ? 5 : block.level==3 ? 9 : 1;
    const int headingDen=block.level<=2 ? 4 : block.level==3 ? 8 : 1;
''',
    'heading scale hierarchy',
)
w = replace_once(w, '      if (heading) y+=12;\n', '      if (heading) y+=block.level<=2 ? 12 : 10;\n',
                 'heading top spacing')

old_warm = '''    // Bound prewarming to a small, UTF-8-valid run rather than the full article.
    char warm[512];size_t consumed=cursor.offset,n=0;
    while (consumed<block.end && n+4<sizeof(warm)) {
      const size_t len=WikiText::utf8Length(entry_.text,consumed,block.end);
      if (!len) { warm[n++]='?';++consumed; }
      else { for(size_t j=0;j<len;++j) warm[n++]=entry_.text[consumed++]; }
    }
    warm[n]=0;
    char warmPlain[512]; WikiText::stripInlineStyles(warm,warmPlain,sizeof(warmPlain));
    uint8_t startStyle=cursor.style;
    if (definitionTerm) startStyle|=WikiText::Bold;
    const uint8_t styleMask=heading ? 0x0a : WikiText::inlineStyleMask(warm,n,startStyle);
    renderer.ensureSdCardFontReady(font,warmPlain,styleMask);
'''
new_warm = '''    uint8_t startStyle=cursor.style;
    if (definitionTerm) startStyle|=WikiText::Bold;
    // The smooth-text grayscale pass immediately follows the base pass over the
    // same glyphs. Avoid repeating UTF-8 scanning and SD font prewarming.
    if (!grayscalePass) {
      char warm[512];size_t consumed=cursor.offset,n=0;
      while (consumed<block.end && n+4<sizeof(warm)) {
        const size_t len=WikiText::utf8Length(entry_.text,consumed,block.end);
        if (!len) { warm[n++]='?';++consumed; }
        else { for(size_t j=0;j<len;++j) warm[n++]=entry_.text[consumed++]; }
      }
      warm[n]=0;
      char warmPlain[512]; WikiText::stripInlineStyles(warm,warmPlain,sizeof(warmPlain));
      const uint8_t styleMask=heading ? 0x0a : WikiText::inlineStyleMask(warm,n,startStyle);
      renderer.ensureSdCardFontReady(font,warmPlain,styleMask);
    }
'''
w = replace_once(w, old_warm, new_warm, 'smooth text duplicate prewarm')
w = replace_once(
    w,
    '''    if (headingComplete && !grayscalePass) {
      const int ruleY=std::min(bottom-1,y+lineHeight-2);
      renderer.drawLine(contentX,ruleY,w-side,ruleY,block.level<=2 ? 2 : 1,true);
    }
    cursor.offset=uint32_t(next);cursor.style=lineEndStyle;y+=lineHeight;
    if (headingComplete) y+=8;
''',
    '''    if (headingComplete && !grayscalePass && block.level<=2) {
      const int ruleY=std::min(bottom-1,y+lineHeight-2);
      renderer.drawLine(contentX,ruleY,w-side,ruleY,2,true);
    }
    cursor.offset=uint32_t(next);cursor.style=lineEndStyle;y+=lineHeight;
    if (headingComplete) y+=block.level<=2 ? 8 : std::max(6,lineHeight/3);
''',
    'heading rule hierarchy',
)
wiki.write_text(w)

ini = Path('platformio.local.ini')
i = ini.read_text()
if '1.6.0-wiki-4.5.0' not in i:
    raise SystemExit('4.5.1: expected 4.5.0 version not found')
i = i.replace('1.6.0-wiki-4.5.0', '1.6.0-wiki-4.5.1')
i = replace_once(i, '  -DLOG_LEVEL=1\n', '  -DLOG_LEVEL=0\n', 'error-only logging')
ini.write_text(i)

print('Wiki 4.5.1 typography, SD Finished Books, and reader/power optimizations applied.')
