#pragma once
#include <I18n.h>

#include <string>
#include <vector>

#include "RecentBooksStore.h"
#include "activities/UiListActivity.h"

class RecentBooksActivity final : public UiListActivity {
 public:
  explicit RecentBooksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput, bool finishedMode = false);
  void onEnter() override;
  void onExit() override;

 private:
  int listCount() const override { return static_cast<int>(rowItems.size()); }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  void onRowLongPress(int index) override;
  bool handleButtons() override;
  const char* headerTitle() const override { return finishedMode ? "Finished Books" : tr(STR_MENU_RECENT_BOOKS); }
  void drawFooter() override;

  bool finishedMode = false;
  std::vector<RecentBook> recentBooks;
  std::vector<freeink::ui::ListItem> rowItems;
  void rebuildRowItems();
  void loadRecentBooks();
  int bookIndexForRow(int row) const { return finishedMode ? row : row - 1; }
  void promptRemoveBook(const std::string& path, const std::string& title);
};
