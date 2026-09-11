#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>

// Presentation helpers. All offsets refer to one bounded article string.
// Reflow is not an attempt to reconstruct sections missing from a WCDB pack.
namespace WikiText {
std::string key(const std::string& value);
std::string friendly(const std::string& value);
std::string displayTitle(const std::string& key, const std::string& text);
void clean(std::string& text, const std::string& articleKey);
size_t utf8Length(const std::string& text, size_t offset, size_t end);
bool citation(const char* text, size_t offset, size_t& end);
enum class Kind : uint8_t { Body, Heading, Note };
struct Block { uint32_t begin = 0, end = 0; Kind kind = Kind::Body; };
struct Cursor { uint32_t offset = 0; uint16_t block = 0; };
class Document {
 public:
  void build(const std::string& text, bool readingView);
  size_t count() const { return count_; }
  const Block& block(size_t i) const { return blocks_[i]; }
 private:
  std::array<Block, 256> blocks_{};
  size_t count_ = 0;
};

// Fixed-size UTF-8 wrapping. Oversized glyphs still consume input; invalid
// sequences become '?' rather than stalling or splitting a valid character.
template <class Measure>
size_t wrap(const std::string& text, size_t from, size_t end, int width,
            char* output, size_t capacity, Measure measure) {
  end = end < text.size() ? end : text.size();
  from = from < end ? from : end;
  if (!capacity) return from;
  output[0] = 0;
  size_t pos = from, used = 0, breakInput = from, breakOutput = 0;
  bool haveBreak = false;
  while (pos < end && (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\r')) ++pos;
  while (pos < end) {
    const unsigned char c = static_cast<unsigned char>(text[pos]);
    const size_t n = utf8Length(text, pos, end);
    const size_t bytes = n ? n : 1;
    if (used + bytes >= capacity) {
      if (haveBreak) { output[breakOutput] = 0; return breakInput; }
      output[used] = 0;
      return pos > from ? pos : from + bytes;
    }
    const size_t previous = used;
    if (!n || c < 32) output[used++] = n ? ' ' : '?';
    else { for (size_t k = 0; k < n; ++k) output[used++] = text[pos + k]; }
    output[used] = 0;
    if (measure(output) > width && previous > 0) {
      if (haveBreak) { output[breakOutput] = 0; return breakInput; }
      output[previous] = 0;
      return pos;
    }
    pos += bytes;
    if (c == ' ' || c == '\t') { haveBreak = true; breakInput = pos; breakOutput = previous; }
  }
  output[used] = 0;
  return pos;
}
}  // namespace WikiText
