#!/usr/bin/env python3
from pathlib import Path
R=Path('.')
def edit(p,a,b):
 f=R/p;s=f.read_text();assert s.count(a)==1,(p,a[:100],s.count(a));f.write_text(s.replace(a,b,1))
(R/'src/activities/reader/ReaderNavigationQueue.h').write_text('''#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
// Single input-task owner. Never overwrite or algebraically cancel an accepted
// command. Explicit navigation away from the reading screen cancels its queue.
class ReaderNavigationQueue {
 public:
  enum class Action:uint8_t {Previous,Next,SkipPrevious,SkipNext,RotatePrevious,RotateNext};
  static constexpr size_t CAPACITY=32;
  bool push(Action a){if(size_==CAPACITY)return false;items_[(head_+size_)%CAPACITY]=a;++size_;return true;}
  Action front()const{return items_[head_];}
  void pop(){if(size_){head_=(head_+1)%CAPACITY;--size_;}}
  bool empty()const{return !size_;}
  size_t size()const{return size_;}
  void clear(){head_=size_=0;}
 private:
  std::array<Action,CAPACITY> items_{};size_t head_=0,size_=0;
};
''')
edit('src/activities/reader/ReaderActivity.h','  bool finishedRecorded = false;','''  bool finishedRecorded = false;
  uint8_t finishedSaveAttempts = 0;
  unsigned long lastFinishedSaveAttempt = 0;
  std::atomic<bool> finishedSaveErrorPending{false};
  bool tryRecordFinished(bool explicitRetry = false);
  void showFinishedSaveError();''')
edit('src/activities/reader/ReaderActivity.cpp','#include "ReaderUtils.h"','#include "ReaderUtils.h"\n#include "I18n.h"\n#include "components/UITheme.h"')
edit('src/activities/reader/ReaderActivity.cpp','''void ReaderActivity::loop() {
  if (isAtEndOfBook() && !finishedRecorded) {
    RECENT_BOOKS.markFinished(bookPath, getBookTitle(), getBookAuthor(), getBookThumbBmpPath());
    finishedRecorded = true;
  }''','''bool ReaderActivity::tryRecordFinished(const bool explicitRetry) {
  if(finishedRecorded)return true;
  const unsigned long now=millis();
  if(!explicitRetry && (finishedSaveAttempts>=3 ||
      (finishedSaveAttempts && now-lastFinishedSaveAttempt<2000UL)))return false;
  if(explicitRetry)finishedSaveAttempts=0;
  ++finishedSaveAttempts;lastFinishedSaveAttempt=now;
  finishedRecorded=RECENT_BOOKS.markFinished(bookPath,getBookTitle(),getBookAuthor(),getBookThumbBmpPath());
  if(!finishedRecorded){finishedSaveErrorPending.store(true,std::memory_order_release);requestUpdate();}
  return finishedRecorded;
}
void ReaderActivity::showFinishedSaveError() {
  if(finishedSaveErrorPending.exchange(false,std::memory_order_acq_rel))
    GUI.drawPopup(renderer,tr(STR_SAVE_PROGRESS_FAILED));
}
void ReaderActivity::loop() {
  if(isAtEndOfBook()&&!finishedRecorded)tryRecordFinished();''')
edit('src/activities/reader/ReaderActivity.cpp','    onEndOfBookRendered();\n    return;','    onEndOfBookRendered();\n    showFinishedSaveError();\n    return;')
edit('src/activities/reader/ReaderActivity.cpp','  renderBook();\n}','  renderBook();\n  showFinishedSaveError();\n}')
p=R/'src/activities/reader/EpubReaderActivity.h';s=p.read_text().replace('#include "ReaderActivity.h"','#include "ReaderActivity.h"\n#include "ReaderNavigationQueue.h"')
s=s.replace('  int8_t pendingManualTurn = 0;','''  ReaderNavigationQueue pendingManualTurns;
  std::atomic<bool> navigationQueueFull{false};
  std::atomic<bool> completionEligible{false};
  std::unique_ptr<Page> preparedNextPage;
  int preparedSpine=-1,preparedPageNumber=-1,preparedFontId=-1;
  size_t preparedPrewarmElement=0;
  unsigned long lastIdleWorkMs=0;
  void invalidatePreparedPage();
  void resetSection();
  void performIdlePreparation();
  void updateCompletionAndRecents();
  float displayedBookProgress() const;
  void noteCompletionCandidate();
  int housekeepingSpine=-2,housekeepingPage=-2,housekeepingCount=-2;
  uint8_t housekeepingFlags=0xff;
  mutable int titleCacheSpine=-2;
  mutable std::string titleCache;''')
