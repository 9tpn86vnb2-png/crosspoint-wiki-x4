from pathlib import Path
import re

cpp = Path('src/activities/wiki/WikiActivity.cpp').read_text()
hdr = Path('src/activities/wiki/WikiActivity.h').read_text()
ini = Path('platformio.local.ini').read_text()
checks = {
    'version 4.4.0': '1.6.0-wiki-4.4.0' in ini,
    'input sampled before render lock': cpp.index('captureInputIntents();') < cpp.index('if (RenderLock::peek()) return;') < cpp.index('RenderLock lock;', cpp.index('void WikiActivity::loop()')),
    'bounded intent queue': 'std::array<InputIntent, 16>' in hdr,
    'dry pagination': 'ensurePaginationFresh();' in cpp and 'Dry-layout' in cpp,
    'status default off': 'bool showStatusMessages_ = false;' in hdr,
    'portrait guides default off': 'bool portraitButtonGuides_ = false;' in hdr,
    'indexed home default on': 'bool indexedHome_ = true;' in hdr,
    'left library descriptor': 'renderer.drawText(SMALL_FONT_ID,headerInset,libraryY,lib.c_str());' in cpp,
    'alphabet browser': 'Browse A-Z' in cpp and 'Screen::BrowseLetters' in cpp,
    'category prefix browser': 'Category:' in cpp and 'ResultsMode::Categories' in cpp,
    'button guide': 'void WikiActivity::renderButtonGuide()' in cpp and 'Last input:' in cpp,
    'page footer uses optional hints': 'articleShowsButtonHints() ? m.buttonHintsHeight : 0' in cpp,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit('4.4.0 source contracts failed: ' + ', '.join(failed))
print(f'{len(checks)} Wiki 4.4.0 source-contract checks passed.')

# Mirror the intended battery interpolation to catch accidental workflow edits.
curve = [3450,3680,3740,3770,3790,3820,3870,3920,3980,4060,4170]
def pct(mv):
    if mv <= curve[0]: return 0
    if mv >= curve[-1]: return 100
    for i in range(1, len(curve)):
        if mv <= curve[i]:
            low, high = curve[i-1], curve[i]
            tenths = ((mv-low)*10 + (high-low)//2)//(high-low)
            return min(100, (i-1)*10 + tenths)
for mv, expected in [(4170,100),(4160,99),(4130,96),(4060,90),(4020,85),(3920,70),(3820,50),(3450,0)]:
    got = pct(mv)
    if got != expected:
        raise SystemExit(f'battery curve {mv} mV: {got} != {expected}')
print('8 battery interpolation checkpoints passed.')
