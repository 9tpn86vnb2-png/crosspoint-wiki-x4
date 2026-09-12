#include "WikiText.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>

int main() {
  using namespace WikiText;
  size_t end = 0;
  uint8_t toggle = 0;
  assert(inlineStyleMarker("''x", 0, 3, end, toggle) && end == 2 && toggle == Italic);
  assert(inlineStyleMarker("'''x", 0, 4, end, toggle) && end == 3 && toggle == Bold);
  assert(inlineStyleMarker("'''''x", 0, 6, end, toggle) && end == 5 && toggle == (Bold | Italic));
  assert(!inlineStyleMarker("'x", 0, 2, end, toggle));

  const char* mixed = "Plain ''italic'' '''bold''' '''''both''''' end";
  char plain[128];
  stripInlineStyles(mixed, plain, sizeof(plain));
  assert(std::string(plain) == "Plain italic bold both end");

  const auto mask = inlineStyleMask(mixed, std::strlen(mixed), Regular);
  assert(mask & (1u << Regular));
  assert(mask & (1u << Italic));
  assert(mask & (1u << Bold));
  assert(mask & (1u << (Bold | Italic)));

  const char* continuation = "word'' end";
  const auto continued = inlineStyleMask(continuation, std::strlen(continuation), Italic);
  assert(continued & (1u << Italic));
  assert(continued & (1u << Regular));

  Document d;
  d.build("== Level 2 ==\n=== Level 3 ===\n==== Level 4 ====\nBody", true);
  assert(d.count() == 4);
  assert(d.block(0).kind == Kind::Heading && d.block(0).level == 2);
  assert(d.block(1).kind == Kind::Heading && d.block(1).level == 3);
  assert(d.block(2).kind == Kind::Heading && d.block(2).level == 4);
  assert(d.block(3).kind == Kind::Body && d.block(3).level == 0);

  Cursor c;
  assert(c.style == Regular);
  std::cout << "Wiki 4.2 WikiText typography host checks passed.\n";
  return 0;
}
