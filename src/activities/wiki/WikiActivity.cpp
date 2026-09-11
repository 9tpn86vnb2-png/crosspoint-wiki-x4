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
#include "fontIds.h"

namespace {
constexpr int FONTS[] = {SMALL_FONT_ID, UI_12_FONT_ID, BITTER_16_FONT_ID};
constexpr unsigned HOLD_MS = 600;
}

int WikiActivity::bodyFont() const {
  const int font = FONTS[fontStep_ % 3];
  return renderer.getLineHeight(font) > 0 ? font : UI_12_FONT_ID;
}
void WikiActivity::resetPages() {
  page_ = 0;
  pageOffsets_[0] = nextOffset_ = 0;
  hasNext_ = false;
}
void WikiActivity::accept(WikiArchive::Entry entry) {
  entry_ = std::move(entry);
  status_ = entry_.found ? "" : "Article unavailable or damaged";
  resetPages();
}
void WikiActivity::onEnter() {
  Activity::onEnter();
  RenderLock lock;
  Preferences preferences;
  if (preferences.begin("wikibeta", true)) {
    fontStep_ = preferences.getUChar("font", 1) % 3;
    preferences.end();
  }
  loadError_ = !archive_.open("/wikipedia.cdb");
  if (loadError_) loadError_ = !archive_.open("/Wikipedia/wikipedia.cdb");
  if (!loadError_) accept(archive_.first());
  requestUpdate();
}
void WikiActivity::onExit() {
  // ActivityManager already holds RenderLock during onExit.
  Preferences preferences;
  if (preferences.begin("wikibeta", false)) {
    preferences.putUChar("font", fontStep_);
    preferences.end();
  }
  archive_.close();
  entry_ = {};
  Activity::onExit();
}
void WikiActivity::changeEntry(int direction) {
  // Free the previous body before allocating the next one.
  entry_ = {};
  if (direction > 0) accept(archive_.next());
  else if (direction < 0) accept(archive_.previous());
  else accept(archive_.random());
}
void WikiActivity::openSearch() {
  auto keyboard = std::unique_ptr<KeyboardEntryActivity>(
      new (std::nothrow) KeyboardEntryActivity(renderer, mappedInput, "Wikipedia title"));
  if (!keyboard) { status_ = "Not enough memory for search"; requestUpdate(); return; }
  auto handler = [this](const ActivityResult& result) {
    RenderLock lock;
    backDown_ = backLong_ = confirmDown_ = confirmLong_ = false;
    if (!result.isCancelled) {
      const auto* typed = std::get_if<KeyboardResult>(&result.data);
      if (typed && !typed->text.empty()) {
        std::string query = typed->text.substr(0, 1024);
        const auto first = query.find_first_not_of(" \t\r\n");
        if (first != std::string::npos) {
          query = query.substr(first, query.find_last_not_of(" \t\r\n") - first + 1);
          entry_ = {};
          auto match = archive_.search(query);
          if (!match.found) match = archive_.search(query, true);
          accept(std::move(match));
          if (!entry_.found) status_ = "No title beginning: " + query;
        }
      }
    }
    requestUpdate();
  };
  startActivityForResult(std::move(keyboard), std::move(handler));
}
void WikiActivity::loop() {
  RenderLock lock;
  using Button = MappedInputManager::Button;
  if (mappedInput.wasPressed(Button::Back)) { backDown_ = true; backLong_ = false; }
  if (backDown_ && !backLong_ && !loadError_ && mappedInput.isPressed(Button::Back) &&
      mappedInput.getHeldTime() >= HOLD_MS) {
    backLong_ = true;
    fontStep_ = (fontStep_ + 1) % 3;
    resetPages();
    requestUpdate();
  }
  if (mappedInput.wasReleased(Button::Back)) {
    const bool goHome = backDown_ && !backLong_;
    backDown_ = backLong_ = false;
    if (goHome) activityManager.goHome(HomeMenuItem::WIKI);
    return;
  }
  if (loadError_) return;
  if (mappedInput.wasPressed(Button::Confirm)) { confirmDown_ = true; confirmLong_ = false; }
  if (confirmDown_ && !confirmLong_ && mappedInput.isPressed(Button::Confirm) &&
      mappedInput.getHeldTime() >= HOLD_MS) {
    confirmLong_ = true;
    changeEntry(0);
    requestUpdate();
  }
  if (mappedInput.wasReleased(Button::Confirm)) {
    const bool search = confirmDown_ && !confirmLong_;
    confirmDown_ = confirmLong_ = false;
    if (search) openSearch();
    return;
  }
  if (mappedInput.wasPressed(Button::Left)) { changeEntry(-1); requestUpdate(); }
  else if (mappedInput.wasPressed(Button::Right)) { changeEntry(1); requestUpdate(); }
  else if (mappedInput.wasPressed(Button::Up) && page_ > 0) { --page_; requestUpdate(); }
  else if (mappedInput.wasPressed(Button::Down) && hasNext_ && size_t(page_ + 1) < pageOffsets_.size()) {
    pageOffsets_[++page_] = nextOffset_;
    requestUpdate();
  }
}

