#!/usr/bin/env python3
"""Differential production TextBlock tests; deterministic metrics/command sink, not a physical display."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
FLAGS=['-std=c++20','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie','-ffunction-sections','-fdata-sections','-Wl,--gc-sections']
GFX=r'''#pragma once
#include <EpdFontFamily.h>
#include <cstring>
#include <sstream>
#include <iomanip>
namespace BidiUtils { enum class BidiBaseDir : int8_t {AUTO=-1,LTR=0,RTL=1}; }
class GfxRenderer {
public:
 bool scanning=false; mutable std::ostringstream output;
 bool isFontCacheScanning()const{return scanning;}
 int getFontAscenderSize(int font)const{return 17+font;}
 int getTextAdvanceX(int font,const char* s,EpdFontFamily::Style style)const {int n=0;for(auto*p=(const unsigned char*)s;*p;++p)if((*p&0xc0)!=0x80)++n;return n*(font+3+int(style&3));}
 int getTextWidth(int font,const char*s,EpdFontFamily::Style style,BidiUtils::BidiBaseDir)const{return getTextAdvanceX(font,s,style);}
 void drawText(int f,int x,int y,const char*s,bool ink,EpdFontFamily::Style st,BidiUtils::BidiBaseDir dir)const {
 output<<"T "<<f<<' '<<x<<' '<<y<<' '<<ink<<' '<<int(st)<<' '<<int(dir)<<' ';
 for(auto*p=(const unsigned char*)s;*p;++p)output<<std::hex<<std::setw(2)<<std::setfill('0')<<int(*p);output<<std::dec<<'\n';
 }
 void drawLine(int a,int b,int c,int d,int thick,bool ink)const{output<<"L "<<a<<' '<<b<<' '<<c<<' '<<d<<' '<<thick<<' '<<ink<<'\n';}
};
'''
MAIN=r'''#include "lib/Epub/Epub/blocks/TextBlock.h"
#include <GfxRenderer.h>
#include <cassert>
#include <iostream>
#include <random>
int main(){
 using S=EpdFontFamily::Style;
 std::mt19937 random(463);
 const std::vector<std::string> pool={"alpha","world","123", "\xd7\x90\xd7\x91", "\xd8\xa8\xd8\xa7", "\xe6\x97\xa5", "\xe6\x9c\xac", "\xe2\x80\x83indent", "a\xcc\x81"};
 for(int trial=0;trial<500;++trial){
   const int n=1+random()%12;std::vector<std::string> words,ruby(n);std::vector<int16_t> positions;std::vector<S> styles;
   std::vector<uint8_t> boundaries(n,0);std::vector<uint16_t> suffix(n,0);BlockStyle blockStyle;
   blockStyle.isRtl=trial%2;blockStyle.directionDefined=trial%3;blockStyle.marginLeft=trial%7;
   for(int i=0;i<n;++i){words.push_back(pool[random()%pool.size()]);positions.push_back(i*43-5);styles.push_back(S(random()%64));
     if(words.back()=="alpha"&&trial%2){boundaries[i]=2;suffix[i]=12;}
     if(trial%3==0&&i%3==0)ruby[i]="annotation";
     if(trial%3==0&&i%3==1)styles[i]=S(styles[i]|EpdFontFamily::RUBY_CONTINUE);
   }
   TextBlock block(words,positions,styles,boundaries,suffix,blockStyle,ruby);assert(block.valid());
   for(int round=0;round<6;++round){GfxRenderer gfx;gfx.scanning=round==1;const int font=round<3?7:9;
     if(round==4){blockStyle.isRtl=!blockStyle.isRtl;block.setBlockStyle(blockStyle);}
     block.render(gfx,font,round*13-8,round*17+3);std::cout<<trial<<' '<<round<<'\n'<<gfx.output.str();
     auto output=Storage.open("/text",O_WRONLY|O_CREAT|O_TRUNC);assert(block.serialize(output));output.close();
     std::cout<<"SER ";for(uint8_t byte:*disk["/text"])std::cout<<std::hex<<std::setw(2)<<std::setfill('0')<<int(byte);std::cout<<std::dec<<'\n';
     auto input=Storage.open("/text",O_RDONLY);auto loaded=TextBlock::deserialize(input);assert(loaded&&loaded->valid());
     GfxRenderer after;after.scanning=gfx.scanning;loaded->render(after,font,round*13-8,round*17+3);assert(after.output.str()==gfx.output.str());
   }
 }
}
'''

def main():
 outputs=[];sources={}
 with tempfile.TemporaryDirectory(prefix='wiki463-text-') as tmp:
  W=Path(tmp)
  for version in ['baseline','candidate']:
   root=W/version;blocks=root/'lib/Epub/Epub/blocks';blocks.mkdir(parents=True);(root/'src').mkdir()
   for name in ['TextBlock.h','TextBlock.cpp']:
    src=R/'wiki463-baseline'/name if version=='baseline' else R/'lib/Epub/Epub/blocks'/name
    shutil.copyfile(src,blocks/name);sources[version+'/'+name]=hashlib.sha256(src.read_bytes()).hexdigest()
   for name in ['Block.h','BlockStyle.h']:shutil.copyfile(R/'lib/Epub/Epub/blocks'/name,blocks/name)
   shutil.copyfile(R/'src/fontIds.h',root/'src/fontIds.h')
   for name in ['HalStorage.h','Print.h','Arduino.h','Logging.h']:shutil.copyfile(R/'.github/wiki463_host'/name,root/name)
   (root/'GfxRenderer.h').write_text(GFX);(root/'test.cpp').write_text(MAIN)
   inc=['-I'+str(root)]+['-I'+str(R/'lib'/x) for x in ['EpdFont','Epub','Memory','MiniBidi','Utf8','Serialization']]
   obj=root/'bidi.o'
   subprocess.run(['gcc','-std=c11','-O1','-fsanitize=address,undefined','-fno-pie','-I'+str(R/'lib/MiniBidi'),'-c',str(R/'lib/MiniBidi/minibidi.c'),'-o',str(obj)],check=True)
   exe=root/'test'
   subprocess.run(['g++',*FLAGS,*inc,str(blocks/'TextBlock.cpp'),str(R/'lib/MiniBidi/BidiUtils.cpp'),str(R/'lib/Utf8/Utf8.cpp'),str(root/'test.cpp'),str(obj),'-o',str(exe)],check=True)
   outputs.append(subprocess.check_output([str(exe)],timeout=30))
 assert outputs[0]==outputs[1], 'Rendering commands or serialized bytes differ from the 4.6.2 baseline'
 report={'production_source_sha256':sources,'baseline_and_candidate_identical':True,'trials':500,'render_configurations':3000,'serialize_deserialize_roundtrips':3000,'output_sha256':hashlib.sha256(outputs[0]).hexdigest(),'sanitizers':['ASan','UBSan'],'font_metrics_and_display':'deterministic mock, not actual glyphs or hardware','production_textblock_and_bidi':'byte-identical source copies compiled separately'}
 (R/'wiki463-text-regression.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
