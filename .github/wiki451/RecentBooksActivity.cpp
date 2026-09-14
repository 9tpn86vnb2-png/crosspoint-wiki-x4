#include "RecentBooksActivity.h"

#include <GfxRenderer.h>
#include <HalStorage.h>
#include <I18n.h>

#include <algorithm>
#include <cstdint>
#include <limits>
#include <memory>

#include "MappedInputManager.h"
#include "RecentBooksStore.h"
#include "activities/util/ConfirmationActivity.h"
#include "components/UITheme.h"
#include "components/UiAppHelpers.h"

namespace fui = freeink::ui;

namespace {
constexpr unsigned long LONG_PRESS_MS = 1000;
constexpr uint16_t FINISHED_WINDOW_EXTRA_ROWS = 2;
}  // namespace

RecentBooksActivity::RecentBooksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput)
    : UiListActivity("RecentBooks", renderer, mappedInput, /*wantsTouchLongPress=*/true) {}

int RecentBooksActivity::finishedListCount() const {
  return static_cast<int>(std::min<uint32_t>(finishedCatalog.count, std::numeric_limits<int16_t>::max()));
}

int RecentBooksActivity::listCount() const {
  return finishedMode ? finishedListCount() : static_cast<int>(rowItems.size());
}

const char* RecentBooksActivity::headerTitle() const {
  return finishedMode ? "Finished Books" : tr(STR_MENU_RECENT_BOOKS);
}

void RecentBooksActivity::loadRecentBooks() {
  recentBooks = RECENT_BOOKS.getBooks();
  rebuildRowItems();
}

