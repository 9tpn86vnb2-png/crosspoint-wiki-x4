#include "RecentBooksActivity.h"

#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>

#include <algorithm>
#include <memory>

#include "MappedInputManager.h"
#include "RecentBooksStore.h"
#include "activities/util/ConfirmationActivity.h"
#include "components/UITheme.h"
#include "components/UiAppHelpers.h"

namespace fui = freeink::ui;

namespace {
constexpr unsigned long LONG_PRESS_MS = 1000;
}  // namespace

RecentBooksActivity::RecentBooksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, bool finishedMode)
    : UiListActivity(finishedMode ? "FinishedBooks" : "RecentBooks", renderer, mappedInput, true),
      finishedMode(finishedMode) {}

void RecentBooksActivity::loadRecentBooks() {
  recentBooks = finishedMode ? RECENT_BOOKS.getFinishedBooks() : RECENT_BOOKS.getBooks();
  rebuildRowItems();
}

void RecentBooksActivity::rebuildRowItems() {
  rowItems.clear();
  rowItems.reserve(recentBooks.size());
  for (const auto& book : recentBooks) {
    fui::ListItem item;
    item.label = book.title.empty() ? book.path.c_str() : book.title.c_str();
    if (!book.author.empty()) item.subtitle = book.author.c_str();
    item.icon = listIconFor(UITheme::getFileIcon(book.path), 32);
    item.actionValue = static_cast<int16_t>(rowItems.size());
    rowItems.push_back(item);
  }

  const auto count = static_cast<uint32_t>(recentBooks.size());
  renderer.prewarmFallbackText(
      uiScaleSpec().smallFontId,
      [](const void* ctx, uint32_t i) -> const char* {
        return (*static_cast<const std::vector<RecentBook>*>(ctx))[i].title.c_str();
      },
      &recentBooks, count, EpdFontFamily::BOLD);
  renderer.prewarmFallbackText(
      uiScaleSpec().smallFontId,
      [](const void* ctx, uint32_t i) -> const char* {
        return (*static_cast<const std::vector<RecentBook>*>(ctx))[i].author.c_str();
      },
      &recentBooks, count);
}

void RecentBooksActivity::onEnter() {
  UiListActivity::onEnter();
  if (!finishedMode && RECENT_BOOKS.pruneMissing()) RECENT_BOOKS.saveToFile();
  loadRecentBooks();
}

void RecentBooksActivity::onExit() {
  Activity::onExit();
  rowItems.clear();
  recentBooks.clear();
}

void RecentBooksActivity::activateIndex(const int index) {
  if (index < 0 || index >= listCount()) return;
  app.clearTapFlash();
  if (finishedMode && !Storage.exists(recentBooks[index].path.c_str())) {
    RECENT_BOOKS.removeFinishedByPath(recentBooks[index].path);
    loadRecentBooks();
    if (recentBooks.empty()) nav.selected = 0;
    else if (nav.selected >= listCount()) nav.selected = listCount() - 1;
    nav.follow(listCount());
    requestUpdate(true);
    return;
  }
  onSelectBook(recentBooks[index].path);
}

void RecentBooksActivity::onRowLongPress(const int index) {
  if (index < 0 || index >= listCount()) return;
  app.clearTapFlash();
  promptRemoveBook(recentBooks[index].path, recentBooks[index].title);
}

bool RecentBooksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    if (!recentBooks.empty() && nav.selected < listCount()) {
      if (mappedInput.getHeldTime() >= LONG_PRESS_MS) {
        promptRemoveBook(recentBooks[nav.selected].path, recentBooks[nav.selected].title);
      } else {
        activateIndex(nav.selected);
      }
      return true;
    }
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    onGoHome(finishedMode ? HomeMenuItem::FINISHED_BOOKS : HomeMenuItem::RECENTS);
    return true;
  }

  return false;
}

void RecentBooksActivity::promptRemoveBook(const std::string& path, const std::string& title) {
  auto handler = [this, path](const ActivityResult& res) {
    if (res.isCancelled) return;
    const bool removed = finishedMode ? RECENT_BOOKS.removeFinishedByPath(path) : RECENT_BOOKS.removeByPath(path);
    if (removed) {
      closeRouting();
      loadRecentBooks();
      if (recentBooks.empty()) nav.selected = 0;
      else if (nav.selected >= listCount()) nav.selected = listCount() - 1;
      nav.follow(listCount());
      requestUpdate(true);
    }
  };

  const char* prompt = finishedMode ? "Remove from Finished Books?" : tr(STR_REMOVE_FROM_RECENTS);
  startActivityForResult(std::make_unique<ConfirmationActivity>(renderer, mappedInput, prompt, title),
                         std::move(handler));
}

void RecentBooksActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  screen.setContentMarginFromScreen(fui::Insets{static_cast<int16_t>(metrics.topPadding + metrics.headerHeight), 0,
                                                static_cast<int16_t>(metrics.buttonHintsHeight), 0});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  if (recentBooks.empty()) {
    screen.centeredText(finishedMode ? "No finished books yet" : tr(STR_NO_RECENT_BOOKS), screen.theme().bodyText);
    return;
  }

  fui::ListProps props;
  props.items = rowItems.data();
  props.count = static_cast<uint16_t>(rowItems.size());
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch | fui::InputLongPress;
  fui::TextStyle label = screen.theme().smallText;
  label.bold = true;
  props.labelText = label;
  syncListViewport(screen, props, true);
  screen.list(props);
}

void RecentBooksActivity::drawFooter() {
  const bool empty = recentBooks.empty();
  const auto labels = mappedInput.mapLabels(tr(STR_HOME), empty ? "" : tr(STR_OPEN), empty ? "" : tr(STR_DIR_UP),
                                            empty ? "" : tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}
