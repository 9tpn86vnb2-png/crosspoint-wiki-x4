#include "WikiText.h"
#include <algorithm>
#include <cstring>

namespace WikiText {
namespace {
bool space(char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v'; }
std::string trim(const std::string& s) {
  size_t a = 0, b = s.size();
  while (a < b && space(s[a])) ++a;
  while (b > a && space(s[b - 1])) --b;
  return s.substr(a, b - a);
}
bool at(const std::string& s, size_t p, const char* token) {
  const size_t n = std::strlen(token);
  return p + n <= s.size() && s.compare(p, n, token) == 0;
}
bool boundary(const std::string& s, size_t p) { return !p || space(s[p-1]) || s[p-1] == '|'; }
bool noteHeading(const std::string& s) {
  const auto k = key(s);
  return k == "references" || k == "notes" || k == "footnotes" || k == "external-links" || k == "other-websites";
}
}
std::string key(const std::string& value) {
  std::string out;
  out.reserve(std::min<size_t>(value.size(), 1024));
  bool pending = false;
  for (unsigned char c : value) {
    if (c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '_' || c == '-') {
      pending = !out.empty();
      continue;
    }
    if (pending) { out += '-'; pending = false; }
    out += (c >= 'A' && c <= 'Z') ? char(c + 32) : char(c);
  }
  return out;
}
std::string friendly(const std::string& value) {
  std::string result = value;
  for (char& c : result) if (c == '-' || c == '_') c = ' ';
  if (!result.empty() && result[0] >= 'a' && result[0] <= 'z') result[0] -= 32;
  return result;
}
std::string displayTitle(const std::string& articleKey, const std::string& text) {
  const size_t colon = text.find(':');
  if (colon > 0 && colon <= 512 && key(text.substr(0, colon)) == key(articleKey))
    return text.substr(0, colon);
  return friendly(articleKey);
}
void clean(std::string& text, const std::string& articleKey) {
  const size_t colon = text.find(':');
  if (colon > 0 && colon <= 512 && key(text.substr(0, colon)) == key(articleKey)) text.erase(0, colon + 1);
  // Remove ONLY unmistakable image-display switches, not the caption or an
  // assumed sentence boundary. Flattened packs do not retain caption endings.
  size_t write = 0;
  for (size_t read = 0; read < text.size();) {
    size_t skip = 0;
    if (boundary(text, read)) {
      for (const char* token : {"thumb|", "thumbnail|", "right|", "left|", "center|", "upright|", "frameless|", "frame|"})
        if (at(text, read, token)) { skip = std::strlen(token); break; }
      if (!skip) {
        size_t digits = read;
        while (digits < text.size() && digits - read < 5 && text[digits] >= '0' && text[digits] <= '9') ++digits;
        if (digits > read && at(text, digits, "px|")) skip = digits - read + 3;
      }
    }
    if (skip) { read += skip; continue; }
    char c = text[read++];
    if (c == '\v' || c == '\r') c = '\n';
    if (c == '\t') c = ' ';
    if (write && c == ' ' && text[write-1] == ' ') continue;
    text[write++] = c;
  }
  text.resize(write);
}
size_t utf8Length(const std::string& text, size_t p, size_t end) {
  if (p >= end || end > text.size()) return 0;
  const unsigned char c = text[p];
  size_t n = c < 0x80 ? 1 : (c >= 0xc2 && c <= 0xdf ? 2 : (c >= 0xe0 && c <= 0xef ? 3 : (c >= 0xf0 && c <= 0xf4 ? 4 : 0)));
  if (!n || n > end - p) return 0;
  for (size_t i = 1; i < n; ++i) if ((static_cast<unsigned char>(text[p+i]) & 0xc0) != 0x80) return 0;
  if (n >= 3) {
    const unsigned char b = text[p+1];
    if ((c == 0xe0 && b < 0xa0) || (c == 0xed && b >= 0xa0) || (c == 0xf0 && b < 0x90) || (c == 0xf4 && b >= 0x90)) return 0;
  }
  return n;
}
bool citation(const char* text, size_t p, size_t& end) {
  if (text[p] != '[') return false;
  size_t i = p + 1, digits = 0;
  while (digits < 5 && text[i] >= '0' && text[i] <= '9') { ++i; ++digits; }
  if (!digits || text[i] != ']') return false;
  end = i + 1;
  return true;
}
void Document::build(const std::string& text, bool readingView) {
  count_ = 0;
  size_t pos = 0;
  bool notes = false;
  while (pos < text.size() && count_ < blocks_.size()) {
    while (pos < text.size() && space(text[pos])) ++pos;
    if (pos == text.size()) break;
    size_t end = text.find_first_of("\n\v", pos);
    if (end == std::string::npos) end = text.size();
    size_t begin = pos, visibleEnd = end;
    Kind kind = Kind::Body;
    if (readingView) {
      // Recognize explicit headings only. Never invent headings for an excerpt.
      if (end - pos > 4 && text.compare(pos, 2, "==") == 0) {
        while (begin < end && text[begin] == '=') ++begin;
        while (visibleEnd > begin && text[visibleEnd-1] == '=') --visibleEnd;
        while (begin < visibleEnd && space(text[begin])) ++begin;
        while (visibleEnd > begin && space(text[visibleEnd-1])) --visibleEnd;
        if (begin < visibleEnd) { kind = Kind::Heading; notes = noteHeading(text.substr(begin, visibleEnd-begin)); }
      } else if (end - pos < 80 && noteHeading(trim(text.substr(pos, end-pos)))) {
        notes = true; kind = Kind::Heading;
      } else if (notes || (end - pos < 360 && (at(text, pos, "[Image]") || at(text, pos, "Caption:") || at(text, pos, "File:")))) kind = Kind::Note;
      // A long flattened excerpt receives visual paragraph breaks at sentence
      // boundaries. No words are removed and these are not source paragraphs.
      if (kind == Kind::Body && end - begin > 520) {
        for (size_t p = begin + 360; p + 2 < end; ++p) {
          if ((text[p] == '.' || text[p] == '?' || text[p] == '!') && text[p+1] == ' ' &&
              (static_cast<unsigned char>(text[p+2]) >= 'A' && static_cast<unsigned char>(text[p+2]) <= 'Z')) {
            end = visibleEnd = p + 1; break;
          }
        }
      }
    }
    if (count_ + 1 == blocks_.size()) { visibleEnd = end = text.size(); kind = Kind::Body; }
    if (visibleEnd > begin) blocks_[count_++] = {uint32_t(begin), uint32_t(visibleEnd), kind};
    pos = end;
  }
}
}  // namespace WikiText
