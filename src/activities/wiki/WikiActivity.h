#pragma once
#include <array>
#include "activities/Activity.h"
#include "WikiArchive.h"
#include "WikiBookmarks.h"
#include "WikiText.h"

class WikiActivity final : public Activity {
 public:
  WikiActivity(GfxRenderer& renderer, MappedInputManager& input) : Activity("Wiki", renderer, input) {}
  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;
 private:
  enum class Screen { Home, Results, Bookmarks, Article, Options };
  void openSearch();
  void openTitle(std::string key);
  void accept(WikiArchive::Entry entry);
  void changeEntry(int direction);
  void resetPages();
  void goWikiHome();
  void activate();
  void saveBookmark();
  void cycleFont();
  void resetKeys();
  int bodyFont() const;
  int titleFont() const;
  int itemCount() const;
  void renderHome();
  void renderList();
  void renderArticle();
  void drawRichLine(int font, int x, int y, char* line, WikiText::Kind kind);
  WikiArchive archive_;
  WikiArchive::Entry entry_;
  WikiBookmarks bookmarks_;
  WikiText::Document document_;
  std::vector<WikiArchive::Title> matches_;
  std::string query_, title_, status_;
  std::array<WikiText::Cursor, 512> pages_{};
  WikiText::Cursor next_{};
  Screen screen_ = Screen::Home;
  uint16_t page_ = 0;
  int selection_ = 0;
  uint8_t fontStep_ = 1;
  bool cleanView_ = true;
  bool hasNext_ = false, loadError_ = false, moreMatches_ = false;
  bool backDown_ = false, backLong_ = false, confirmDown_ = false, confirmLong_ = false;
};
