#!/usr/bin/env python3
from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'4.5.0: {label} anchor not found')
    return text.replace(old, new, 1)

# Add one tiny piece of row state. We keep the renderer streaming: no whole-table buffer.
header = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.h')
h = header.read_text()
h = replace_once(
    h,
    '  size_t tableCellTextBytes = 0;\n',
    '  size_t tableCellTextBytes = 0;\n  size_t tableStackedCellIndex = 0;\n',
    'table stacked cell state',
)
header.write_text(h)

parser = Path('lib/Epub/Epub/parsers/ChapterHtmlSlimParser.cpp')
s = parser.read_text()

s = replace_once(
    s,
    '''constexpr int16_t TABLE_CELL_HORIZONTAL_PADDING = 4;\nconstexpr int16_t TABLE_ROW_SEPARATOR_GAP = 4;\nconstexpr uint8_t TABLE_ROW_SEPARATOR_THICKNESS = 1;\nconstexpr int16_t TABLE_MIN_CELL_WIDTH_LINE_HEIGHTS = 3;\n''',
    '''constexpr int16_t TABLE_CELL_HORIZONTAL_PADDING = 4;\nconstexpr int16_t TABLE_ROW_SEPARATOR_GAP = 4;\nconstexpr uint8_t TABLE_ROW_SEPARATOR_THICKNESS = 1;\nconstexpr int16_t TABLE_MIN_CELL_WIDTH_LINE_HEIGHTS = 3;\nconstexpr int16_t TABLE_STACKED_SECONDARY_INDENT = 12;\n''',
    'table constants',
)

structural = '''bool isTableStructuralTag(const char* name) {\n  return strcmp(name, "table") == 0 || strcmp(name, "tr") == 0 || strcmp(name, "td") == 0 || strcmp(name, "th") == 0;\n}\n'''
structural_plus = structural + '''\nvoid indentStackedTableCell(ParsedText* cell, const size_t cellIndex) {\n  if (!cell || cellIndex == 0) return;\n  auto style = cell->getBlockStyle();\n  style.marginLeft = static_cast<int16_t>(style.marginLeft + TABLE_STACKED_SECONDARY_INDENT);\n  style.paddingLeft = 0;\n  style.textIndent = 0;\n  style.textIndentDefined = false;\n  cell->setBlockStyle(style);\n}\n'''
s = replace_once(s, structural, structural_plus, 'stacked table style helper')

old = '''void ChapterHtmlSlimParser::fallbackTableRowToStacked() {\n  if (tableRowStacked) {\n    return;\n  }\n\n  auto activeCell = std::move(currentTextBlock);\n  tableRowStacked = true;\n\n  for (auto& cell : tableRowCells) {\n    currentTextBlock = std::move(cell);\n    wordsExtractedInBlock = 0;\n    if (currentTextBlock && !currentTextBlock->isEmpty()) {\n      makePages();\n    }\n  }\n  tableRowCells.clear();\n  currentTextBlock = std::move(activeCell);\n  wordsExtractedInBlock = 0;\n}\n'''
new = '''void ChapterHtmlSlimParser::fallbackTableRowToStacked() {\n  if (tableRowStacked) {\n    return;\n  }\n\n  auto activeCell = std::move(currentTextBlock);\n  tableRowStacked = true;\n\n  size_t cellIndex = 0;\n  for (auto& cell : tableRowCells) {\n    currentTextBlock = std::move(cell);\n    wordsExtractedInBlock = 0;\n    if (currentTextBlock && !currentTextBlock->isEmpty()) {\n      indentStackedTableCell(currentTextBlock.get(), cellIndex);\n      makePages();\n    }\n    cellIndex++;\n  }\n  tableRowCells.clear();\n  tableStackedCellIndex = cellIndex;\n  currentTextBlock = std::move(activeCell);\n  wordsExtractedInBlock = 0;\n}\n'''
s = replace_once(s, old, new, 'stacked row fallback')

old = '''  if (tableRowStacked) {\n    wordsExtractedInBlock = 0;\n    if (!currentTextBlock->isEmpty()) {\n      makePages();\n    }\n    currentTextBlock.reset();\n    return;\n  }\n'''
new = '''  if (tableRowStacked) {\n    wordsExtractedInBlock = 0;\n    if (!currentTextBlock->isEmpty()) {\n      indentStackedTableCell(currentTextBlock.get(), tableStackedCellIndex);\n      makePages();\n    }\n    currentTextBlock.reset();\n    tableStackedCellIndex++;\n    return;\n  }\n'''
s = replace_once(s, old, new, 'stacked close cell')

old = '''  if (tableRowCells.empty()) {\n    if (tableRowStacked) {\n      addTableRowSeparator();\n    }\n    tableRowStacked = false;\n    return;\n  }\n\n  const int16_t lineHeight =\n'''
new = '''  if (tableRowCells.empty()) {\n    if (tableRowStacked) {\n      addTableRowSeparator();\n    }\n    tableRowStacked = false;\n    tableStackedCellIndex = 0;\n    return;\n  }\n\n  // Calibre and other EPUB generators sometimes emit a leading row of empty <th>\n  // cells as a layout shim. It is not a visible row and should not consume e-ink space.\n  bool allCellsEmpty = true;\n  for (const auto& cell : tableRowCells) {\n    if (cell && !cell->isEmpty()) {\n      allCellsEmpty = false;\n      break;\n    }\n  }\n  if (allCellsEmpty) {\n    tableRowCells.clear();\n    tableRowStacked = false;\n    tableStackedCellIndex = 0;\n    return;\n  }\n\n  const int16_t lineHeight =\n'''
s = replace_once(s, old, new, 'empty table row suppression')

