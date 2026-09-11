#pragma once
// WCDB layout and navigation adapted from Sparkadium/CrossInk Almanac,
// commit 7eea632e834639ac0f28470aea7fd50ea8923cc7, DictionaryActivity.{h,cpp}.
// MIT License; see WIKI_BETA.md and the repository LICENSE.
#include <cstdint>
#include <memory>
#include <string>
#include <HalStorage.h>

class WikiArchive {
 public:
  struct Entry {
    std::string title;
    std::string text;
    bool found = false;
  };
  bool open(const char* path);
  void close();
  bool ready() const { return ready_; }
  uint32_t entryCount() const { return entries_; }
  Entry first();
  Entry next();
  Entry previous();
  Entry random();
  // Exact lookup, or first prefix match when prefix is true. ASCII case folding;
  // non-ASCII UTF-8 bytes compare literally. Follows at most eight redirects.
  Entry search(const std::string& query, bool prefix = false);

 private:
  static constexpr uint32_t MAX_RAW = 32768;
  static constexpr uint32_t MAX_COMP = MAX_RAW + MAX_RAW / 16 + 64;
  static constexpr uint32_t INDEX_START = 12;
  static constexpr uint32_t RECORD_SIZE = 44;
  struct Record { char first[32]; uint32_t offset, compressed, raw; };
  bool record(uint32_t index, Record& out);
  bool load(uint32_t block);
  bool findStart(const std::string& query, uint32_t& block);
  Entry line(uint32_t index) const;
  uint32_t lineCount() const;
  Entry lookup(const std::string& query, bool prefix);
  Entry resolve(Entry entry);
  static std::string folded(std::string value);
  HalFile file_;
  std::unique_ptr<uint8_t[]> raw_, compressed_;
  uint64_t fileSize_ = 0, dataStart_ = 0;
  uint32_t blocks_ = 0, entries_ = 0, rawSize_ = 0;
  uint32_t cursorBlock_ = 0, cursorLine_ = 0;
  int32_t cachedBlock_ = -1;
  bool ready_ = false;
};
