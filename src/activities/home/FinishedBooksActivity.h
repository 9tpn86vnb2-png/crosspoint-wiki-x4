#pragma once

#include <string>
#include <vector>

#include "RecentBooksStore.h"
#include "activities/UiListActivity.h"

class FinishedBooksActivity final : public UiListActivity {
 public:
  explicit FinishedBooksActivity(GfxRenderer& renderer, MappedInputManager& mappedInput);
  void onEnter() override;
  void onExit() override;

 private:
  int listCount() const override { return static_cast<int>(finishedBooks.size()); }
  void buildScreen(UiScreen& screen) override;
  void activateIndex(int index) override;
  bool handleButtons() override;
  const char* headerTitle() const override { return "Finished Books"; }
  void drawFooter() override;

  std::vector<RecentBook> finishedBooks;
  std::vector<freeink::ui::ListItem> rowItems;
  void loadFinishedBooks();
  void rebuildRowItems();
};
