#!/usr/bin/env python3
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]

BETA42_EXPECTED = {
  'src/activities/wiki/WikiArchive.cpp': 'ad6631123d29a430262798dffdb2857b1b7316897aadaf5ed9b256c59bb0211f',
  'src/activities/wiki/WikiText.cpp': 'dd084174b1c7bb0a9efae3df02706cc8b3c543cea19abf2c1e8338cc9e16b94a',
  'src/activities/wiki/WikiText.h': '8416d41ea9c98fbc47f2772991a25d7940ab173c04ede0baa6c286755deedc11',
  'src/activities/wiki/WikiActivity.cpp': '4a3f47005af7689028843c681b2dd55f5c7f122971651570d0ca669a2d17639c',
  'src/activities/wiki/WikiActivity.h': '5e792a7ecd28c75a851768e8faa53bfb330eb0a445a36a0a1bb3a256fa148f22',
  'platformio.local.ini': 'b2c60281af5b7dfdf6733a905e1ae36b6c4b8cc6234d475fed589a6d89c2258d',
  'WIKI_BETA42.md': 'dc6e5651d1ed893de73b0df9b1b074840010999ff173f1a904777f591a3d2852'
}
BETA43_EXPECTED = {
  'src/activities/wiki/WikiArchive.cpp': '8010acf4616c44fc2152f5c4bdff3699c4c42015995fd5e89745ea9196c85dcf',
  'src/activities/wiki/WikiText.cpp': 'de4ed0bcb8911f309c6c5ab673cd217d505fa3d188a408f2ba34326cef417c90',
  'src/activities/wiki/WikiText.h': 'e55928c3eb3b5a90848e2317d61b8fc0424e90a2be64264d7f19640046cbbf81',
  'src/activities/wiki/WikiActivity.cpp': '0c3005fac0aa04d93d74c1f1a7d4cbee9417334c6ba81cfb62f318739e47245e',
  'platformio.local.ini': '71dbf50953d4398e2941c169affd98d898b7d347629dfc611cb92c09cfd2e028',
  'WIKI_BETA43.md': '03a28d5143720a0ff24ca71c22d29f197cf5f87eccc3314d67936b87f20e3e03'
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(mapping, label):
    for name, expected in mapping.items():
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f'{label}: missing {name}')
        actual = sha(path)
        if actual != expected:
            raise SystemExit(f'{label}: {name} {actual} != {expected}')

def replace_exact(path, old, new, expected=1):
    p = ROOT / path
    s = p.read_text()
    actual = s.count(old)
    if actual != expected:
        raise SystemExit(f'Wiki 4.3 patch anchor mismatch: {path}: {actual} occurrences, expected {expected}')
    p.write_text(s.replace(old, new, expected))

def replace_once(path, old, new):
    replace_exact(path, old, new, 1)


