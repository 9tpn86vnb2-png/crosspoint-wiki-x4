#!/usr/bin/env python3
"""Apply the icon additions after the existing guarded beta 1 menu integration."""
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
 'src/components/themes/BaseTheme.h': '6f88dc080779d92281967ec59adafd714111df9c6e4e59a25d501c3e03611afc',
 'src/components/themes/BaseTheme.cpp': '8f15835f79e053f80de412f6666bf334a1c0f39d7e32c2a492173c959f2f94f9',
 'src/components/themes/lyra/LyraTheme.cpp': '0dfd41b088b847bf459fa0ce7b4f3cbebe9473ba9803b0e05dbbc6b7fe506b22',
 'src/components/themes/roundedraff/RoundedRaffTheme.cpp': '388e9080899b9c88e296259e0ef5f5df1f464a9cdfb6a421129a4be6027f5076',
 'src/components/UiAppHelpers.h': '38cd72487e060ffe812f2d52923adbe20d44bd39343b24c843062aa1246c2ee9',
}
def replace(s,a,b,count=1):
    if s.count(a)!=count: raise ValueError('Unknown beta 2 integration anchor: '+repr(a[:100]))
    return s.replace(a,b)
def main():
    sources={}
    for name,digest in EXPECTED.items():
        data=(ROOT/name).read_bytes()
        if hashlib.sha256(data).hexdigest()!=digest: raise ValueError('Unreviewed source: '+name)
        sources[name]=data.decode()
    name='src/components/themes/BaseTheme.h'
    sources[name]=replace(sources[name],'  Bookmark,\n  Usb\n};','  Bookmark,\n  Usb,\n  WikiGlobeIcon\n};')
    name='src/components/UiAppHelpers.h'
    s=replace(sources[name],'#include "components/icons/listIcons.h"','#include "components/icons/listIcons.h"\n#include "components/icons/wikiGlobe.h"')
    s=replace(s,'      case UIIcon::Book:\n        return freeink::ui::bitmapFromIcon(icon_book_32);','      case UIIcon::WikiGlobeIcon:\n        return freeink::ui::bitmapFromIcon(WikiGlobe::icon32);\n      case UIIcon::Book:\n        return freeink::ui::bitmapFromIcon(icon_book_32);')
    s=replace(s,'    case UIIcon::Book:\n      return freeink::ui::bitmapFromIcon(icon_book_24);','    case UIIcon::WikiGlobeIcon:\n      return freeink::ui::bitmapFromIcon(WikiGlobe::icon24);\n    case UIIcon::Book:\n      return freeink::ui::bitmapFromIcon(icon_book_24);')
    sources[name]=s
    name='src/components/themes/lyra/LyraTheme.cpp'
    s=replace(sources[name],'#include "components/icons/book.h"','#include "components/icons/book.h"\n#include "components/icons/wikiGlobe.h"')
    s=replace(s,'    case UIIcon::Book:\n      return BookIcon;','    case UIIcon::WikiGlobeIcon:\n      return WikiGlobe::legacy32;\n    case UIIcon::Book:\n      return BookIcon;')
    sources[name]=s
    name='src/components/themes/BaseTheme.cpp'
    s=sources[name]
    s=replace(s,'    const int textX = rect.x + (rect.width - textWidth) / 2;','    const bool wikiIcon = rowIcon && rowIcon(i) == UIIcon::WikiGlobeIcon;\n    const int textX = rect.x + (rect.width - textWidth) / 2 + (wikiIcon ? 16 : 0);')
    s=replace(s,'    // Invert text when the tile is selected, to contrast with the filled background','    if (wikiIcon) WikiGlobe::draw(renderer,textX-32,tileY+(BaseMetrics::values.menuRowHeight-24)/2,24,!selected);\n    // Invert text when the tile is selected, to contrast with the filled background')
    sources[name]=s
    name='src/components/themes/roundedraff/RoundedRaffTheme.cpp'
    s=sources[name]
    s=replace(s,'#include "RoundedRaffTheme.h"','#include "RoundedRaffTheme.h"\n#include "components/icons/wikiGlobe.h"')
    s=replace(s,'  (void)rowIcon;','')
    s=replace(s,'    const int maxLabelWidth = std::max(0, menuMaxWidth - kRowPaddingX);','    const bool wikiIcon = rowIcon && rowIcon(i) == UIIcon::WikiGlobeIcon;\n    const int iconSpace = wikiIcon ? 32 : 0;\n    const int maxLabelWidth = std::max(0, menuMaxWidth - kRowPaddingX - iconSpace);')
    s=replace(s,'EpdFontFamily::BOLD) + kRowPaddingX);','EpdFontFamily::BOLD) + kRowPaddingX + iconSpace);')
    s=replace(s,'    const int textX = rowX + kInteractiveInsetX;','    const int textX = rowX + kInteractiveInsetX + iconSpace;\n    if (wikiIcon) WikiGlobe::draw(renderer,rowX+kInteractiveInsetX,rowY+(rowHeight-24)/2,24,!isSelected);')
    sources[name]=s
    home='src/activities/home/HomeActivity.cpp'
    sources[home]=replace((ROOT/home).read_text(),'{Folder, Recent, Book, Transfer, Settings}','{Folder, Recent, UIIcon::WikiGlobeIcon, Transfer, Settings}')
    for name,s in sources.items(): (ROOT/name).write_text(s)
    print('Integrated circle-grid Wiki icon for Classic, Lyra and Rounded Raff themes.')
if __name__=='__main__': main()
