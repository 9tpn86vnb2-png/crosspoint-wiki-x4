#!/usr/bin/env python3
from pathlib import Path
R=Path('.')
def edit(p,a,b):
 f=R/p;s=f.read_text();assert s.count(a)==1,(p,a[:100],s.count(a));f.write_text(s.replace(a,b,1))
p='lib/Epub/Epub/Page.cpp'
edit(p,"  // Images don't use fontId or text rendering\n  imageBlock->render",'''  // Orientation-aware exact geometry: avoid SD decode for an off-strip image.
  if(!imageBlock||!renderer.glyphIntersectsStrip(xPos+xOffset,yPos+yOffset,
       xPos+xOffset+imageBlock->getWidth()-1,yPos+yOffset+imageBlock->getHeight()-1))return;
  imageBlock->render''')
edit(p,'  renderer.drawLine(xPos + xOffset, yPos + yOffset, xPos + xOffset + width - 1, yPos + yOffset, thickness, true);','''  if(!renderer.glyphIntersectsStrip(xPos+xOffset-thickness,yPos+yOffset-thickness,
      xPos+xOffset+width+thickness,yPos+yOffset+thickness))return;
  renderer.drawLine(xPos + xOffset, yPos + yOffset, xPos + xOffset + width - 1, yPos + yOffset, thickness, true);''')
edit(p,'  if (width < 2 || height == 0 || columnCount < 2 || thickness == 0) return;','''  if (width < 2 || height == 0 || columnCount < 2 || thickness == 0) return;
  if(!renderer.glyphIntersectsStrip(xPos+xOffset-thickness,yPos+yOffset-thickness,
      xPos+xOffset+width+thickness,yPos+yOffset+height+thickness))return;''')
p='lib/Epub/Epub/blocks/TextBlock.h'
edit(p,'  std::vector<std::string> rubyTexts;','''  std::vector<std::string> rubyTexts;
  // Runtime-only direction bytes follow text in the SAME arena allocation;
  // arenaSize and the on-SD representation intentionally remain unchanged.
  uint8_t* preparedDirections=nullptr;
  mutable std::unique_ptr<int[]> preparedRubyOffsets;
  mutable int preparedRubyFont=-1;''')
edit(p,'  void setBlockStyle(const BlockStyle& blockStyle) { this->blockStyle = blockStyle; }','''  void setBlockStyle(const BlockStyle& blockStyle) {
    this->blockStyle=blockStyle;
    if(preparedDirections)for(uint16_t i=0;i<numWords;++i)preparedDirections[i]=255;
    preparedRubyFont=-1;
  }''')
p=R/'lib/Epub/Epub/blocks/TextBlock.cpp';s=p.read_text()
s=s.replace('  arena = makeUniqueNoThrow<uint8_t[]>(size);','  arena = makeUniqueNoThrow<uint8_t[]>(size + numWords);',1)
s=s.replace('    block->arena = makeUniqueNoThrow<uint8_t[]>(size);','    block->arena = makeUniqueNoThrow<uint8_t[]>(size + wc);',1)
s=s.replace('  textArr = reinterpret_cast<const char*>(base + off);','''  textArr = reinterpret_cast<const char*>(base + off);
  preparedDirections=base+off+textBytes;
  std::memset(preparedDirections,255,wc);''',1)
s=s.replace('  const bool scanning = renderer.isFontCacheScanning();','''  const auto direction=[&](uint16_t i) {
    if(preparedDirections&&preparedDirections[i]==255)
      preparedDirections[i]=static_cast<uint8_t>(BidiUtils::detectParagraphLevel(wordText(i),blockStyle.isRtl?1:0));
    return static_cast<BidiUtils::BidiBaseDir>(preparedDirections?preparedDirections[i]:
        BidiUtils::detectParagraphLevel(wordText(i),blockStyle.isRtl?1:0));
  };
  const bool scanning = renderer.isFontCacheScanning();''',1)
a=s.index('  // Resolve ruby positions.');b=s.index('\n  struct DecorationLineTracker',a)
s=s[:a]+'''  const bool blockHasRuby=hasRuby();
  const auto rubyOffset=[&](uint16_t i) {
    int count=1;
    while(i+count<numWords&&(wordStyle(i+count)&EpdFontFamily::RUBY_CONTINUE))++count;
    int width=0;for(int k=0;k<count;++k)width+=renderer.getTextAdvanceX(fontId,wordText(i+k),wordStyle(i+k));
    const int rubyWidth=renderer.getTextAdvanceX(fontId,rubyTexts[i].c_str(),EpdFontFamily::SUP);
    return int(xposArr[i])-(rubyWidth-width)/2;
  };
  if(blockHasRuby&&(!preparedRubyOffsets||preparedRubyFont!=fontId)) {
    if(!preparedRubyOffsets)preparedRubyOffsets.reset(new(std::nothrow)int[numWords]);
    if(preparedRubyOffsets) {
      for(uint16_t i=0;i<numWords;++i)
        preparedRubyOffsets[i]=i<rubyTexts.size()&&!rubyTexts[i].empty()&&!(wordStyle(i)&EpdFontFamily::RUBY_CONTINUE)?rubyOffset(i):0;
      preparedRubyFont=fontId;
    }
  }
'''+s[b:]
s=s.replace('''    const auto baseDir =
        static_cast<BidiUtils::BidiBaseDir>(BidiUtils::detectParagraphLevel(word, blockStyle.isRtl ? 1 : 0));''','    const auto baseDir=direction(i);',1)
a='''      renderer.drawText(fontId, rubies[i].x, rubyY, rubies[i].text.c_str(), true, EpdFontFamily::SUP,
                        rubies[i].baseDir);''';assert s.count(a)==1
s=s.replace(a,'''      renderer.drawText(fontId,x+(preparedRubyOffsets?preparedRubyOffsets[i]:rubyOffset(i)),rubyY,
                        rubyTexts[i].c_str(),true,EpdFontFamily::SUP,direction(i));''')
assert 'rubies[' not in s
p.write_text(s)
print('4.6.3 rendering: exact off-strip geometry, same-arena bidi cache, cached relative ruby offsets, unchanged page serialization')
