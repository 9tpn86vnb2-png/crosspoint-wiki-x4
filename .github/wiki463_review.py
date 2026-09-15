#!/usr/bin/env python3
from pathlib import Path
R=Path('.')
def edit(p,a,b):
 f=R/p;s=f.read_text();assert s.count(a)==1,(p,a[:100],s.count(a));f.write_text(s.replace(a,b,1))
edit('src/activities/RenderLock.h','  RenderLock();','''  RenderLock();
  enum class Mode { Try };
  explicit RenderLock(Mode);
  bool ownsLock() const { return isLocked; }''')
edit('src/activities/ActivityManager.cpp','RenderLock::RenderLock() {','''RenderLock::RenderLock(Mode) {
  isLocked=xSemaphoreTake(activityManager.renderingMutex,0)==pdTRUE;
}
RenderLock::RenderLock() {''')
p=R/'src/activities/reader/EpubReaderActivity.h';s=p.read_text();s=s.replace('  void noteCompletionCandidate();','''  void noteCompletionCandidate();
  bool pageTurnLocked(bool forward);
  bool skipPagesLocked(int amount);
  void applyOrientationLocked(uint8_t orientation);''');p.write_text(s)
p=R/'src/activities/reader/EpubReaderActivity.cpp';s=p.read_text()
# UI menu and toolbar share the same inclusive percentage used by completion.
a=s.index('  float bookProgress = 0.0f;',s.index('void EpubReaderActivity::openReaderMenu'));b=s.index('  const int bookProgressPercent',a)
s=s[:a]+'  const float bookProgress=displayedBookProgress();\n'+s[b:]
# The stored title is shared by the input and render tasks. Protect its lookup
# and copy using the existing recursive SD transaction lock, not a second owner.
s=s.replace('std::string EpubReaderActivity::currentChapterTitle() const {\n  if(!epub)', 'std::string EpubReaderActivity::currentChapterTitle() const {\n  HalStorage::Transaction transaction;\n  if(!epub)',1)
s=s.replace('''  RenderLock lock;
  if(!epub)return;
  if((completionEligible''','''  RenderLock lock(RenderLock::Mode::Try);
  if(!lock.ownsLock()||!epub)return;
  noteCompletionCandidate();
  if((completionEligible''',1)
s=s.replace('const unsigned long now=millis();RenderLock lock;if(!section)return;', 'const unsigned long now=millis();RenderLock lock(RenderLock::Mode::Try);if(!lock.ownsLock()||!section)return;',1)
# Turn helpers are also used by menus. Keep their normal locking wrapper, while
# queue dispatch uses a nonblocking lock and the same mutation implementation.
a=s.index('bool EpubReaderActivity::pageTurn(bool isForwardTurn) {');b=s.index('\nbool EpubReaderActivity::skipPages',a)
body=s[a:b]
body=body.replace('bool EpubReaderActivity::pageTurn(bool isForwardTurn) {','''bool EpubReaderActivity::pageTurn(bool isForwardTurn) {
  RenderLock lock;return pageTurnLocked(isForwardTurn);
}
bool EpubReaderActivity::pageTurnLocked(bool isForwardTurn) {''',1)
body=body.replace('''  {
    RenderLock lock;
    clearDeferredReposition();
  }''','  clearDeferredReposition();',1)
body=body.replace('      RenderLock lock;\n','')
s=s[:a]+body+s[b:]
a=s.index('bool EpubReaderActivity::skipPages(int amount) {');b=s.index('\nbool EpubReaderActivity::isAtEndOfBook',a)
body=s[a:b].replace('bool EpubReaderActivity::skipPages(int amount) {','''bool EpubReaderActivity::skipPages(int amount) {
  RenderLock lock;return skipPagesLocked(amount);
}
bool EpubReaderActivity::skipPagesLocked(int amount) {''',1)
body=body.replace('    RenderLock lock;\n','').replace('      RenderLock lock;\n','')
s=s[:a]+body+s[b:]
a=s.index('void EpubReaderActivity::applyOrientation(const uint8_t orientation) {');b=s.index('\nvoid EpubReaderActivity::toggleAutoPageTurn',a)
body=s[a:b].replace('void EpubReaderActivity::applyOrientation(const uint8_t orientation) {','''void EpubReaderActivity::applyOrientation(const uint8_t orientation) {
  RenderLock lock;applyOrientationLocked(orientation);
}
void EpubReaderActivity::applyOrientationLocked(const uint8_t orientation) {''',1).replace('  RenderLock lock(*this);\n','')
s=s[:a]+body+s[b:]
a=s.index('  constexpr unsigned long kMinManualTurnGapMs=200;',s.index('void EpubReaderActivity::loop()'));b=s.index('  updateCompletionAndRecents();',a)
body=s[a:b]
body=body.replace('''    if(RenderLock::peek()||millis()-lastPageTurnTime<kMinManualTurnGapMs)return;
    using Action''','''    if(millis()-lastPageTurnTime<kMinManualTurnGapMs)return;
    RenderLock turnLock(RenderLock::Mode::Try);if(!turnLock.ownsLock())return;
    using Action''',1)
body=body.replace('applyOrientation(orientation);','applyOrientationLocked(orientation);')
body=body.replace('skipPages(forward?1:-1);','skipPagesLocked(forward?1:-1);').replace('else pageTurn(forward);','else pageTurnLocked(forward);')
body=body.replace('    pageTurn(true);requestUpdate();return;','    RenderLock autoLock(RenderLock::Mode::Try);if(!autoLock.ownsLock())return;\n    pageTurnLocked(true);requestUpdate();return;')
s=s[:a]+body+s[b:]
p.write_text(s)
# Ensure the expanded reviewed-source set is hashed and packaged, too.
p=R/'.github/wiki463_finish.py';s=p.read_text();s=s.replace("FILES=['platformio.local.ini'", "FILES=['src/activities/RenderLock.h','src/activities/ActivityManager.cpp','platformio.local.ini'",1);p.write_text(s)
print('4.6.3 review: nonblocking optional work and queue dispatch, protected section mutation, shared UI percentage and title cache')
