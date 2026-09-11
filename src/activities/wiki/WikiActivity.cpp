#include <Arduino.h>
#include "WikiActivity.h"
#include <Preferences.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <new>
#include <utility>
#include <variant>
#include "activities/util/KeyboardEntryActivity.h"
#include "components/UITheme.h"
#include "components/icons/wikiGlobe.h"
#include "fontIds.h"

namespace {
constexpr int FONTS[] = {NOTOSANS_12_FONT_ID, NOTOSANS_14_FONT_ID, NOTOSANS_16_FONT_ID};
constexpr unsigned HOLD_MS = 600;
}
int WikiActivity::bodyFont() const {
  const int font = FONTS[fontStep_ % 3];
  return renderer.getLineHeight(font) > 0 ? font : UI_12_FONT_ID;
}
int WikiActivity::titleFont() const {
  return renderer.getLineHeight(NOTOSERIF_18_FONT_ID) > 0 ? NOTOSERIF_18_FONT_ID : NOTOSERIF_16_FONT_ID;
}
void WikiActivity::resetKeys() { backDown_ = backLong_ = confirmDown_ = confirmLong_ = false; }
void WikiActivity::resetPages() {
  page_ = 0; pages_[0] = {}; next_ = {}; hasNext_ = false;
}
void WikiActivity::accept(WikiArchive::Entry entry) {
  entry_ = std::move(entry);
  status_.clear(); resetPages();
  if (!entry_.found) { screen_ = Screen::Home; selection_ = 0; status_ = "Article unavailable or damaged"; return; }
  title_ = WikiText::displayTitle(entry_.key, entry_.text);
  if (cleanView_) WikiText::clean(entry_.text, entry_.key);
  document_.build(entry_.text, cleanView_);
  screen_ = Screen::Article;
}
void WikiActivity::onEnter() {
  Activity::onEnter();
  RenderLock lock;
  Preferences preferences;
  if (preferences.begin("wikibeta", true)) {
    fontStep_ = preferences.getUChar("font", 1) % 3;
    cleanView_ = preferences.getBool("clean", true);
    preferences.end();
  }
  bookmarks_.load();
  loadError_ = !archive_.open("/wikipedia.cdb");
  if (loadError_) loadError_ = !archive_.open("/Wikipedia/wikipedia.cdb");
  // Intentionally no archive_.first(): entering Wiki always starts at Search.
  screen_ = Screen::Home; selection_ = 0; entry_ = {}; resetPages(); resetKeys();
  status_ = bookmarks_.status();
  requestUpdate();
}
void WikiActivity::onExit() {
  Preferences preferences;
  if (preferences.begin("wikibeta", false)) {
    preferences.putUChar("font", fontStep_); preferences.putBool("clean", cleanView_); preferences.end();
  }
  archive_.close(); entry_ = {}; matches_.clear();
  Activity::onExit();
}
void WikiActivity::goWikiHome() {
  screen_ = Screen::Home; selection_ = 0; status_.clear(); matches_.clear(); resetKeys(); requestUpdate();
}
void WikiActivity::openTitle(std::string key) {
  entry_ = {}; matches_.clear();
  accept(archive_.search(key));
  requestUpdate();
}
void WikiActivity::changeEntry(int direction) {
  entry_ = {}; matches_.clear();
  if (direction > 0) accept(archive_.next());
  else if (direction < 0) accept(archive_.previous());
  else accept(archive_.random());
  requestUpdate();
}
void WikiActivity::openSearch() {
  auto keyboard = std::unique_ptr<KeyboardEntryActivity>(new (std::nothrow)
      KeyboardEntryActivity(renderer, mappedInput, "Search Wikipedia", query_, 256));
  if (!keyboard) { status_ = "Not enough memory for search"; requestUpdate(); return; }
  auto handler = [this](const ActivityResult& result) {
    RenderLock lock; resetKeys();
    if (!result.isCancelled) {
      const auto* typed = std::get_if<KeyboardResult>(&result.data);
      if (typed) {
        query_ = typed->text.substr(0, 256);
        const auto first = query_.find_first_not_of(" \t\r\n");
        if (first == std::string::npos) { goWikiHome(); return; }
        query_ = query_.substr(first, query_.find_last_not_of(" \t\r\n") - first + 1);
        entry_ = {}; matches_.clear();
        matches_ = archive_.titles(query_, moreMatches_);
        selection_ = 0; screen_ = Screen::Results;
        status_ = matches_.empty() ? "No matching titles. Back to try again." : "";
      }
    }
    requestUpdate();
  };
  startActivityForResult(std::move(keyboard), std::move(handler));
}
int WikiActivity::itemCount() const {
  if (screen_ == Screen::Home) return 3;
  if (screen_ == Screen::Options) return 6;
  if (screen_ == Screen::Results) return int(matches_.size());
  if (screen_ == Screen::Bookmarks) return int(bookmarks_.items().size());
  return 0;
}
void WikiActivity::saveBookmark() {
  if (entry_.found) { bookmarks_.toggle(entry_.key, title_); status_ = bookmarks_.status(); requestUpdate(); }
}
void WikiActivity::cycleFont() {
  fontStep_ = (fontStep_+1)%3; resetPages(); status_ = "Text size changed"; requestUpdate();
}
void WikiActivity::activate() {
  if (screen_ == Screen::Home) {
    if (selection_ == 0) openSearch();
    else if (selection_ == 1) changeEntry(0);
    else { screen_ = Screen::Bookmarks; selection_ = 0; status_ = bookmarks_.status(); requestUpdate(); }
  } else if (screen_ == Screen::Results && selection_ < int(matches_.size())) openTitle(matches_[selection_].key);
  else if (screen_ == Screen::Bookmarks && selection_ < int(bookmarks_.items().size())) openTitle(bookmarks_.items()[selection_].key);
  else if (screen_ == Screen::Article) { screen_ = Screen::Options; selection_ = 0; requestUpdate(); }
  else if (screen_ == Screen::Options) {
    switch (selection_) {
      case 0: saveBookmark(); screen_ = Screen::Article; break;
      case 1: changeEntry(0); break;
      case 2: openSearch(); break;
      case 3: cycleFont(); screen_ = Screen::Article; break;
      case 4: { const auto key = entry_.key; cleanView_ = !cleanView_; openTitle(key); break; }
      default: screen_ = Screen::Article; break;
    }
    requestUpdate();
  }
}
void WikiActivity::loop() {
  RenderLock lock;
  using Button = MappedInputManager::Button;
  if (mappedInput.wasPressed(Button::Back)) { backDown_ = true; backLong_ = false; }
  if (backDown_ && !backLong_ && screen_ == Screen::Article && mappedInput.isPressed(Button::Back) && mappedInput.getHeldTime() >= HOLD_MS) {
    backLong_ = true; cycleFont();
  }
  if (mappedInput.wasReleased(Button::Back)) {
    const bool tap = backDown_ && !backLong_; backDown_ = backLong_ = false;
    if (tap) {
      if (loadError_ || screen_ == Screen::Home) activityManager.goHome(HomeMenuItem::WIKI);
      else if (screen_ == Screen::Options) { screen_ = Screen::Article; requestUpdate(); }
      else goWikiHome();
    }
    return;
  }
  if (loadError_) return;
  if (mappedInput.wasPressed(Button::Confirm)) { confirmDown_ = true; confirmLong_ = false; }
  if (confirmDown_ && !confirmLong_ && screen_ == Screen::Article && mappedInput.isPressed(Button::Confirm) && mappedInput.getHeldTime() >= HOLD_MS) {
    confirmLong_ = true; saveBookmark();
  }
  if (mappedInput.wasReleased(Button::Confirm)) {
    const bool tap = confirmDown_ && !confirmLong_; confirmDown_ = confirmLong_ = false;
    if (tap) activate();
    return;
  }
  if (screen_ == Screen::Article) {
    if (mappedInput.wasPressed(Button::Left)) changeEntry(-1);
    else if (mappedInput.wasPressed(Button::Right)) changeEntry(1);
    else if (mappedInput.wasPressed(Button::Up) && page_ > 0) { --page_; requestUpdate(); }
    else if (mappedInput.wasPressed(Button::Down) && hasNext_ && size_t(page_+1) < pages_.size()) { pages_[++page_] = next_; requestUpdate(); }
  } else {
    const int n = itemCount();
    if (n && (mappedInput.wasPressed(Button::Left) || mappedInput.wasPressed(Button::Up))) { selection_ = (selection_+n-1)%n; requestUpdate(); }
    else if (n && (mappedInput.wasPressed(Button::Right) || mappedInput.wasPressed(Button::Down))) { selection_ = (selection_+1)%n; requestUpdate(); }
  }
}
void WikiActivity::renderHome() {
  const auto& m = UITheme::getInstance().getMetrics();
  const int w = renderer.getScreenWidth(), h = renderer.getScreenHeight(), side = std::max(24, m.contentSidePadding);
  const bool compact = h < 600;
  const int globeSize = compact ? 40 : 64, logoY = compact ? 12 : 48;
  WikiGlobe::draw(renderer,(w-globeSize)/2,logoY,globeSize,true);
  int y = logoY+globeSize+12;
  renderer.drawCenteredText(titleFont(), y, "Wikipedia");
  y += renderer.getLineHeight(titleFont())+10;
  renderer.drawCenteredText(SMALL_FONT_ID, y, "The offline encyclopedia");
  y += renderer.getLineHeight(SMALL_FONT_ID)+(compact ? 14 : 34);
  if (loadError_) {
    for (const char* line : {"No readable Wikipedia pack found.", "Copy wikipedia.cdb to the SD card.", "This version reads WCDB, not ZIM."}) {
      renderer.drawText(SMALL_FONT_ID, side, y, line); y += renderer.getLineHeight(SMALL_FONT_ID)+8;
    }
    return;
  }
  const int row = std::max(compact ? 42 : 56, renderer.getLineHeight(UI_12_FONT_ID)+16);
  const char* labels[] = {"Search Wikipedia...", "Random article", "Bookmarks"};
  for (int i=0; i<3; ++i) {
    const bool selected = selection_ == i;
    // Search stays a recognizable outlined field; selection is a thicker border.
    renderer.drawRoundedRect(side,y,w-2*side,row,selected ? 3 : 1,6,true);
    renderer.drawText(UI_12_FONT_ID,side+16,y+(row-renderer.getLineHeight(UI_12_FONT_ID))/2,labels[i]);
    if (i == 0) renderer.drawText(UI_12_FONT_ID,w-side-30,y+(row-renderer.getLineHeight(UI_12_FONT_ID))/2,"_");
    y += row+12;
  }
  char count[72]; std::snprintf(count,sizeof(count),"%lu indexed titles   |   %u saved",static_cast<unsigned long>(archive_.entryCount()),unsigned(bookmarks_.items().size()));
  const int bottom = h-m.buttonHintsHeight-renderer.getLineHeight(SMALL_FONT_ID)-8;
  if (y+renderer.getLineHeight(SMALL_FONT_ID) < bottom) renderer.drawCenteredText(SMALL_FONT_ID,y+8,count);
}
void WikiActivity::renderList() {
  const auto& m = UITheme::getInstance().getMetrics();
  const int w = renderer.getScreenWidth(), h = renderer.getScreenHeight(), side = std::max(24,m.contentSidePadding);
  const char* heading = screen_ == Screen::Results ? "Search results" : screen_ == Screen::Bookmarks ? "Bookmarks" : "Article options";
  GUI.drawHeader(renderer,Rect{0,m.topPadding,w,m.headerHeight},heading);
  int top = m.topPadding+m.headerHeight+16;
  const auto subtitle = renderer.truncatedText(SMALL_FONT_ID,(screen_ == Screen::Results ? query_ : screen_ == Screen::Options ? title_ : "Saved on your SD card").c_str(),w-2*side);
  renderer.drawText(SMALL_FONT_ID,side,top,subtitle.c_str());
  top += renderer.getLineHeight(SMALL_FONT_ID)+14;
  const int row = std::max(46,renderer.getLineHeight(UI_12_FONT_ID)+18);
  const int bottom = h-m.buttonHintsHeight-2*renderer.getLineHeight(SMALL_FONT_ID)-16;
  const int visible = std::max(1,(bottom-top)/row), n = itemCount();
  const int start = std::max(0,selection_-visible+1);
  const char* options[] = {bookmarks_.contains(entry_.key) ? "Remove bookmark" : "Save bookmark", "Random article", "Search Wikipedia", "Change text size", cleanView_ ? "Show original pack text" : "Use clean reading view", "Back to article"};
  if (!n) renderer.drawText(UI_12_FONT_ID,side,top,screen_ == Screen::Bookmarks ? "No saved articles yet." : "No matching titles.");
  for (int i=start; i<n && i<start+visible; ++i) {
    const int y = top+(i-start)*row;
    const bool selected = i == selection_;
    if (selected) renderer.fillRect(side,y,w-2*side,row-4,true);
    const std::string label = screen_ == Screen::Results ? matches_[i].label : screen_ == Screen::Bookmarks ? bookmarks_.items()[i].title : options[i];
    const auto shortened = renderer.truncatedText(UI_12_FONT_ID,label.c_str(),w-2*side-20);
    renderer.drawText(UI_12_FONT_ID,side+10,y+(row-4-renderer.getLineHeight(UI_12_FONT_ID))/2,shortened.c_str(),!selected);
  }
  if (screen_ == Screen::Results && moreMatches_) renderer.drawText(SMALL_FONT_ID,side,bottom,"More matches: refine your search.");
  else if (n > visible) {
    char position[48]; std::snprintf(position,sizeof(position),"%d of %d",selection_+1,n);
    renderer.drawText(SMALL_FONT_ID,side,bottom,position);
  }
}
void WikiActivity::drawRichLine(int font, int x, int y, char* line, WikiText::Kind kind) {
  if (!cleanView_ || kind != WikiText::Kind::Body) {
    renderer.drawText(font,x,y,line,true,kind == WikiText::Kind::Heading ? EpdFontFamily::BOLD : EpdFontFamily::REGULAR); return;
  }
  size_t begin = 0;
  for (size_t pos=0; line[pos];) {
    size_t end = pos;
    if (!WikiText::citation(line,pos,end)) { ++pos; continue; }
    const char saved = line[pos]; line[pos] = 0;
    renderer.drawText(font,x,y,line+begin); x += renderer.getTextWidth(font,line+begin); line[pos] = saved;
    const char last = line[end]; line[end] = 0;
    renderer.drawText(SMALL_FONT_ID,x,y,line+pos); x += renderer.getTextWidth(SMALL_FONT_ID,line+pos); line[end] = last;
    begin = pos = end;
  }
  renderer.drawText(font,x,y,line+begin);
}
void WikiActivity::renderArticle() {
  const auto& m = UITheme::getInstance().getMetrics();
  const int w = renderer.getScreenWidth(), h = renderer.getScreenHeight(), side = std::max(24,m.contentSidePadding);
  const int smallHeight = std::max(1,renderer.getLineHeight(SMALL_FONT_ID));
  int y = m.topPadding+8;
  renderer.drawText(SMALL_FONT_ID,side,y,cleanView_ ? "WIKIPEDIA" : "WIKIPEDIA / ORIGINAL PACK TEXT");
  if (bookmarks_.contains(entry_.key)) renderer.drawText(SMALL_FONT_ID,w-side-renderer.getTextWidth(SMALL_FONT_ID,"Saved"),y,"Saved");
  y += smallHeight+10;
  const auto titleLines = renderer.wrappedText(titleFont(),title_.c_str(),w-2*side,2);
  for (const auto& line:titleLines) { renderer.drawText(titleFont(),side,y,line.c_str()); y += renderer.getLineHeight(titleFont()); }
  renderer.drawLine(side,y+6,w-side,y+6); y += 20;
  const int top = y, bottom = h-m.buttonHintsHeight-2*smallHeight-18;
  auto cursor = pages_[page_];
  char line[512];
  while (cursor.block < document_.count()) {
    const auto& block = document_.block(cursor.block);
    cursor.offset = std::max(cursor.offset,block.begin);
    if (cursor.offset >= block.end) { ++cursor.block; cursor.offset = 0; continue; }
    int font = block.kind == WikiText::Kind::Heading ? NOTOSERIF_16_FONT_ID : block.kind == WikiText::Kind::Note ? SMALL_FONT_ID : bodyFont();
    if (renderer.getLineHeight(font) <= 0) font = UI_12_FONT_ID;
    const auto style = block.kind == WikiText::Kind::Heading ? EpdFontFamily::BOLD : EpdFontFamily::REGULAR;
    const int lineHeight = std::max(1,renderer.getLineHeight(font))+2;
    if (cursor.offset == block.begin && y != top) y += block.kind == WikiText::Kind::Heading ? 12 : (cleanView_ ? 8 : 3);
    if (y+lineHeight > bottom) break;
    const size_t next = WikiText::wrap(entry_.text,cursor.offset,block.end,w-2*side,line,sizeof(line),[&](const char* text){return renderer.getTextWidth(font,text,style);});
    drawRichLine(font,side,y,line,block.kind);
    if (next <= cursor.offset) break;
    cursor.offset = uint32_t(next); y += lineHeight;
    if (cursor.offset >= block.end) { ++cursor.block; cursor.offset = 0; }
  }
  next_ = cursor;
  hasNext_ = cursor.block < document_.count() && size_t(page_+1)<pages_.size() &&
      (cursor.block != pages_[page_].block || cursor.offset != pages_[page_].offset);
  char info[96]; std::snprintf(info,sizeof(info),"Page %u%s   |   Side keys: page",unsigned(page_)+1,hasNext_ ? "" : " (end)");
  renderer.drawText(SMALL_FONT_ID,side,bottom+6,info);
}
void WikiActivity::render(RenderLock&&) {
  renderer.clearScreen();
  if (screen_ == Screen::Home) renderHome();
  else if (screen_ == Screen::Article) renderArticle();
  else renderList();
  const auto& m = UITheme::getInstance().getMetrics();
  if (!status_.empty()) {
    const auto text = renderer.truncatedText(SMALL_FONT_ID,status_.c_str(),renderer.getScreenWidth()-48);
    renderer.drawText(SMALL_FONT_ID,24,renderer.getScreenHeight()-m.buttonHintsHeight-renderer.getLineHeight(SMALL_FONT_ID)-6,text.c_str());
  }
  const auto labels = mappedInput.mapLabels(screen_ == Screen::Home ? "Home" : "Back",loadError_ ? "" : screen_ == Screen::Article ? "Options" : screen_ == Screen::Home && selection_ == 0 ? "Search" : "Open",loadError_ ? "" : "Prev",loadError_ ? "" : "Next");
  GUI.drawButtonHints(renderer,labels.btn1,labels.btn2,labels.btn3,labels.btn4);
  renderer.displayBuffer();
}