old = '''  const size_t columnCount = tableRowCells.size();\n  const uint16_t cellWidth = static_cast<uint16_t>(viewportWidth / columnCount);\n\n  // Keep enough width for a few glyphs while allowing ordinary three-column\n'''
new = '''  const size_t columnCount = tableRowCells.size();\n  const uint16_t cellWidth = static_cast<uint16_t>(viewportWidth / columnCount);\n\n  // On a 480px portrait display, prose-heavy 3/4-column cells become a wall of\n  // one- or two-word wraps. Keep compact data tabular, but turn narrative rows\n  // into structured full-width records. The source order and all text are preserved.\n  const size_t gridReadableWordLimit = columnCount >= 4 ? 14 : (columnCount == 3 ? 20 : MAX_GRID_TABLE_CELL_WORDS);\n  for (const auto& cell : tableRowCells) {\n    if (cell && cell->size() > gridReadableWordLimit) {\n      fallbackTableRowToStacked();\n      addTableRowSeparator();\n      tableRowStacked = false;\n      tableStackedCellIndex = 0;\n      return;\n    }\n  }\n\n  // Keep enough width for a few glyphs while allowing ordinary three-column\n'''
s = replace_once(s, old, new, 'readability fallback')

old = '''  addTableRowSeparator();\n  tableRowStacked = false;\n  clearLayoutLines();\n}\n'''
new = '''  addTableRowSeparator();\n  tableRowStacked = false;\n  tableStackedCellIndex = 0;\n  clearLayoutLines();\n}\n'''
s = replace_once(s, old, new, 'grid row cleanup')

old = '''    self->tableRowStacked = false;\n    self->tableRowRtl = cssStyle.hasDirection() && cssStyle.direction == CssTextDirection::Rtl;\n    self->tableRowsSpannedRemaining = 0;\n'''
new = '''    self->tableRowStacked = false;\n    self->tableStackedCellIndex = 0;\n    self->tableRowRtl = cssStyle.hasDirection() && cssStyle.direction == CssTextDirection::Rtl;\n    self->tableRowsSpannedRemaining = 0;\n'''
s = replace_once(s, old, new, 'table start state')

old = '''  if (self->tableDepth == 1 && strcmp(name, "tr") == 0) {\n    self->finishTableRow();\n'''
new = '''  if (self->tableDepth == 1 &&\n      (strcmp(name, "thead") == 0 || strcmp(name, "tbody") == 0 || strcmp(name, "tfoot") == 0 ||\n       strcmp(name, "colgroup") == 0 || strcmp(name, "col") == 0)) {\n    // Structural wrappers carry no visible text of their own. Keeping them out of\n    // ordinary block-style handling prevents CSS display:table metadata from\n    // disturbing the bounded row renderer.\n    self->depth += 1;\n    return;\n  }\n\n  if (self->tableDepth == 1 && strcmp(name, "tr") == 0) {\n    self->finishTableRow();\n'''
s = replace_once(s, old, new, 'table section wrappers')

old = '''    self->currentTextBlock.reset();\n    self->tableRowStacked = self->tableRowsSpannedRemaining > 0;\n    self->tableRowRtl = cssStyle.hasDirection() && cssStyle.direction == CssTextDirection::Rtl;\n'''
new = '''    self->currentTextBlock.reset();\n    self->tableRowStacked = self->tableRowsSpannedRemaining > 0;\n    self->tableStackedCellIndex = 0;\n    self->tableRowRtl = cssStyle.hasDirection() && cssStyle.direction == CssTextDirection::Rtl;\n'''
s = replace_once(s, old, new, 'table row start state')

old = '''    self->tableRowStacked = false;\n    self->tableRowsSpannedRemaining = 0;\n    self->tableCellTextBytes = 0;\n'''
new = '''    self->tableRowStacked = false;\n    self->tableStackedCellIndex = 0;\n    self->tableRowsSpannedRemaining = 0;\n    self->tableCellTextBytes = 0;\n'''
s = replace_once(s, old, new, 'table end state')

parser.write_text(s)

# Version bump plus exception scoping. 4.4.1 enabled exceptions globally to make
# the XML article allocation boundary catchable; 4.5.0 restores -fno-exceptions
# globally and opts only WikiArchive.cpp back in through a build middleware.
ini = Path('platformio.local.ini')
i = ini.read_text()
if '1.6.0-wiki-4.4.2' not in i:
    raise SystemExit('4.5.0: expected 4.4.2 version not found')
i = i.replace('1.6.0-wiki-4.4.2', '1.6.0-wiki-4.5.0')
i = i.replace('; Wiki 4.4.1 catches std::bad_alloc/length_error at the XML article boundary.\n; The base profile disables C++ exceptions globally, so this X4 Wiki profile\n; explicitly removes that flag and re-enables exceptions for its translation units.\n', '; Wiki XML allocation failures are caught in WikiArchive.cpp.\n; 4.5.0 keeps the normal no-exception firmware profile everywhere else and\n; enables exceptions only for that translation unit via build middleware.\n')
i = replace_once(
    i,
    '''build_unflags =\n  -std=gnu++11\n  -fno-exceptions\n''',
    '''build_unflags =\n  -std=gnu++11\nextra_scripts =\n  ${base.extra_scripts}\n  pre:.github/wiki450_scoped_exceptions.py\n''',
    'global exception unflag',
)
i = i.replace('  -fexceptions\n', '', 1)
ini.write_text(i)

print('Wiki 4.5.0 streaming EPUB table renderer + scoped-exception optimization applied.')
