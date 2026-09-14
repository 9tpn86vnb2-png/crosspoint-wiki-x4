#!/usr/bin/env python3
from pathlib import Path

parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp')
text = parser.read_text()

needle = '''bool isTableStructuralTag(const char* name) {\n  return strcmp(name, "table") == 0 || strcmp(name, "tr") == 0 || strcmp(name, "td") == 0 || strcmp(name, "th") == 0;\n}\n'''
insert = needle + r'''

bool tableHelperClassTokenEquals(const std::string& classes, const char* token) {
  size_t pos = 0;
  const size_t tokenLen = strlen(token);
  while (pos < classes.size()) {
    while (pos < classes.size() && isWhitespace(classes[pos])) pos++;
    const size_t start = pos;
    while (pos < classes.size() && !isWhitespace(classes[pos])) pos++;
    const size_t len = pos - start;
    if (len != tokenLen) continue;
    bool matches = true;
    for (size_t i = 0; i < len; i++) {
      char a = classes[start + i];
      char b = token[i];
      if (a >= 'A' && a <= 'Z') a = static_cast<char>(a + ('a' - 'A'));
      if (b >= 'A' && b <= 'Z') b = static_cast<char>(b + ('a' - 'A'));
      if (a != b) {
        matches = false;
        break;
      }
    }
    if (matches) return true;
  }
  return false;
}

bool isAccessibilityOnlyClass(const std::string& classes) {
  static constexpr const char* HIDDEN_CLASSES[] = {
      "sr-only",          "sr_only",          "sr-only-focusable", "screen-reader-only",
      "screenreader-only", "screen-reader-text", "visually-hidden",   "visuallyhidden",
      "a11y-hidden",      "assistive-text",    "accessibility-only"};
  for (const char* token : HIDDEN_CLASSES) {
    if (tableHelperClassTokenEquals(classes, token)) return true;
  }
  return false;
}

bool inlineStyleHidesElement(const std::string& style) {
  if (style.empty()) return false;
  std::string compact;
  compact.reserve(style.size());
  for (char c : style) {
    if (isWhitespace(c)) continue;
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + ('a' - 'A'));
    compact.push_back(c);
  }
  return compact.find("display:none") != std::string::npos ||
         compact.find("visibility:hidden") != std::string::npos ||
         compact.find("visibility:collapse") != std::string::npos;
}
'''
if needle not in text:
    raise SystemExit('4.4.2: table structural helper anchor not found')
text = text.replace(needle, insert, 1)

needle = '''  std::string classAttr;\n  std::string styleAttr;\n  std::string dirAttr;\n'''
replacement = '''  std::string classAttr;\n  std::string styleAttr;\n  std::string dirAttr;\n  bool htmlHidden = false;\n  bool ariaHidden = false;\n'''
if needle not in text:
    raise SystemExit('4.4.2: attribute state anchor not found')
text = text.replace(needle, replacement, 1)

needle = '''      } else if (strcmp(atts[i], "dir") == 0) {\n        dirAttr = atts[i + 1];\n      }\n'''
replacement = '''      } else if (strcmp(atts[i], "dir") == 0) {\n        dirAttr = atts[i + 1];\n      } else if (strcmp(atts[i], "hidden") == 0) {\n        htmlHidden = true;\n      } else if (strcmp(atts[i], "aria-hidden") == 0 &&\n                 (strcasecmp(atts[i + 1], "true") == 0 || strcmp(atts[i + 1], "1") == 0)) {\n        ariaHidden = true;\n      }\n'''
if needle not in text:
    raise SystemExit('4.4.2: dir attribute anchor not found')
text = text.replace(needle, replacement, 1)

needle = '''  // Skip elements with display:none before all fast paths (tables, links, etc.).\n  if (cssStyle.hasDisplay() && cssStyle.display == CssDisplay::None) {\n'''
replacement = '''  // Visibility/accessibility semantics are not optional publisher styling.\n  // EPUB generators often keep table navigation labels in screen-reader-only wrappers;\n  // if publisher CSS is disabled those labels must still not enter normal reading text.\n  if (htmlHidden || ariaHidden || isAccessibilityOnlyClass(classAttr) || inlineStyleHidesElement(styleAttr)) {\n    self->skipUntilDepth = self->depth;\n    self->depth += 1;\n    return;\n  }\n\n  // Skip elements with display:none before all fast paths (tables, links, etc.).\n  if (cssStyle.hasDisplay() && cssStyle.display == CssDisplay::None) {\n'''
if needle not in text:
    raise SystemExit('4.4.2: display-none anchor not found')
text = text.replace(needle, replacement, 1)

needle = '''  const bool countVisibleOffsets = self->insideBody && self->nonVisibleTextDepth == 0 && !self->syntheticCharacterData;\n'''
replacement = '''  const bool countVisibleOffsets = self->insideBody && self->nonVisibleTextDepth == 0 && !self->syntheticCharacterData &&\n                                   !(self->skipUntilDepth < self->depth);\n'''
if needle not in text:
    raise SystemExit('4.4.2: visible-offset anchor not found')
text = text.replace(needle, replacement, 1)
parser.write_text(text)

ini = Path('platformio.local.ini')
ini_text = ini.read_text()
if '1.6.0-wiki-4.4.1' not in ini_text:
    raise SystemExit('4.4.2: expected 4.4.1 version not found in platformio.local.ini')
ini.write_text(ini_text.replace('1.6.0-wiki-4.4.1', '1.6.0-wiki-4.4.2'))

print('Wiki 4.4.2 EPUB helper-text suppression applied.')