s=s.replace('  unsigned long lastRenderCompleteMs = 0;','  std::atomic<unsigned long> lastRenderCompleteMs{0};')
s=s.replace('BACKGROUND_BUILD_PAGES_PER_TICK = 2','BACKGROUND_BUILD_PAGES_PER_TICK = 1')
p.write_text(s)
p=R/'src/activities/reader/EpubReaderActivity.cpp';s=p.read_text()
s=s.replace('pendingManualTurn = 0;','pendingManualTurns.clear();').replace('section.reset();','resetSection();')
s=s.replace('void EpubReaderActivity::onExit() {','''void EpubReaderActivity::onExit() {
  // ActivityManager has already stopped rendering here. Do not recursively lock it.
  if(epub && (completionEligible.load(std::memory_order_acquire)||isAtEndOfBook()))tryRecordFinished();
  invalidatePreparedPage();''')
a=s.index('  constexpr unsigned long IDLE_PREWARM_DEBOUNCE_MS = 400;',s.index('void EpubReaderActivity::loop()'));b=s.index('  const auto touch = ReaderUtils::detectTouchPageTurn',a)
s=s[:a]+'''  const bool atEndOfBook=isAtEndOfBook();
  pendingReadFolderMove=atEndOfBook&&SETTINGS.moveFinishedToReadFolder&&!isInReadFolder(epub->getPath());
  clearEndOfBookOptionsIfNeeded();

'''+s[b:]
# Timer actions must not return before sampling manual navigation.
a=s.index('    if (!section) {',s.index('  if (automaticPageTurnActive) {',s.index('void EpubReaderActivity::loop()')));b=s.index('\n  // While the end-of-book suggestion',a)
s=s[:a]+'''    if(RenderLock::peek())lastPageTurnTime=millis();
  }
'''+s[b:]
s=s.replace('''    } else {
      openReaderMenu();
    }
  }

  if (footnoteDepth > 0''','''    } else {
      pendingManualTurns.clear();
      openReaderMenu();
    }
    return;
  }

  if (footnoteDepth > 0''',1)
