#include "WikiText.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>

int main() {
  using namespace WikiText;
  size_t end = 0;
  uint8_t toggle = 0;

  const char linkMarker[] = {char(LINK_MARKER), 'x', 0};
  assert(inlineStyleMarker(linkMarker, 0, 2, end, toggle));
  assert(end == 1 && toggle == Link);

  std::string rich = "Plain ";
  rich.push_back(char(LINK_MARKER));
  rich += "linked ";
  rich += "''italic''";
  rich.push_back(char(LINK_MARKER));
  rich += " end";

  char plain[128];
  stripInlineStyles(rich.c_str(), plain, sizeof(plain));
  assert(std::string(plain) == "Plain linked italic end");

  const auto mask = inlineStyleMask(rich.c_str(), rich.size(), Regular);
  assert(mask & (1u << Regular));
  assert(mask & (1u << Italic));

  char wrapped[128];
  const size_t next = wrap(rich, 0, rich.size(), 200, wrapped, sizeof(wrapped),
      [](char* s) {
        char visible[128];
        stripInlineStyles(s, visible, sizeof(visible));
        return int(std::strlen(visible));
      });
  assert(next == rich.size());
  assert(std::strchr(wrapped, char(LINK_MARKER)) != nullptr);
  stripInlineStyles(wrapped, plain, sizeof(plain));
  assert(std::string(plain) == "Plain linked italic end");

  std::cout << "Wiki 4.3 link-marker/wrapping host checks passed.\n";
  return 0;
}
