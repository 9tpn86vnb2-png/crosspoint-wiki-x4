from pathlib import Path
cpp=Path('src/activities/wiki/WikiArchive.cpp').read_text()
hdr=Path('src/activities/wiki/WikiArchive.h').read_text()
ini=Path('platformio.local.ini').read_text()
checks={
 'version 4.4.1': '1.6.0-wiki-4.4.1' in ini,
 'Wiki X4 exceptions enabled': '-fexceptions' in ini and '-fno-exceptions' in ini.split('build_unflags =',1)[1].split('build_flags =',1)[0],
 '32KiB XML body cap': 'XML_MAX_TEXT = 32768' in hdr,
 'reference count budget': 'XML_MAX_REFERENCES = 24' in hdr,
 'reference bytes budget': 'XML_MAX_REFERENCE_BYTES = 1024' in hdr,
 'table count budget': 'TABLE_CAPTURE_MAX_TABLES = 8' in cpp,
 'table row budget': 'TABLE_CAPTURE_MAX_ROWS = 128' in cpp,
 'table cell budget': 'TABLE_CAPTURE_MAX_CELLS = 256' in cpp,
 'table byte budget': 'TABLE_CAPTURE_MAX_CELL_BYTES = 8192' in cpp,
 'bad alloc protected': 'catch(const std::bad_alloc&)' in cpp,
 'length error protected': 'catch(const std::length_error&)' in cpp,
 'heap diagnostics': 'heap_caps_get_largest_free_block' in cpp and '[WIKI XML]' in cpp,
 'move captured body': 'simplifyWikitext(std::move(text),truncated,&result)' in cpp,
 'conditional table normalization': 'if (source.find("{|" ) != std::string::npos) source = normalizeTableSource(source, semantic);' in cpp,
 'in-place whitespace cleanup': 'compactWhitespaceInPlace(clean);' in cpp,
 'move reference metadata': 'semantic->references=std::move(refs);' in cpp,
 'readable OOM fallback': 'Article too complex for available X4 memory.' in cpp,
 'header contains declarations only': 'WikiArchive::simplifyWikitext' not in hdr and hdr.rstrip().endswith('};'),
}
failed=[k for k,v in checks.items() if not v]
if failed: raise SystemExit('4.4.1 XML memory contracts failed: '+', '.join(failed))
print(f'{len(checks)} Wiki 4.4.1 XML memory contracts passed.')
for forbidden in ['const std::string source = normalizeTableSource(rawSource, semantic);','std::string clean; clean.reserve(out.size());','semantic->references=refs;','simplifyWikitext(text,truncated,&result)']:
    if forbidden in cpp: raise SystemExit('forbidden old peak-memory pattern remains: '+forbidden)
print('4 peak-memory anti-regression guards passed.')
