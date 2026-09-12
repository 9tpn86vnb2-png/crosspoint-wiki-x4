#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
wiki = (ROOT/'src/activities/wiki/WikiActivity.cpp').read_text()
wh = (ROOT/'src/activities/wiki/WikiActivity.h').read_text()
ts = (ROOT/'src/activities/settings/TextSettingsActivity.cpp').read_text()
th = (ROOT/'src/activities/settings/TextSettingsActivity.h').read_text()
pio = (ROOT/'platformio.local.ini').read_text()

checks = {
    'version descriptor': '1.6.0-wiki-4.3.1' in pio,
    'wiki profile capture': 'readerTextProfile_.fontFamily = SETTINGS.fontFamily' in wiki,
    'wiki profile restore': 'restoreReaderTextProfile();' in wiki and 'SETTINGS.fontFamily = readerTextProfile_.fontFamily' in wiki,
    'wiki profile independent persistence': 'preferences.putBool("wprofile", true);' in wiki and 'preferences.putString("wfontname", SETTINGS.sdFontFamilyName);' in wiki,
    'text settings wiki persistence': 'void TextSettingsActivity::persistSettings()' in ts and 'if (!wikiMode_)' in ts and 'SETTINGS.saveToFile();' in ts,
    'wiki text settings keys': all(k in ts for k in ['"wfont"','"wsize"','"wline"','"wpara"','"walign"','"wmargin"','"wfontname"']),
    'wiki style tab remains hidden': 'return wikiMode_ ? 3 : static_cast<int>(Tab::Count);' in th,
    'wiki family pre-snap': ts.count('if (wikiMode_) snapCurrentFontSize();') == 2,
    'font options no longer described shared': 'Text options applied (also used by books)' not in wiki,
    'wiki text status': 'Wiki text options applied' in wiki,
    'cycle font persists wiki': 'saveWikiTextProfile();\n  resetPages(); status_ = "Wiki text size changed";' in wiki,
    'thick internal-link underline': 'drawLine(x,underlineY,x+runWidth-1,underlineY,2,true)' in wiki,
    '4.3 link style preserved': 'WikiText::Bold | WikiText::Italic | WikiText::Link' in wiki,
    '4.3 spacing cap preserved': 'count>=4 && stretch>=0 && stretch*4<=naturalGaps*3' in wiki,
    'compact native header shell': 'GUI.drawHeader(renderer,Rect{0,m.topPadding,w,m.headerHeight},nullptr' in wiki,
    'library article banner format': 'const std::string prefix=lib+": ";' in wiki,
    'small library banner font': 'renderer.drawText(SMALL_FONT_ID,left,textY,prefix.c_str())' in wiki,
    'compact bold article banner font': 'renderer.drawText(UI_10_FONT_ID,left+prefixW,textY,article.c_str(),true,EpdFontFamily::BOLD)' in wiki,
    'old multiline article title removed': 'titleLines=renderer.wrappedText' not in wiki,
    'solid heading rule': 'headingComplete && !grayscalePass' in wiki and 'block.level<=2 ? 2 : 1,true' in wiki,
    'heading rule spacing': 'if (headingComplete) y+=8;' in wiki,
    'reader profile fields declared': all(k in wh for k in ['ReaderTextProfile','fontPointSize','lineSpacing','paragraphAlignment','screenMargin','extraParagraphSpacing','sdFontFamilyName']),
}
failed=[name for name,ok in checks.items() if not ok]
for name,ok in checks.items(): print(('PASS' if ok else 'FAIL')+': '+name)
if failed: raise SystemExit('Wiki 4.3.1 source contract failures: '+', '.join(failed))
print(f'Wiki 4.3.1 source contracts passed: {len(checks)} assertions.')
