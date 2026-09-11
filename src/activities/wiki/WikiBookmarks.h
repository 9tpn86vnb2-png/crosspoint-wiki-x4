#pragma once
#include <cstdint>
#include <string>
#include <vector>

// Two CRC-checked alternating snapshots on SD. A failed new write never
// truncates the last accepted snapshot. This is not a filesystem journal.
class WikiBookmarks {
 public:
  struct Item { std::string key, title; };
  static constexpr size_t MAX_ITEMS = 64;
  static constexpr size_t MAX_PAYLOAD = 16384;
  bool load();
  bool toggle(const std::string& key, const std::string& title);
  bool contains(const std::string& key) const;
  const std::vector<Item>& items() const { return items_; }
  const char* status() const { return status_; }
 private:
  bool save();
  std::vector<Item> items_;
  uint32_t sequence_ = 0;
  int active_ = -1;
  bool writable_ = false;
  const char* status_ = "";
};
