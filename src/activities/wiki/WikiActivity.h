#pragma once
#include <array>
#include "activities/Activity.h"
#include "WikiArchive.h"

class WikiActivity final : public Activity {
 public:
  WikiActivity(GfxRenderer& renderer, MappedInputManager& input)
      : Activity("Wiki", renderer, input) {}
  void onEnter() override;
  void onExit() override;
  void loop() override;
  void render(RenderLock&&) override;
 private:
  void openSearch();
  void accept(WikiArchive::Entry entry);
  void changeEntry(int direction);
  void resetPages();
  int bodyFont() const;
  size_t nextLine(size_t from, int width, char* output, size_t capacity) const;
  WikiArchive archive_;
  WikiArchive::Entry entry_;
  std::string status_;
  std::array<uint32_t, 512> pageOffsets_{};
  uint16_t page_ = 0;
  uint32_t nextOffset_ = 0;
  uint8_t fontStep_ = 1;
  bool hasNext_ = false, loadError_ = false;
  bool backDown_ = false, backLong_ = false, confirmDown_ = false, confirmLong_ = false;
};
