#pragma once
#include <I18n.h>

#include <cstdint>
#include <string>
#include <vector>

#include "FinishedBooksStore.h"
#include "RecentBooksStore.h"
#include "activities/UiListActivity.h"

class RecentBooksActivity final : public UiListActivity {
 public:
  explicit RecentBooksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput);
  void onEnter() override;
  void onExit() override;

 private:
  int listCount() const override;
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  void onRowLongPress(int index) override;
  bool handleButtons() override;
  const char* headerTitle() const override;
  void drawFooter() override;

  bool finishedMode = false;
  std::vector<RecentBook> recentBooks;
  std::vector<freeink::ui::ListItem> rowItems;

  FinishedBooksCatalog finishedCatalog;
  std::vector<RecentBook> finishedWindowBooks;
  std::vector<freeink::ui::ListItem> finishedRowItems;

  void rebuildRowItems();
  void loadRecentBooks();
  void enterFinishedBooks();
  void leaveFinishedBooks();
  void rebuildFinishedCatalog();
  bool loadFinishedBook(int index, RecentBook& out);
  void buildFinishedWindow(uint16_t first, uint16_t count);
  int finishedListCount() const;
  int recentBookIndexForRow(int row) const { return row - 1; }
  void promptRemoveBook(const std::string& path, const std::string& title, bool finished);
};