def main():
    verify(BETA42_EXPECTED, 'Wiki 4.2 input fingerprint mismatch')

    replace_once('src/activities/wiki/WikiArchive.cpp',
        '#include "WikiArchive.h"\n#include <InflateReader.h>',
        '#include "WikiArchive.h"\n#include "WikiText.h"\n#include <InflateReader.h>')
    replace_once('src/activities/wiki/WikiArchive.cpp',
        'size_t e=source.find("]]",i+2); if(e!=std::string::npos&&e-i<4096){std::string inner=source.substr(i+2,e-i-2);std::string low=folded(inner);if(low.rfind("file:",0)!=0&&low.rfind("image:",0)!=0&&low.rfind("category:",0)!=0){size_t pipe=inner.find_last_of(\'|\');std::string label=pipe==std::string::npos?inner:inner.substr(pipe+1);size_t hash=label.find(\'#\');if(hash!=std::string::npos&&pipe==std::string::npos)label.resize(hash);appendText(trimCopy(label));}i=e+2;lineStart=false;continue;}',
        'size_t e=source.find("]]",i+2); if(e!=std::string::npos&&e-i<4096){std::string inner=source.substr(i+2,e-i-2);std::string low=folded(inner);if(low.rfind("file:",0)!=0&&low.rfind("image:",0)!=0&&low.rfind("category:",0)!=0){size_t pipe=inner.find_last_of(\'|\');std::string label=pipe==std::string::npos?inner:inner.substr(pipe+1);size_t hash=label.find(\'#\');if(hash!=std::string::npos&&pipe==std::string::npos)label.resize(hash);label=trimCopy(label);if(!label.empty()){append(char(WikiText::LINK_MARKER));appendText(label);append(char(WikiText::LINK_MARKER));}}i=e+2;lineStart=false;continue;}')

    replace_once('src/activities/wiki/WikiText.h',
        'enum InlineStyle : uint8_t { Regular = 0, Bold = 1, Italic = 2 };',
        'enum InlineStyle : uint8_t { Regular = 0, Bold = 1, Italic = 2, Link = 4 };\nstatic constexpr unsigned char LINK_MARKER = 0x1d;')
    replace_once('src/activities/wiki/WikiText.h',
        '// uses Bold/Italic bits. Runs of five quotes toggle both; three toggle bold;\n// two toggle italic. Longer runs are consumed in those canonical groups.',
        '// uses Bold/Italic bits plus Link for an internal MediaWiki article reference.\n// Runs of five quotes toggle both; three toggle bold; two toggle italic.\n// LINK_MARKER toggles link-underlining state and never consumes glyph width.')
    replace_once('src/activities/wiki/WikiText.h',
        "if (!n || c < 32) output[used++] = n ? ' ' : '?';",
        "if (!n) output[used++] = '?';\n    else if (c < 32 && c != LINK_MARKER) output[used++] = ' ';\n    else")
    replace_once('src/activities/wiki/WikiText.h',
        "else\n    else { for (size_t k = 0; k < n; ++k) output[used++] = text[pos + k]; }",
        "else { for (size_t k = 0; k < n; ++k) output[used++] = text[pos + k]; }")

    replace_once('src/activities/wiki/WikiText.cpp',
        "if (!text || p >= end || text[p] != '\\'') return false;",
        "if (!text || p >= end) return false;\n  if (static_cast<unsigned char>(text[p]) == LINK_MARKER) {\n    markerEnd = p + 1; toggleMask = Link; return true;\n  }\n  if (text[p] != '\\'') return false;")
    replace_once('src/activities/wiki/WikiText.cpp',
        'uint8_t style = initialStyle & (Bold | Italic);\n  uint8_t mask = uint8_t(1u << style);',
        'uint8_t style = initialStyle & (Bold | Italic | Link);\n  uint8_t mask = uint8_t(1u << (style & (Bold | Italic)));')
    replace_once('src/activities/wiki/WikiText.cpp',
        'style ^= toggle; mask |= uint8_t(1u << style); p = markerEnd; continue;',
        'style ^= toggle; mask |= uint8_t(1u << (style & (Bold | Italic))); p = markerEnd; continue;')

    replace_exact('src/activities/wiki/WikiActivity.cpp',
        'uint8_t style=startStyle & (WikiText::Bold | WikiText::Italic);',
        'uint8_t style=startStyle & (WikiText::Bold | WikiText::Italic | WikiText::Link);', 2)
    replace_once('src/activities/wiki/WikiActivity.cpp',
        'renderer.drawText(font,x,y,line+begin,true,fontStyle(style));\n    x+=renderer.getTextWidth(font,line+begin,fontStyle(style));',
        'const int runWidth=renderer.getTextWidth(font,line+begin,fontStyle(style));\n    renderer.drawText(font,x,y,line+begin,true,fontStyle(style));\n    if ((style & WikiText::Link) && runWidth > 0) {\n      const int underlineY=y+std::max(1,renderer.getTextHeight(font)-1);\n      renderer.drawLine(x,underlineY,x+runWidth-1,underlineY);\n    }\n    x+=runWidth;')
    replace_once('src/activities/wiki/WikiActivity.cpp',
        'const int extra=width-wordWidth;\n    // Avoid huge rivers in short lines. A final paragraph line is never stretched.\n    if (count>1 && extra>=(count-1)*space && extra<=(count-1)*space*3) {',
        'const int naturalGaps=std::max(0,count-1)*space;\n    const int stretch=width-wordWidth-naturalGaps;\n    // Wiki 4.2 allowed gaps up to 3x the natural space width. Real MediaWiki\n    // text with long emphasized/link labels made that visibly uneven. Keep\n    // justification only when a line has enough words and needs <=75% stretch.\n    if (count>=4 && stretch>=0 && stretch*4<=naturalGaps*3) {')
    replace_once('src/activities/wiki/WikiActivity.cpp',
        'const int pos=x+drawn+(index*extra)/(count-1);',
        'const int pos=x+drawn+index*space+(count>1 ? (index*stretch)/(count-1) : 0);')

    replace_exact('platformio.local.ini', '1.6.0-wiki-4.2', '1.6.0-wiki-4.3', 2)

    verify(BETA43_EXPECTED, 'Wiki 4.3 production fingerprint mismatch')
    (ROOT / 'wiki-beta43-reviewed-source.json').write_text(json.dumps(BETA43_EXPECTED, indent=2) + '\n')
    print('Applied Wiki 4.3 spacing/link typography patch and verified', len(BETA43_EXPECTED), 'production fingerprints.')

if __name__ == '__main__':
    main()