void RecentBooksActivity::rebuildRowItems() {
  rowItems.clear();
  rowItems.reserve(recentBooks.size() + 1);

  fui::ListItem finished;
  finished.label = "Finished Books";
  finished.subtitle = "Books you have completed";
  finished.icon = listIconFor(Book, 32);
  finished.actionValue = 0;
  rowItems.push_back(finished);

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

void RecentBooksActivity::rebuildFinishedCatalog() {
  finishedWindowBooks.clear();
  finishedRowItems.clear();
  if (!FinishedBooksStore::buildCatalog(finishedCatalog)) {
    finishedCatalog.clear();
    LOG_ERR("RBA", "Failed to load Finished Books catalog");
  }
}

void RecentBooksActivity::enterFinishedBooks() {
  finishedMode = true;
  name = "FinishedBooks";
  nav.reset();
  rebuildFinishedCatalog();
  requestUpdate(true);
}

void RecentBooksActivity::leaveFinishedBooks() {
  finishedMode = false;
  name = "RecentBooks";
  nav.reset();
  finishedWindowBooks.clear();
  finishedRowItems.clear();
  requestUpdate(true);
}

bool RecentBooksActivity::loadFinishedBook(const int index, RecentBook& out) {
  if (index < 0 || index >= finishedListCount()) return false;
  std::vector<RecentBook> one;
  if (!FinishedBooksStore::loadNewestWindow(finishedCatalog, static_cast<uint32_t>(index), 1, one) || one.empty()) {
    return false;
  }
  out = std::move(one.front());
  return true;
}

void RecentBooksActivity::buildFinishedWindow(const uint16_t first, const uint16_t count) {
  finishedWindowBooks.clear();
  finishedRowItems.clear();
  if (!FinishedBooksStore::loadNewestWindow(finishedCatalog, first, count, finishedWindowBooks)) return;

  finishedRowItems.reserve(finishedWindowBooks.size());
  for (size_t i = 0; i < finishedWindowBooks.size(); ++i) {
    const auto& book = finishedWindowBooks[i];
    fui::ListItem item;
    item.label = book.title.empty() ? book.path.c_str() : book.title.c_str();
    if (!book.author.empty()) item.subtitle = book.author.c_str();
    item.icon = listIconFor(UITheme::getFileIcon(book.path), 32);
    item.actionValue = static_cast<int16_t>(first + i);
    finishedRowItems.push_back(item);
  }

  const auto visible = static_cast<uint32_t>(finishedWindowBooks.size());
  renderer.prewarmFallbackText(
      uiScaleSpec().smallFontId,
      [](const void* ctx, uint32_t i) -> const char* {
        return (*static_cast<const std::vector<RecentBook>*>(ctx))[i].title.c_str();
      },
      &finishedWindowBooks, visible, EpdFontFamily::BOLD);
  renderer.prewarmFallbackText(
      uiScaleSpec().smallFontId,
      [](const void* ctx, uint32_t i) -> const char* {
        return (*static_cast<const std::vector<RecentBook>*>(ctx))[i].author.c_str();
      },
      &finishedWindowBooks, visible);
}

void RecentBooksActivity::onEnter() {
  UiListActivity::onEnter();
  if (RECENT_BOOKS.pruneMissing()) RECENT_BOOKS.saveToFile();
  loadRecentBooks();
}

void RecentBooksActivity::onExit() {
  Activity::onExit();
  rowItems.clear();
  recentBooks.clear();
  finishedRowItems.clear();
  finishedWindowBooks.clear();
  finishedCatalog.clear();
}

void RecentBooksActivity::activateIndex(const int row) {
  if (row < 0 || row >= listCount()) return;
  app.clearTapFlash();

  if (!finishedMode) {
    if (row == 0) {
      enterFinishedBooks();
      return;
    }
    const int index = recentBookIndexForRow(row);
    if (index < 0 || index >= static_cast<int>(recentBooks.size())) return;
    onSelectBook(recentBooks[index].path);
    return;
  }

  RecentBook book;
  if (!loadFinishedBook(row, book)) return;
  if (!Storage.exists(book.path.c_str())) {
    FinishedBooksStore::removeByPath(book.path);
    rebuildFinishedCatalog();
    if (nav.selected >= listCount()) nav.selected = std::max(0, listCount() - 1);
    nav.follow(listCount());
    requestUpdate(true);
    return;
  }
  onSelectBook(book.path);
}

void RecentBooksActivity::onRowLongPress(const int row) {
  if (row < 0 || row >= listCount()) return;
  if (!finishedMode && row == 0) return;
  app.clearTapFlash();

  if (!finishedMode) {
    const int index = recentBookIndexForRow(row);
    if (index >= 0 && index < static_cast<int>(recentBooks.size())) {
      promptRemoveBook(recentBooks[index].path, recentBooks[index].title, false);
    }
    return;
  }

  RecentBook book;
  if (loadFinishedBook(row, book)) promptRemoveBook(book.path, book.title, true);
}

bool RecentBooksActivity::handleButtons() {
  if (mappedInput.wasReleased(MappedInputManager::Button::Confirm)) {
    const int selected = nav.selected;
    if (selected >= 0 && selected < listCount()) {
      if (mappedInput.getHeldTime() >= LONG_PRESS_MS && (finishedMode || selected != 0)) {
        onRowLongPress(selected);
      } else {
        activateIndex(selected);
      }
      return true;
    }
  }

  if (mappedInput.wasReleased(MappedInputManager::Button::Back)) {
    if (finishedMode) leaveFinishedBooks();
    else onGoHome();
    return true;
  }
  return false;
}

void RecentBooksActivity::promptRemoveBook(const std::string& path, const std::string& title, const bool finished) {
  auto handler = [this, path, finished](const ActivityResult& res) {
    if (res.isCancelled) return;
    const bool removed = finished ? FinishedBooksStore::removeByPath(path) : RECENT_BOOKS.removeByPath(path);
    if (!removed) return;

    closeRouting();
    if (finished) rebuildFinishedCatalog();
    else loadRecentBooks();

    if (listCount() == 0) nav.selected = 0;
    else if (nav.selected >= listCount()) nav.selected = listCount() - 1;
    nav.follow(listCount());
    requestUpdate(true);
  };

  startActivityForResult(
      std::make_unique<ConfirmationActivity>(renderer, mappedInput,
                                             finished ? "Remove from Finished Books?" : tr(STR_REMOVE_FROM_RECENTS),
                                             title),
      std::move(handler));
}

void RecentBooksActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  screen.setContentMarginFromScreen(fui::Insets{static_cast<int16_t>(metrics.topPadding + metrics.headerHeight), 0,
                                                static_cast<int16_t>(metrics.buttonHintsHeight), 0});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));

  if (finishedMode) {
    const int total = finishedListCount();
    if (total == 0) {
      screen.centeredText("No finished books yet", screen.theme().bodyText);
      return;
    }

    fui::ListProps props;
    props.count = static_cast<uint16_t>(total);
    props.action = ACTION_ROW;
    props.inputMask = fui::InputTouch | fui::InputLongPress;
    fui::TextStyle label = screen.theme().smallText;
    label.bold = true;
    props.labelText = label;

    syncListViewport(screen, props, /*hasSubtitle=*/true);
    const uint16_t first = props.topIndex;
    const int planned = std::max(1, nav.visibleRows) + FINISHED_WINDOW_EXTRA_ROWS;
    const uint16_t wanted = static_cast<uint16_t>(
        std::min<int>(planned, std::max(0, total - static_cast<int>(first))));
    buildFinishedWindow(first, wanted);

    props.items = finishedRowItems.data();
    props.itemsWindowFirst = first;
    props.itemsWindowCount = static_cast<uint16_t>(finishedRowItems.size());
    screen.list(props);
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
  syncListViewport(screen, props, /*hasSubtitle=*/true);
  screen.list(props);
}

void RecentBooksActivity::drawFooter() {
  const bool empty = listCount() == 0;
  const auto labels = mappedInput.mapLabels(finishedMode ? tr(STR_BACK) : tr(STR_HOME),
                                            empty ? "" : tr(STR_OPEN),
                                            empty ? "" : tr(STR_DIR_UP),
                                            empty ? "" : tr(STR_DIR_DOWN));
  GUI.drawButtonHints(renderer, labels.btn1, labels.btn2, labels.btn3, labels.btn4);
}