a=s.index('  constexpr unsigned long kMinManualTurnGapMs = 200;',s.index('void EpubReaderActivity::loop()'));b=s.index('\nvoid EpubReaderActivity::jumpToPercent',a)
s=s[:a]+'''  // Capture the current debounced event BEFORE draining older commands.
  auto [prevTriggered,nextTriggered,fromTilt]=ReaderUtils::detectPageTurn(mappedInput);
  prevTriggered=prevTriggered||touch.prev;nextTriggered=nextTriggered||touch.next;
  const bool screenshotChord=mappedInput.wasReleased(MappedInputManager::Button::Power)&&
                              mappedInput.wasReleased(MappedInputManager::Button::Down);
  if((prevTriggered||nextTriggered)&&!screenshotChord) {
    using Action=ReaderNavigationQueue::Action;
    const unsigned long heldMs=(touch.prev||touch.next)?touch.heldMs:mappedInput.getHeldTime();
    const bool longPress=!fromTilt&&heldMs>=ReaderUtils::SKIP_HOLD_MS;
    const auto capture=[&](bool forward) {
      Action a=forward?Action::Next:Action::Previous;
      if(longPress&&SETTINGS.longPressButtonBehavior==SETTINGS.CHAPTER_SKIP)
        a=forward?Action::SkipNext:Action::SkipPrevious;
      else if(longPress&&SETTINGS.longPressButtonBehavior==SETTINGS.ORIENTATION_CHANGE)
        a=forward?Action::RotateNext:Action::RotatePrevious;
      if(!pendingManualTurns.push(a)) {
        navigationQueueFull.store(true,std::memory_order_release);
        LOG_ERR("ERS","Navigation queue full: newest event rejected");requestUpdate();
      }
    };
    if(prevTriggered)capture(false);
    if(nextTriggered)capture(true);
  }
  constexpr unsigned long kMinManualTurnGapMs=200;
  if(!pendingManualTurns.empty()) {
    if(RenderLock::peek()||millis()-lastPageTurnTime<kMinManualTurnGapMs)return;
    using Action=ReaderNavigationQueue::Action;
    const Action a=pendingManualTurns.front();
    const bool forward=a==Action::Next||a==Action::SkipNext||a==Action::RotateNext;
    if(isAtEndOfBook()) {
      pendingManualTurns.clear();tryRecordFinished();
      handleEndOfBookPageTurn(!forward,forward);return;
    }
    const bool rotate=a==Action::RotateNext||a==Action::RotatePrevious;
    if(!section&&!rotate){requestUpdate();return;} // preserve across chapter loading
    pendingManualTurns.pop();
    if(rotate) {
      const uint8_t orientation=forward?(SETTINGS.orientation-1+SETTINGS.ORIENTATION_COUNT)%SETTINGS.ORIENTATION_COUNT:
                                           (SETTINGS.orientation+1)%SETTINGS.ORIENTATION_COUNT;
      applyOrientation(orientation);
    } else if(a==Action::SkipNext||a==Action::SkipPrevious)skipPages(forward?1:-1);
    else pageTurn(forward);
    lastPageTurnTime=millis();requestUpdate();return;
  }
  if(RenderLock::peek()||mappedInput.wasAnyPressed()||mappedInput.wasAnyReleased())return;
  if(automaticPageTurnActive&&section&&millis()-lastPageTurnTime>=pageTurnDuration&&
     (!lastRenderCompleteMs||millis()-lastRenderCompleteMs>=200UL)) {
    pageTurn(true);requestUpdate();return;
  }
  updateCompletionAndRecents();
  performIdlePreparation();
}
float EpubReaderActivity::displayedBookProgress() const {
  if(!epub)return 0.0f;if(isAtEndOfBook())return 100.0f;
  const int count=section?section->estimatedTotalPages():0;
  const float chapter=count>0?float(section->currentPage+1)/float(count):0.0f;
  return std::clamp(epub->calculateProgress(currentSpineIndex,chapter)*100.0f,0.0f,100.0f);
}
void EpubReaderActivity::noteCompletionCandidate() {
  if(!epub)return;
  const bool stable=section&&!section->isBuilding()&&!section->isPartial()&&section->pageCount>0;
  const bool final=stable&&currentSpineIndex==epub->getSpineItemsCount()-1&&section->currentPage>=int(section->pageCount)-1;
  if(isAtEndOfBook()||final||(stable&&displayedBookProgress()>=99.5f))
    completionEligible.store(true,std::memory_order_release);
}
void EpubReaderActivity::updateCompletionAndRecents() {
  // Only called after sampled input has been retained and dispatched.
  RenderLock lock;
  if(!epub)return;
  if((completionEligible.load(std::memory_order_acquire)||isAtEndOfBook())&&!finishedRecorded)tryRecordFinished();
  const bool end=isAtEndOfBook();const int page=section?section->currentPage:-1;
  const int count=section?section->estimatedTotalPages():0;
  const uint8_t flags=uint8_t(end)|(uint8_t(SETTINGS.removeReadBooksFromRecents)<<1)|
      (uint8_t(SETTINGS.moveFinishedToReadFolder)<<2);
  if(housekeepingSpine==currentSpineIndex&&housekeepingPage==page&&housekeepingCount==count&&housekeepingFlags==flags)return;
  housekeepingSpine=currentSpineIndex;housekeepingPage=page;housekeepingCount=count;housekeepingFlags=flags;
  if(SETTINGS.removeReadBooksFromRecents) {
    if(end&&!recentsEntryRemoved)recentsEntryRemoved=RECENT_BOOKS.removeByPath(epub->getPath());
    else if(!end&&recentsEntryRemoved) {
      RECENT_BOOKS.addBook(epub->getPath(),epub->getTitle(),epub->getAuthor(),epub->getThumbBmpPath());recentsEntryRemoved=false;
    }
  }
}
void EpubReaderActivity::invalidatePreparedPage() {
  preparedNextPage.reset();preparedSpine=preparedPageNumber=preparedFontId=-1;preparedPrewarmElement=0;
}
void EpubReaderActivity::resetSection() {
  invalidatePreparedPage();idlePrewarmSpine=idlePrewarmPage=-1;housekeepingSpine=-2;section.reset();
}
void EpubReaderActivity::performIdlePreparation() {
  if(RenderLock::peek()||!pendingManualTurns.empty()||overlay!=Overlay::None)return;
  for(int b=0;b<=int(MappedInputManager::Button::Power);++b)
    if(mappedInput.isPressed(static_cast<MappedInputManager::Button>(b)))return;
  const unsigned long now=millis();RenderLock lock;if(!section)return;
  if(ESP.getFreeHeap()<48*1024||ESP.getMaxAllocHeap()<24*1024)invalidatePreparedPage();
  if(!lastRenderCompleteMs||now-lastRenderCompleteMs<400||now-lastIdleWorkMs<10)return;
  lastIdleWorkMs=now;
  // One parser page or four text elements per tick. An individual synchronous
  // SD/parser operation can exceed the cooperative scan budget; not hard real time.
  if(!section->isBuilding()&&section->isPartial()&&buildViewportWidth>0&&!partialRebuildStartFailed&&
     section->currentPage+PARTIAL_REBUILD_START_MARGIN>=int(section->pageCount)) {
    invalidatePreparedPage();const ReaderRenderSpec spec=SETTINGS.readerRenderSpec(buildViewportWidth,buildViewportHeight);
    if(!section->startBuild(spec))partialRebuildStartFailed=true;
    return;
  }
  if(section->isBuilding()) {
    if((section->isPartial()||int(section->pageCount)<section->currentPage+BUILD_WINDOW_AHEAD)&&buildTickHeapGate()) {
      invalidatePreparedPage();
      if(!section->buildSomeMore(BACKGROUND_BUILD_PAGES_PER_TICK)){resetSection();requestUpdate();}
      else if(section->isBuildComplete()&&applyDeferredReposition())requestUpdate();
    }
    return;
  }
  const int next=section->currentPage+1;if(next>=int(section->pageCount)||!renderer.hasFrameBuffer())return;
  if(preparedNextPage&&(preparedSpine!=currentSpineIndex||preparedPageNumber!=next||preparedFontId!=SETTINGS.getReaderFontId()))
    invalidatePreparedPage();
  if(!preparedNextPage) {
    if(idlePrewarmSpine==currentSpineIndex&&idlePrewarmPage==section->currentPage)return;
    if(ESP.getFreeHeap()<72*1024||ESP.getMaxAllocHeap()<32*1024)return;
    const size_t before=ESP.getFreeHeap();auto page=section->loadPage(next);
    idlePrewarmSpine=currentSpineIndex;idlePrewarmPage=section->currentPage;
    if(!page||ESP.getFreeHeap()<48*1024||ESP.getMaxAllocHeap()<24*1024||
       before-std::min<size_t>(before,ESP.getFreeHeap())>20*1024)return;
    preparedNextPage=std::move(page);preparedSpine=currentSpineIndex;preparedPageNumber=next;
    preparedFontId=SETTINGS.getReaderFontId();preparedPrewarmElement=0;return;
  }
  auto* fcm=renderer.getFontCacheManager();if(!fcm||preparedPrewarmElement>=preparedNextPage->elements.size())return;
  const unsigned long began=millis();auto scope=fcm->createPrewarmScope();
  for(unsigned n=0;n<4&&preparedPrewarmElement<preparedNextPage->elements.size();++n) {
    const auto& element=preparedNextPage->elements[preparedPrewarmElement++];
    if(element->getTag()==TAG_PageLine)element->render(renderer,preparedFontId,0,0);
    if(millis()-began>=3)break;
  }
  scope.endScanAndPrewarm();
}
'''+s[b:]
a=s.index('bool EpubReaderActivity::skipLoopDelay() {');b=s.index('\n}',a)+2
s=s[:a]+'''bool EpubReaderActivity::skipLoopDelay() {
  // Do not busy-spin while the idle budget/debounce defers optional pagination.
  return false;
}'''+s[b:]
s=s.replace('''        RECENT_BOOKS.markFinished(epub->getPath(), epub->getTitle(), epub->getAuthor(), epub->getThumbBmpPath());
        finishedRecorded = true;''','''        tryRecordFinished(true);''')
