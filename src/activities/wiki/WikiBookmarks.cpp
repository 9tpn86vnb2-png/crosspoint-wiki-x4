#include "WikiBookmarks.h"
#include <HalStorage.h>
#include <algorithm>
#include <array>
#include <cstring>
#include <utility>

namespace {
constexpr const char* DIR = "/.crosspoint/wiki";
constexpr const char* PATHS[] = {"/.crosspoint/wiki/bookmarks.a", "/.crosspoint/wiki/bookmarks.b"};
uint32_t get32(const uint8_t* p) { return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24; }
void put32(uint8_t* p, uint32_t v) { for (unsigned i=0; i<4; ++i) p[i] = uint8_t(v >> (8*i)); }
uint32_t crc(const uint8_t* p, size_t n, uint32_t value = 0xffffffffU) {
  for (size_t i=0; i<n; ++i) { value ^= p[i]; for (int bit=0; bit<8; ++bit) value = (value >> 1) ^ ((value & 1) ? 0xedb88320U : 0); }
  return value;
}
bool validString(const std::string& s) {
  if (s.empty() || s.size() > 1024) return false;
  for (unsigned char c : s) if (c < 32 || c == 127) return false;
  return true;
}
bool readSlot(int slot, uint32_t& sequence, std::vector<WikiBookmarks::Item>& items) {
  auto file = Storage.open(PATHS[slot], O_RDONLY);
  if (!file) return false;
  std::array<uint8_t,20> h{};
  const size_t size = file.size();
  if (size < h.size() || size > h.size() + WikiBookmarks::MAX_PAYLOAD || file.read(h.data(),h.size()) != int(h.size()) ||
      std::memcmp(h.data(),"WKB2",4)) return false;
  const uint32_t n = get32(h.data()+8), bytes = get32(h.data()+12);
  if (n > WikiBookmarks::MAX_ITEMS || bytes > WikiBookmarks::MAX_PAYLOAD || bytes + h.size() != size) return false;
  std::vector<uint8_t> payload(bytes);
  if (bytes && file.read(payload.data(),bytes) != int(bytes)) return false;
  if (~crc(payload.data(),payload.size(),crc(h.data(),16)) != get32(h.data()+16)) return false;
  std::vector<WikiBookmarks::Item> parsed;
  parsed.reserve(n);
  size_t pos = 0;
  for (uint32_t i=0; i<n; ++i) {
    if (payload.size()-pos < 4) return false;
    const size_t keyLen = payload[pos] | size_t(payload[pos+1]) << 8;
    const size_t titleLen = payload[pos+2] | size_t(payload[pos+3]) << 8;
    pos += 4;
    if (!keyLen || keyLen > 1024 || !titleLen || titleLen > 1024 || keyLen+titleLen > payload.size()-pos) return false;
    WikiBookmarks::Item item{std::string(reinterpret_cast<const char*>(payload.data()+pos),keyLen),
      std::string(reinterpret_cast<const char*>(payload.data()+pos+keyLen),titleLen)};
    if (!validString(item.key) || !validString(item.title)) return false;
    for (const auto& old : parsed) if (old.key == item.key) return false;
    parsed.push_back(std::move(item));
    pos += keyLen+titleLen;
  }
  if (pos != payload.size()) return false;
  sequence = get32(h.data()+4);
  items = std::move(parsed);
  return true;
}
}
bool WikiBookmarks::load() {
  items_.clear(); sequence_ = 0; active_ = -1; writable_ = false; status_ = "";
  bool damaged = false;
  for (int slot=0; slot<2; ++slot) {
    if (!Storage.exists(PATHS[slot])) continue;
    uint32_t seq = 0;
    std::vector<Item> candidate;
    if (!readSlot(slot,seq,candidate)) { damaged = true; continue; }
    const uint32_t delta = seq-sequence_;
    if (active_ < 0 || (delta && delta < 0x80000000U)) { active_ = slot; sequence_ = seq; items_ = std::move(candidate); }
  }
  writable_ = active_ >= 0 || !damaged;
  if (damaged) status_ = writable_ ? "Recovered previous bookmarks" : "Bookmark files damaged; saving disabled";
  return writable_;
}
bool WikiBookmarks::contains(const std::string& key) const {
  return std::any_of(items_.begin(),items_.end(),[&](const Item& item){return item.key==key;});
}
bool WikiBookmarks::save() {
  size_t bytes = 0;
  for (const auto& item:items_) bytes += 4 + item.key.size() + item.title.size();
  if (bytes > MAX_PAYLOAD) { status_ = "Bookmark storage limit reached"; return false; }
  if (!Storage.ensureDirectoryExists(DIR)) { status_ = "Cannot create bookmark folder on SD"; return false; }
  std::vector<uint8_t> payload(bytes);
  size_t pos = 0;
  for (const auto& item:items_) {
    payload[pos++] = uint8_t(item.key.size()); payload[pos++] = uint8_t(item.key.size() >> 8);
    payload[pos++] = uint8_t(item.title.size()); payload[pos++] = uint8_t(item.title.size() >> 8);
    std::memcpy(payload.data()+pos,item.key.data(),item.key.size()); pos += item.key.size();
    std::memcpy(payload.data()+pos,item.title.data(),item.title.size()); pos += item.title.size();
  }
  std::array<uint8_t,20> h{};
  std::memcpy(h.data(),"WKB2",4); put32(h.data()+4,sequence_+1); put32(h.data()+8,uint32_t(items_.size()));
  put32(h.data()+12,uint32_t(bytes)); put32(h.data()+16,~crc(payload.data(),payload.size(),crc(h.data(),16)));
  const int slot = active_ == 0 ? 1 : 0;
  auto file = Storage.open(PATHS[slot],O_WRONLY | O_CREAT | O_TRUNC);
  if (!file || file.write(h.data(),h.size()) != h.size() || (bytes && file.write(payload.data(),bytes) != bytes)) {
    status_ = "Bookmark write failed; previous list retained"; return false;
  }
  file.flush();
  if (!file.close()) { status_ = "Bookmark close failed; previous list retained"; return false; }
  uint32_t seq = 0;
  std::vector<Item> verified;
  if (!readSlot(slot,seq,verified) || seq != sequence_+1 || verified.size() != items_.size()) {
    status_ = "Bookmark verification failed"; return false;
  }
  for (size_t i=0; i<items_.size(); ++i) if (verified[i].key != items_[i].key || verified[i].title != items_[i].title) {
    status_ = "Bookmark verification failed"; return false;
  }
  active_ = slot; sequence_ = seq;
  return true;
}
bool WikiBookmarks::toggle(const std::string& key, const std::string& title) {
  if (!writable_) { status_ = "Bookmark files damaged; saving disabled"; return false; }
  if (!validString(key) || !validString(title)) { status_ = "Invalid bookmark title"; return false; }
  const auto found = std::find_if(items_.begin(),items_.end(),[&](const Item& item){return item.key==key;});
  if (found != items_.end()) {
    const size_t pos = size_t(found-items_.begin());
    Item removed = std::move(*found); items_.erase(found);
    if (!save()) { items_.insert(items_.begin()+pos,std::move(removed)); return false; }
    status_ = "Bookmark removed";
  } else {
    if (items_.size() >= MAX_ITEMS) { status_ = "64 bookmarks saved; remove one first"; return false; }
    items_.push_back({key,title});
    if (!save()) { items_.pop_back(); return false; }
    status_ = "Bookmark saved";
  }
  return true;
}
