#include <Arduino.h>
#include "WikiArchive.h"
#include <InflateReader.h>
#include <esp_random.h>
#include <algorithm>
#include <climits>
#include <cstring>
#include <new>
#include <utility>

namespace {
std::string queryKey(const std::string& text) {
  std::string out;
  bool separator = false;
  for (unsigned char c : text) {
    if (c == ' ' || c == '_' || c == '-' || c == '\t' || c == '\r' || c == '\n') { separator = !out.empty(); continue; }
    if (separator) { out += '-'; separator = false; }
    out += c >= 'A' && c <= 'Z' ? char(c + 32) : char(c);
  }
  return out;
}
uint32_t little32(const uint8_t* p) {
  return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
}

std::string WikiArchive::folded(std::string value) {
  for (char& c : value) if (c >= 'A' && c <= 'Z') c = char(c + ('a' - 'A'));
  return value;
}

void WikiArchive::close() {
  ready_ = false;
  if (file_) file_.close();
  raw_.reset();
  compressed_.reset();
  fileSize_ = dataStart_ = 0;
  blocks_ = entries_ = rawSize_ = cursorBlock_ = cursorLine_ = 0;
  cachedBlock_ = -1;
}

bool WikiArchive::open(const char* path) {
  close();
  file_ = Storage.open(path, O_RDONLY);
  if (!file_) return false;
  uint8_t header[12];
  fileSize_ = file_.size();
  if (fileSize_ < sizeof(header) || file_.read(header, sizeof(header)) != int(sizeof(header)) ||
      std::memcmp(header, "WCDB", 4) != 0) { close(); return false; }
  blocks_ = little32(header + 4);
  entries_ = little32(header + 8);
  dataStart_ = uint64_t(INDEX_START) + uint64_t(blocks_) * RECORD_SIZE;
  if (!blocks_ || blocks_ > INT32_MAX || entries_ < blocks_ || dataStart_ >= fileSize_) {
    close(); return false;
  }
  // Allocation sizes are constants, never values taken from the card. No vector
  // growth and no throwing allocations for either large working buffer.
  raw_.reset(new (std::nothrow) uint8_t[MAX_RAW + 1]);
  compressed_.reset(new (std::nothrow) uint8_t[MAX_COMP]);
  if (!raw_ || !compressed_) { close(); return false; }
  ready_ = true;
  if (!load(0)) { close(); return false; }
  return true;
}

bool WikiArchive::record(uint32_t index, Record& out) {
  if (!ready_ || index >= blocks_) return false;
  const uint64_t position = uint64_t(INDEX_START) + uint64_t(index) * RECORD_SIZE;
  if (!file_.seek(position)) return false;
  uint8_t bytes[RECORD_SIZE];
  if (file_.read(bytes, sizeof(bytes)) != int(sizeof(bytes))) return false;
  std::memcpy(out.first, bytes, 32);
  if (!std::memchr(out.first, 0, 32)) return false;
  out.offset = little32(bytes + 32);
  out.compressed = little32(bytes + 36);
  out.raw = little32(bytes + 40);
  return out.raw > 0 && out.raw <= MAX_RAW && out.compressed > 0 && out.compressed <= MAX_COMP &&
         uint64_t(out.offset) >= dataStart_ && uint64_t(out.offset) + out.compressed <= fileSize_;
}

bool WikiArchive::load(uint32_t block) {
  if (!ready_ || block >= blocks_) return false;
  if (cachedBlock_ == int32_t(block)) return true;
  // A failed read must never leave an old cache ID pointing at overwritten data.
  cachedBlock_ = -1;
  rawSize_ = 0;
  Record r;
  if (!record(block, r) || !file_.seek(r.offset) ||
      file_.read(compressed_.get(), r.compressed) != int(r.compressed)) return false;
  InflateReader inflater;
  if (!inflater.init(false)) return false;
  inflater.setSource(compressed_.get(), r.compressed);
  size_t produced = 0;
  const auto status = inflater.readAtMost(raw_.get(), r.raw + 1, &produced);
  if (status != InflateStatus::Done || produced != r.raw || raw_[r.raw - 1] != '\n' ||
      std::memchr(raw_.get(), 0, r.raw)) return false;
  // Require one bounded, nonempty title and a tab separator on every record.
  uint32_t pos = 0;
  while (pos < r.raw) {
    uint32_t end = pos;
    while (end < r.raw && raw_[end] != '\n') ++end;
    uint32_t tab = pos;
    while (tab < end && raw_[tab] != '\t') ++tab;
    if (tab == pos || tab == end || tab - pos > 1024) return false;
    pos = end + 1;
  }
  rawSize_ = r.raw;
  cachedBlock_ = int32_t(block);
  return true;
}

bool WikiArchive::findStart(const std::string& query, uint32_t& block) {
  // The index stores only the first 31 bytes of a title. Use lower_bound on
  // that truncated key and start one block earlier; duplicate long-title keys
  // must not make exact or prefix lookup skip their earlier blocks.
  const std::string key = folded(query.substr(0, 31));
  uint32_t lo = 0, hi = blocks_;
  while (lo < hi) {
    const uint32_t mid = lo + (hi - lo) / 2;
    Record r;
    if (!record(mid, r)) return false;
    if (folded(r.first) < key) lo = mid + 1;
    else hi = mid;
  }
  block = lo ? lo - 1 : 0;
  return true;
}

uint32_t WikiArchive::lineCount() const {
  uint32_t count = 0;
  for (uint32_t i = 0; i < rawSize_; ++i) if (raw_[i] == '\n') ++count;
  return count;
}

WikiArchive::Entry WikiArchive::line(uint32_t index) const {
  uint32_t pos = 0, number = 0;
  while (pos < rawSize_) {
    uint32_t end = pos;
    while (end < rawSize_ && raw_[end] != '\n') ++end;
    if (number++ == index) {
      uint32_t tab = pos;
      while (tab < end && raw_[tab] != '\t') ++tab;
      if (tab == end) return {};
      Entry result;
      result.title.assign(reinterpret_cast<const char*>(raw_.get() + pos), tab - pos);
      result.key = result.title;
      result.text.assign(reinterpret_cast<const char*>(raw_.get() + tab + 1), end - tab - 1);
      result.found = true;
      return result;
    }
    pos = end + 1;
  }
  return {};
}

WikiArchive::Entry WikiArchive::lookup(const std::string& query, bool prefix) {
  if (!ready_ || query.empty() || query.size() > 1024) return {};
  const std::string key = folded(query);
  uint32_t firstBlock = 0;
  if (!findStart(key, firstBlock)) return {};
  for (uint32_t block = firstBlock; block < blocks_; ++block) {
    if (!load(block)) return {};
    uint32_t pos = 0, number = 0;
    while (pos < rawSize_) {
      uint32_t end = pos;
      while (end < rawSize_ && raw_[end] != '\n') ++end;
      uint32_t tab = pos;
      while (tab < end && raw_[tab] != '\t') ++tab;
      const std::string title(reinterpret_cast<const char*>(raw_.get() + pos), tab - pos);
      const std::string lowerTitle = folded(title);
      if (lowerTitle == key || (prefix && lowerTitle.compare(0, key.size(), key) == 0)) {
        cursorBlock_ = block;
        cursorLine_ = number;
        return line(number);
      }
      if (lowerTitle > key) return {};
      pos = end + 1;
      ++number;
    }
    delay(1);
  }
  return {};
}

WikiArchive::Entry WikiArchive::resolve(Entry entry) {
  const std::string original = entry.title;
  for (unsigned hops = 0; entry.found && !entry.text.empty() && entry.text.front() == '>'; ++hops) {
    if (hops == 8) { entry.text = "Redirect chain too long or cyclic."; return entry; }
    std::string target = entry.text.substr(1);
    const auto a = target.find_first_not_of(" \t\r");
    if (a == std::string::npos) { entry.text = "Empty redirect target."; return entry; }
    target = target.substr(a, target.find_last_not_of(" \t\r") - a + 1);
    // Release the previous body before loading another bounded article.
    entry.text.clear();
    auto resolved = lookup(target, false);
    if (!resolved.found) { entry.text = "Redirect target unavailable: " + target.substr(0, 1024); return entry; }
    entry = std::move(resolved);
  }
  if (entry.found && entry.title != original) entry.title = original + " -> " + entry.title;
  return entry;
}

WikiArchive::Entry WikiArchive::search(const std::string& query, bool prefix) {
  auto entry = lookup(query, prefix);
  // The published pack stores multiword titles as lower-case hyphenated keys.
  // Try literal lookup first to remain compatible with non-slug WCDB packs.
  if (!entry.found && !query.empty() && query.size() <= 1024) {
    const auto slug = queryKey(query);
    if (slug != folded(query)) entry = lookup(slug, prefix);
  }
  return resolve(std::move(entry));
}
WikiArchive::Entry WikiArchive::first() {
  if (!ready_ || !load(0)) return {};
  cursorBlock_ = cursorLine_ = 0;
  return resolve(line(0));
}
WikiArchive::Entry WikiArchive::next() {
  if (!ready_ || !load(cursorBlock_)) return {};
  uint32_t block = cursorBlock_, number = cursorLine_ + 1;
  if (number >= lineCount()) { number = 0; block = (block + 1) % blocks_; }
  if (!load(block)) return {};
  cursorBlock_ = block;
  cursorLine_ = number;
  return resolve(line(number));
}
WikiArchive::Entry WikiArchive::previous() {
  if (!ready_) return {};
  uint32_t block = cursorBlock_, number = cursorLine_;
  if (!number) {
    block = block ? block - 1 : blocks_ - 1;
    if (!load(block) || !lineCount()) return {};
    number = lineCount() - 1;
  } else --number;
  if (!load(block)) return {};
  cursorBlock_ = block;
  cursorLine_ = number;
  return resolve(line(number));
}
WikiArchive::Entry WikiArchive::random() {
  if (!ready_) return {};
  const uint32_t block = esp_random() % blocks_;
  if (!load(block) || !lineCount()) return {};
  cursorBlock_ = block;
  cursorLine_ = esp_random() % lineCount();
  return resolve(line(cursorLine_));
}

std::vector<WikiArchive::Title> WikiArchive::titles(const std::string& query, bool& more, size_t limit) {
  std::vector<Title> results;
  more = false;
  if (!ready_ || query.empty() || query.size() > 1024 || !limit) return results;
  limit = std::min<size_t>(limit, 16);
  const std::string literal = folded(query), slug = queryKey(query);
  for (unsigned attempt = 0; attempt < 2; ++attempt) {
    if (attempt && (slug == literal || !results.empty())) break;
    const std::string& prefix = attempt ? slug : literal;
    if (prefix.empty()) continue;
    uint32_t firstBlock = 0;
    if (!findStart(prefix, firstBlock)) return results;
    size_t allocated = 0;
    bool stop = false;
    for (uint32_t block = firstBlock; block < blocks_ && !stop; ++block) {
      if (!load(block)) return {};
      uint32_t pos = 0;
      while (pos < rawSize_) {
        uint32_t end = pos;
        while (end < rawSize_ && raw_[end] != '\n') ++end;
        uint32_t tab = pos;
        while (tab < end && raw_[tab] != '\t') ++tab;
        const std::string title(reinterpret_cast<const char*>(raw_.get()+pos), tab-pos);
        const auto lower = folded(title);
        if (lower.compare(0, prefix.size(), prefix) == 0) {
          if (results.size() >= limit || allocated + 2 * title.size() + 512 > 16384) { more = true; return results; }
          std::string label = title;
          uint32_t colon = tab+1;
          while (colon < end && colon-tab <= 513 && raw_[colon] != ':') ++colon;
          if (colon < end && raw_[colon] == ':') {
            const std::string candidate(reinterpret_cast<const char*>(raw_.get()+tab+1), colon-tab-1);
            if (queryKey(candidate) == queryKey(title)) label = candidate;
          }
          if (label == title) { for (char& c : label) if (c == '-' || c == '_') c = ' '; if (!label.empty() && label[0] >= 'a' && label[0] <= 'z') label[0] -= 32; }
          allocated += title.size()+label.size();
          results.push_back({title,std::move(label)});
        } else if (lower > prefix) { stop = true; break; }
        pos = end+1;
      }
      delay(1);
    }
  }
  return results;
}