size_t WikiActivity::nextLine(size_t from, int width, char* output, size_t capacity) const {
  // Layout only one line at a time. Never duplicate a whole article into a
  // vector of wrapped strings. All cursor values are byte offsets into text.
  const std::string& text = entry_.text;
  size_t pos = from, used = 0, breakInput = from, breakOutput = 0;
  bool haveBreak = false;
  output[0] = 0;
  while (pos < text.size() && (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\r')) ++pos;
  while (pos < text.size()) {
    const unsigned char c = static_cast<unsigned char>(text[pos]);
    if (c == '\n' || c == '\v') { output[used] = 0; return pos + 1; }
    size_t bytes = 1;
    bool valid = true;
    if (c >= 0x80) {
      if (c >= 0xc2 && c <= 0xdf) bytes = 2;
      else if (c >= 0xe0 && c <= 0xef) bytes = 3;
      else if (c >= 0xf0 && c <= 0xf4) bytes = 4;
      else valid = false;
      if (pos + bytes > text.size()) valid = false;
      if (valid) for (size_t i = 1; i < bytes; ++i)
        if ((static_cast<unsigned char>(text[pos + i]) & 0xc0) != 0x80) valid = false;
      if (valid && bytes >= 3) {
        const unsigned char second = static_cast<unsigned char>(text[pos + 1]);
        if ((c == 0xe0 && second < 0xa0) || (c == 0xed && second >= 0xa0) ||
            (c == 0xf0 && second < 0x90) || (c == 0xf4 && second >= 0x90)) valid = false;
      }
      if (!valid) bytes = 1;
    }
    if (used + bytes >= capacity) {
      if (haveBreak) { output[breakOutput] = 0; return breakInput; }
      output[used] = 0;
      return pos;
    }
    const size_t previous = used;
    if (valid) {
      std::memcpy(output + used, text.data() + pos, bytes);
      if (c == '\t' || c == '\r' || c < 0x20) output[used] = ' ';
      used += bytes;
    } else output[used++] = '?';
    output[used] = 0;
    if (renderer.getTextWidth(bodyFont(), output) > width && previous > 0) {
      if (haveBreak) { output[breakOutput] = 0; return breakInput; }
      output[previous] = 0;
      return pos;
    }
    pos += bytes;
    if (c == ' ' || c == '\t') {
      haveBreak = true;
      breakInput = pos;
      breakOutput = previous;
    }
  }
  output[used] = 0;
  return pos;
}
void WikiActivity::render(RenderLock&&) {
  renderer.clearScreen();
  const auto& m = UITheme::getInstance().getMetrics();
  const int width = renderer.getScreenWidth(), height = renderer.getScreenHeight();
  const int side = std::max(12, m.contentSidePadding);
  const int smallHeight = std::max(1, renderer.getLineHeight(SMALL_FONT_ID));
  const int footer = height - m.buttonHintsHeight - 2 * smallHeight - m.verticalSpacing;
  const int top = m.topPadding + m.headerHeight + m.verticalSpacing;
  const char* title = loadError_ ? "Wiki beta: no readable pack" :
      (!status_.empty() ? status_.c_str() : (entry_.found ? entry_.title.c_str() : "Wiki"));
  GUI.drawHeader(renderer, Rect{0, m.topPadding, width, m.headerHeight}, title);
  if (loadError_) {
    const char* lines[] = {"Copy a compatible WCDB pack as:", "/wikipedia.cdb", "or /Wikipedia/wikipedia.cdb",
      "on your SD card.", "", "Missing, damaged or oversized blocks",
      "and insufficient memory are rejected.", "This beta does not open ZIM files."};
    int y = top;
    for (const char* line : lines) {
      renderer.drawText(SMALL_FONT_ID, side, y, line);
      y += smallHeight + 4;
    }
  } else {
    const int lineHeight = std::max(1, renderer.getLineHeight(bodyFont()));
    size_t offset = std::min<size_t>(pageOffsets_[page_], entry_.text.size());
    char line[512];
    for (int y = top; y + lineHeight <= footer && offset < entry_.text.size(); y += lineHeight) {
      const size_t next = nextLine(offset, std::max(16, width - 2 * side), line, sizeof(line));
      renderer.drawText(bodyFont(), side, y, line);
      if (next <= offset) break;
      offset = next;
    }
    nextOffset_ = offset;
    hasNext_ = offset < entry_.text.size() && size_t(page_ + 1) < pageOffsets_.size();
    renderer.drawText(SMALL_FONT_ID, side, footer, "Hold Search: random   Hold Home: text size");
    char info[80];
    std::snprintf(info, sizeof(info), "Page %u%s | %lu articles | side keys: page",
      unsigned(page_) + 1, hasNext_ ? " +" : " (end)", static_cast<unsigned long>(archive_.entryCount()));
    renderer.drawText(SMALL_FONT_ID, side, footer + smallHeight, info);
  }
  const auto labels = mappedInput.mapLabels("Home", loadError_ ? "" : "Search", loadError_ ? "" : "Prev", loadError_ ? "" : "Next");
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
  renderer.displayBuffer();
}
