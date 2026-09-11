#!/usr/bin/env python3
"""Apply guarded integration to the exact CrossPoint 1.6.0 source files.
Run once on a clean checkout, before PlatformIO. Never patches unknown sources.
"""
import hashlib
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '54337e6d73fc628f4ba523ddc89a743ca8c6e4c5'
EXPECTED = {
 'src/activities/ActivityManager.h': 'acda6444fc9078a353eaa1eeaef2cf41864818cc',
 'src/activities/home/HomeActivity.h': '4ea540e57f27abe992dc6a0449d24345c97e3c2a',
 'src/activities/home/HomeActivity.cpp': '228b2e6055373e46856f71a33af0343fa4323099',
}

def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError('Integration anchor is absent or ambiguous: ' + repr(old[:100]))
    return text.replace(old, new, 1)

def main():
    subprocess.run(['git', 'merge-base', '--is-ancestor', BASE, 'HEAD'], cwd=ROOT, check=True)
    source = {}
    for name, expected in EXPECTED.items():
        data = (ROOT / name).read_bytes()
        digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if digest != expected:
            raise RuntimeError(f'{name}: not the reviewed 1.6.0 source; refusing to patch ({digest})')
        source[name] = data.decode()
    name = 'src/activities/ActivityManager.h'
    source[name] = replace(source[name], 'FILE_TRANSFER, SETTINGS_MENU };', 'FILE_TRANSFER, SETTINGS_MENU, WIKI };')
    name = 'src/activities/home/HomeActivity.h'
    text = source[name]
    text = replace(text, '    if (item == HomeMenuItem::OPDS_BROWSER)',
        '    if (item == HomeMenuItem::WIKI) return i;\n    ++i;\n    if (item == HomeMenuItem::OPDS_BROWSER)')
    text = replace(text, '    if (hasOpdsUrl && idx == i++)',
        '    if (idx == i++) return HomeMenuItem::WIKI;\n    if (hasOpdsUrl && idx == i++)')
    text = replace(text, '  void onOpdsBrowserOpen();', '  void onOpdsBrowserOpen();\n  void onWikiOpen();')
    source[name] = text
    name = 'src/activities/home/HomeActivity.cpp'
    text = source[name]
    text = replace(text, '#include "HomeActivity.h"', '#include "HomeActivity.h"\n#include <new>\n#include "activities/wiki/WikiActivity.h"')
    text = replace(text, 'int count = 4;  // File Browser, Recents, File transfer, Settings',
        'int count = 5;  // File Browser, Recents, Wiki, File transfer, Settings')
    text = replace(text, '      case HomeMenuItem::OPDS_BROWSER:',
        '      case HomeMenuItem::WIKI:\n        onWikiOpen();\n        break;\n      case HomeMenuItem::OPDS_BROWSER:')
    text = replace(text, 'tr(STR_MENU_RECENT_BOOKS), tr(STR_FILE_TRANSFER),',
        'tr(STR_MENU_RECENT_BOOKS), "Wiki", tr(STR_FILE_TRANSFER),')
    text = replace(text, '{Folder, Recent, Transfer, Settings}', '{Folder, Recent, Book, Transfer, Settings}')
    text = replace(text, 'menuItems.begin() + 2, tr(STR_OPDS_BROWSER)', 'menuItems.begin() + 3, tr(STR_OPDS_BROWSER)')
    text = replace(text, 'menuIcons.begin() + 2, Library', 'menuIcons.begin() + 3, Library')
    # Keep every menu item reachable when an extra row exceeds a theme's space.
    text = replace(text, '  int menuRow = -1;', '''  int menuRow = -1;
  const int menuBottom = renderer.getScreenHeight() - metrics.buttonHintsHeight - metrics.verticalSpacing;
  const int visibleRows = std::max(1, std::min(renderedMenuCount,
      (menuBottom - menuTop + metrics.menuSpacing) / std::max(1, GUI.getMenuRowHeight(renderer) + metrics.menuSpacing)));
  const int windowStart = std::max(0, renderedMenuSelection - visibleRows + 1);''')
    text = replace(text, 'menuRowHeight + metrics.menuSpacing, renderedMenuCount,',
        'menuRowHeight + metrics.menuSpacing, visibleRows,')
    text = replace(text, '  if (menuTouch != MappedInputManager::RowTouch::None) {',
        '  if (menuTouch != MappedInputManager::RowTouch::None) {\n    menuRow += windowStart;')
    text = replace(text, '  GUI.drawButtonMenu(\n', '''  const int menuTop = metrics.homeTopPadding + metrics.homeCoverTileHeight + metrics.homeMenuTopOffset;
  const int menuBottom = pageHeight - metrics.buttonHintsHeight - metrics.verticalSpacing;
  const int selectedMenu = metrics.homeContinueReadingInMenu ? selectorIndex : selectorIndex - static_cast<int>(recentBooks.size());
  const int visibleRows = std::max(1, std::min(static_cast<int>(menuItems.size()),
      (menuBottom - menuTop + metrics.menuSpacing) / std::max(1, GUI.getMenuRowHeight(renderer) + metrics.menuSpacing)));
  const int windowStart = std::max(0, selectedMenu - visibleRows + 1);
  GUI.drawButtonMenu(
''')
    text = replace(text, '''      static_cast<int>(menuItems.size()),
      metrics.homeContinueReadingInMenu ? selectorIndex : selectorIndex - recentBooks.size(),
      [&menuItems](int index) { return std::string(menuItems[index]); },
      [&menuIcons](int index) { return menuIcons[index]; });''', '''      visibleRows,
      selectedMenu - windowStart,
      [&menuItems, windowStart](int index) { return std::string(menuItems[windowStart + index]); },
      [&menuIcons, windowStart](int index) { return menuIcons[windowStart + index]; });''')
    text += '''

void HomeActivity::onWikiOpen() {
  auto wiki = std::unique_ptr<WikiActivity>(new (std::nothrow) WikiActivity(renderer, mappedInput));
  if (wiki) activityManager.replaceActivity(std::move(wiki));
  else LOG_ERR("WIKI", "Not enough memory to open Wiki");
}
'''
    source[name] = text
    # All assertions above finish before any original file is modified.
    for name, text in source.items():
        (ROOT / name).write_text(text)
    print('Integrated Wiki into reviewed CrossPoint 1.6.0 sources.')

if __name__ == '__main__':
    main()