needle='''  {
    auto p = section->loadPage(section->currentPage);
    if (!p) {''';assert s.count(needle)==1
s=s.replace(needle,'''  {
    std::unique_ptr<Page> p;
    if(preparedNextPage&&preparedSpine==currentSpineIndex&&preparedPageNumber==section->currentPage&&
       preparedFontId==SETTINGS.getReaderFontId()&&!section->isBuilding()) {
      p=std::move(preparedNextPage);preparedPageNumber=-1;preparedPrewarmElement=0;
    } else {
      invalidatePreparedPage();p=section->loadPage(section->currentPage);
    }
    if (!p) {''',1)
s=s.replace('    lastRenderCompleteMs = millis();','    lastRenderCompleteMs = millis();\n    noteCompletionCandidate();',1)
s=s.replace('void EpubReaderActivity::onEndOfBookRendered() {','void EpubReaderActivity::onEndOfBookRendered() {\n  noteCompletionCandidate();')
s=s.replace('void EpubReaderActivity::renderBook() {','''void EpubReaderActivity::renderBook() {
  if(navigationQueueFull.exchange(false,std::memory_order_acq_rel)) {
    GUI.drawPopup(renderer,"Navigation queue full");return;
  }''')
a=s.index('  const float sectionChapterProg =',s.index('void EpubReaderActivity::renderStatusBar'));b=s.index('\n  std::string title;',a)
s=s[:a]+'  const float bookProgress=displayedBookProgress();\n'+s[b:]
a=s.index('    title = tr(STR_UNNAMED);',s.index('void EpubReaderActivity::renderStatusBar'));b=s.index('  } else if (sb.titleMode ==',a)
s=s[:a]+'    title=currentChapterTitle();\n'+s[b:]
a=s.index('std::string EpubReaderActivity::currentChapterTitle() const {');b=s.index('\nstd::string EpubReaderActivity::textRowName',a)
s=s[:a]+'''std::string EpubReaderActivity::currentChapterTitle() const {
  if(!epub)return "";
  if(titleCacheSpine!=currentSpineIndex) {
    titleCacheSpine=currentSpineIndex;const int toc=epub->getTocIndexForSpineIndex(currentSpineIndex);
    titleCache=toc>=0?epub->getTocItem(toc).title:"";
  }
  return titleCache.empty()?tr(STR_UNNAMED):titleCache;
}
'''+s[b:]
p.write_text(s)
p=R/'platformio.local.ini';s=p.read_text();assert s.count('1.6.0-wiki-4.6.2')==2;p.write_text(s.replace('1.6.0-wiki-4.6.2','1.6.0-wiki-4.6.3'))
print('4.6.3 reader: ordered input-first queue, bounded preparation, one reusable next page, shared completion semantics')
