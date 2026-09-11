#!/usr/bin/env python3
"""Compile the real beta 2 UI/text/bookmark/archive code with host adapters.
Not an ESP32 or display emulator. Uses fault-injected host SD and test fonts.
"""
from pathlib import Path
import shutil, subprocess, sys
import wiki_host_tests
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'wiki-beta2-tests'
S=WORK/'stubs'

def main():
    S.mkdir(parents=True,exist_ok=True)
    for d in ['activities/util','components','activities']: (S/d).mkdir(parents=True,exist_ok=True)
    (S/'Arduino.h').write_text('#pragma once\ninline void delay(unsigned) {}\n')
    (S/'Icon.h').write_text('#pragma once\n#include <cstdint>\nnamespace freeink { struct Icon {uint16_t w,h;int16_t opticalCenterY;const uint8_t* bits;}; }\n')
    (S/'Preferences.h').write_text(r'''#pragma once
#include <map>
#include <string>
class Preferences {
 inline static std::map<std::string,unsigned> values;
 public:
 bool begin(const char*,bool) {return true;}
 unsigned char getUChar(const char* key,unsigned char fallback) {return values.count(key)?values[key]:fallback;}
 bool getBool(const char* key,bool fallback) {return values.count(key)?bool(values[key]):fallback;}
 void putUChar(const char* key,unsigned char v){values[key]=v;}
 void putBool(const char* key,bool v){values[key]=v;}
 void end(){}
};
''')
    (S/'HalStorage.h').write_text(r'''#pragma once
#include <cstdint>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <algorithm>
inline std::string hostRoot;
inline long hostWriteBudget=-1;
class HalFile {
 std::shared_ptr<std::fstream> file;
 bool writing=false;
 public:
 HalFile()=default;
 HalFile(const std::string& path,int flags) {
  writing=(flags&O_WRONLY)!=0;
  auto mode=std::ios::binary|(writing?std::ios::out:std::ios::in);
  if(flags&O_TRUNC) mode|=std::ios::trunc;
  auto p=std::make_shared<std::fstream>(path,mode);
  if(p->is_open()) file=std::move(p);
 }
 explicit operator bool() const{return bool(file)&&file->is_open();}
 size_t size() const {if(!file)return 0;auto old=file->tellg();file->seekg(0,std::ios::end);auto end=file->tellg();file->seekg(old);return size_t(end);}
 bool seek(uint64_t p){if(!file)return false;file->clear();file->seekg(p);return bool(*file);}
 int read(void* out,size_t n){if(!file)return -1;file->read(static_cast<char*>(out),n);return int(file->gcount());}
 size_t write(const uint8_t* data,size_t n){if(!file)return 0;if(hostWriteBudget>=0)n=std::min<size_t>(n,hostWriteBudget);file->write(reinterpret_cast<const char*>(data),n);if(hostWriteBudget>=0)hostWriteBudget-=n;return *file?n:0;}
 void flush(){if(file)file->flush();}
 bool close(){if(!file)return false;file->close();bool ok=!file->fail();file.reset();return ok;}
};
struct HostStorage {
 std::string path(const char* p) const {return (std::string(p).rfind("/.crosspoint/",0)==0||std::string(p)=="/wikipedia.cdb"||std::string(p)=="/Wikipedia/wikipedia.cdb")?hostRoot+p:p;}
 HalFile open(const char* p,int flags){return HalFile(path(p),flags);}
 bool exists(const char* p){return std::filesystem::exists(path(p));}
 bool ensureDirectoryExists(const char* p){std::error_code e;std::filesystem::create_directories(path(p),e);return !e;}
};
inline HostStorage Storage;
''')
    (S/'GfxRenderer.h').write_text(r'''#pragma once
#include <algorithm>
#include <cstring>
#include <string>
#include <vector>
#include <fontIds.h>
namespace EpdFontFamily {enum Style {REGULAR,BOLD,ITALIC};}
struct DrawText {int font,x,y;std::string text;};
struct GfxRenderer {
 int width=480,height=800;
 mutable std::vector<DrawText> texts;
 mutable unsigned badBounds=0;
 int getScreenWidth()const{return width;} int getScreenHeight()const{return height;}
 int getLineHeight(int id)const {return id==SMALL_FONT_ID?18:id==NOTOSERIF_18_FONT_ID?38:id==NOTOSANS_16_FONT_ID||id==NOTOSERIF_16_FONT_ID?34:id==NOTOSANS_14_FONT_ID?30:26;}
 int getTextWidth(int id,const char* s,EpdFontFamily::Style=EpdFontFamily::REGULAR)const {int n=0;for(const unsigned char* p=reinterpret_cast<const unsigned char*>(s);*p;++p)if((*p&0xc0)!=0x80)++n;return n*(getLineHeight(id)/2);}
 void clearScreen(){texts.clear();} void displayBuffer(){}
 void drawText(int id,int x,int y,const char* s,bool=true,EpdFontFamily::Style=EpdFontFamily::REGULAR)const {texts.push_back({id,x,y,s});if(x<0||y<0||y+getLineHeight(id)>height)++badBounds;}
 void drawCenteredText(int id,int y,const char* s,bool black=true,EpdFontFamily::Style st=EpdFontFamily::REGULAR)const{drawText(id,(width-getTextWidth(id,s,st))/2,y,s,black,st);}
 void drawPixel(int x,int y,bool=true)const{if(x<0||x>=width||y<0||y>=height)++badBounds;}
 void drawRect(int,int,int,int,bool=true)const{}
 void drawLine(int,int,int,int,bool=true)const{}
 void fillRect(int,int,int,int,bool=true)const{}
 void drawRoundedRect(int,int,int,int,int,int,bool)const{}
 std::string truncatedText(int id,const char* s,int max,EpdFontFamily::Style st=EpdFontFamily::REGULAR)const{std::string v=s;while(!v.empty()&&getTextWidth(id,v.c_str(),st)>max)v.pop_back();return v;}
 std::vector<std::string> wrappedText(int id,const char* s,int max,int lines)const {
  std::vector<std::string> out;std::string rest=s;
  while(!rest.empty()&&int(out.size())<lines){const size_t n=std::min(rest.size(),size_t(std::max(1,max/(getLineHeight(id)/2))));out.push_back(rest.substr(0,n));rest.erase(0,n);}return out;
 }
 bool has(const std::string& s)const{for(const auto& t:texts)if(t.text.find(s)!=std::string::npos)return true;return false;}
};
''')
    (S/'activities/Activity.h').write_text(r'''#pragma once
#include <functional>
#include <memory>
#include <string>
#include <variant>
#include <GfxRenderer.h>
struct RenderLock { RenderLock() {} ~RenderLock() {} };
struct KeyboardResult {std::string text;};
struct ActivityResult {bool isCancelled=false;std::variant<std::monostate,KeyboardResult> data;};
using ActivityResultHandler=std::function<void(const ActivityResult&)>;
inline ActivityResultHandler hostKeyboard;
enum class HomeMenuItem {WIKI};
struct HostActivityManager {int homes=0;void goHome(HomeMenuItem){++homes;}};
inline HostActivityManager activityManager;
struct MappedInputManager {
 enum class Button {Back,Confirm,Left,Right,Up,Down};
 int pressed=-1,released=-1;unsigned held=0;
 bool wasPressed(Button b)const{return pressed==int(b);} bool wasReleased(Button b)const{return released==int(b);}
 bool isPressed(Button b)const{return pressed==int(b);} unsigned getHeldTime()const{return held;}
 struct Labels {const char *btn1,*btn2,*btn3,*btn4;};
 Labels mapLabels(const char* a,const char* b,const char* c,const char* d)const{return {a,b,c,d};}
};
class Activity {
 public:
 GfxRenderer& renderer;MappedInputManager& mappedInput;
 Activity(const char*,GfxRenderer& r,MappedInputManager& m):renderer(r),mappedInput(m){}
 virtual ~Activity()=default;
 virtual void onEnter(){} virtual void onExit(){} virtual void loop(){} virtual void render(RenderLock&&){}
 void requestUpdate(){}
 void startActivityForResult(std::unique_ptr<Activity>&&,ActivityResultHandler f){hostKeyboard=std::move(f);}
};
''')
    (S/'activities/util/KeyboardEntryActivity.h').write_text(r'''#pragma once
#include "activities/Activity.h"
class KeyboardEntryActivity:public Activity{public:KeyboardEntryActivity(GfxRenderer&r,MappedInputManager&m,const char*,std::string,size_t):Activity("keyboard",r,m){}};
''')
    (S/'components/UITheme.h').write_text(r'''#pragma once
#include <GfxRenderer.h>
struct Rect{int x,y,width,height;};
struct Metrics{int contentSidePadding=20,topPadding=5,headerHeight=45,buttonHintsHeight=40,verticalSpacing=10;};
class UITheme{public:static UITheme& getInstance(){static UITheme t;return t;}const Metrics& getMetrics()const{static Metrics m;return m;}};
struct HostGUI{void drawHeader(GfxRenderer&r,Rect p,const char*t){r.drawText(UI_12_FONT_ID,24,p.y,t);}void drawButtonHints(GfxRenderer&,const char*,const char*,const char*,const char*){}};
inline HostGUI GUI;
''')
    # Prefix fixture deliberately spans blocks and includes the multiword slug
    # convention of the published pack. Fixture bodies are not Wikipedia text.
    data=[('albert-einstein','Albert Einstein: Example only.'),('earth','Earth: '+('This is a fixture sentence. '*180)),
          ('moon','Moon: Fixture text with reference [12].'),('water','Water: thumb|250px|A caption. Water body text.')]
    data += [('earth-'+str(i).zfill(2),'Earth '+str(i)+': Fixture.') for i in range(20)]
    data.sort()
    fixture=WORK/'sd';fixture.mkdir(exist_ok=True)
    (fixture/'wikipedia.cdb').write_bytes(wiki_host_tests.pack_blocks([(k+'\t'+v+'\n').encode() for k,v in data]))
    (WORK/'tests.cpp').write_text(r'''#include "WikiActivity.h"
#include "WikiText.h"
#include "WikiBookmarks.h"
#include <HalStorage.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <random>
#include <stdexcept>
int checks=0;
void check(bool b,const char* s){++checks;if(!b)throw std::runtime_error(s);}
void clearBookmarks(){std::filesystem::remove_all(hostRoot+"/.crosspoint/wiki");}
void corrupt(const char* suffix){std::fstream f(hostRoot+"/.crosspoint/wiki/bookmarks."+suffix,std::ios::in|std::ios::out|std::ios::binary);f.seekp(18);f.put('x');}
int main(int argc,char**argv){try{
 check(argc>=2,"fixture argument");hostRoot=argv[1];clearBookmarks();
 WikiBookmarks b;check(b.load(),"empty bookmark list");check(b.items().empty(),"empty initial count");
 check(b.toggle("earth","Earth"),"save Earth");check(b.contains("earth"),"contains Earth");
 WikiBookmarks restart;check(restart.load()&&restart.contains("earth"),"bookmarks survive restart");
 check(b.toggle("moon","Moon"),"second snapshot");
 corrupt("b");WikiBookmarks recovered;check(recovered.load()&&recovered.contains("earth")&&!recovered.contains("moon"),"CRC fallback to previous snapshot");
 check(recovered.toggle("water","Water"),"repair alternate slot");
 hostWriteBudget=22;check(!recovered.toggle("cat","Cat"),"short write rejected");hostWriteBudget=-1;
 check(!recovered.contains("cat")&&recovered.contains("water"),"failed write rolls back RAM");
 WikiBookmarks afterFailure;check(afterFailure.load()&&afterFailure.contains("water")&&!afterFailure.contains("cat"),"short write retains last good snapshot");
 check(afterFailure.toggle("earth","Earth")&&!afterFailure.contains("earth"),"bookmark removal");
 WikiBookmarks afterRemoval;check(afterRemoval.load()&&!afterRemoval.contains("earth"),"removal persisted");
 check(!afterRemoval.toggle("bad\nkey","Bad"),"control characters rejected");
 check(!afterRemoval.toggle(std::string(1025,'x'),"Bad"),"overlong bookmark rejected");
 check(afterRemoval.toggle("e\xc3\xa9","\xc3\x89toile"),"UTF-8 bookmark round trip save");
 WikiBookmarks unicode;check(unicode.load()&&unicode.contains("e\xc3\xa9"),"UTF-8 survives reload");
 clearBookmarks();WikiBookmarks full;check(full.load(),"new list");
 for(int i=0;i<64;++i)check(full.toggle("key"+std::to_string(i),"Title "+std::to_string(i)),"bounded bookmark insertion");
 check(!full.toggle("overflow","Overflow")&&full.items().size()==64,"count ceiling");
 corrupt("a");corrupt("b");WikiBookmarks broken;check(!broken.load(),"both corrupt slots detected");check(!broken.toggle("new","New"),"do not overwrite corrupt originals");
 clearBookmarks();WikiBookmarks payload;check(payload.load(),"payload fixture");
 bool hit=false;for(int i=0;i<20;++i){if(!payload.toggle(std::to_string(i)+std::string(950,'k'),std::string(950,'t'))){hit=true;break;}}
 check(hit&&payload.items().size()<20,"payload ceiling");clearBookmarks();
 using namespace WikiText;
 check(key("  Albert Einstein ")=="albert-einstein","normalizes human query");
 check(key("Solar_system")=="solar-system","underscores supported");
 check(displayTitle("albert-einstein","Albert Einstein: A scientist.")=="Albert Einstein","original title casing");
 std::string original="Water: thumb|250px|Caption text. Water is wet.";auto cleanText=original;clean(cleanText,"water");
 check(cleanText.find("thumb|")==std::string::npos&&cleanText.find("250px|")==std::string::npos,"format switches removed");
 check(cleanText.find("Caption text.")!=std::string::npos&&cleanText.find("Water is wet.")!=std::string::npos,"caption and prose preserved");
 std::string notMetadata="The left| token inside prose is ambiguous.";clean(notMetadata,"x");check(notMetadata.find("inside prose")!=std::string::npos,"cleanup retains following prose");
 Document doc;std::string structured="Body paragraph.\n== History ==\nHistorical text.\n== References ==\n[1] A source.";doc.build(structured,true);
 check(doc.count()==5,"explicit sections parsed");check(doc.block(1).kind==Kind::Heading,"heading style");check(doc.block(4).kind==Kind::Note,"references smaller");
 std::string flat;for(int i=0;i<70;++i)flat+="A complete sentence in a flattened pack. ";doc.build(flat,true);check(doc.count()>1,"long excerpt visually reflowed");
 std::string joined;for(size_t i=0;i<doc.count();++i)joined+=flat.substr(doc.block(i).begin,doc.block(i).end-doc.block(i).begin);
 auto noSpace=[](std::string s){s.erase(std::remove(s.begin(),s.end(),' '),s.end());return s;};check(noSpace(joined)==noSpace(flat),"reflow retains every non-space character");
 doc.build(flat,false);check(doc.count()==1,"original text mode avoids synthetic paragraphs");
 size_t end=0;check(citation("x[12]",1,end)&&end==5,"numeric citation");check(!citation("[abc]",0,end),"ordinary brackets not footnotes");
 check(utf8Length("\xf0\x9f\x8c\x8d",0,4)==4,"valid four-byte UTF-8");check(!utf8Length("\xed\xa0\x80",0,3),"reject surrogate");
 char line[32];std::string utf="one \xc3\xa9 two";auto p=wrap(utf,0,utf.size(),5,line,sizeof(line),[](const char*s){return int(std::strlen(s));});check(p>0&&p<utf.size(),"bounded word wrap");
 std::mt19937 rng(2182);
 for(int i=0;i<10000;++i){std::string s(1+rng()%500,' ');for(char&c:s)c=char(rng()%256);size_t pos=0;unsigned iterations=0;while(pos<s.size()){size_t next=wrap(s,pos,s.size(),1+rng()%50,line,sizeof(line),[](const char*t){return int(std::strlen(t));});if(next<=pos||next>s.size())throw std::runtime_error("random wrap failed progress");pos=next;if(++iterations>s.size()+1)throw std::runtime_error("random wrap stuck");}doc.build(s,true);for(size_t j=0;j<doc.count();++j)if(doc.block(j).begin>=doc.block(j).end||doc.block(j).end>s.size())throw std::runtime_error("random document bounds");}
 check(true,"10,000 seeded malformed/UTF-8 wrap/document cases");
 check(wrap(std::string("abc"),100,900,20,line,sizeof(line),[](const char*s){return int(std::strlen(s));})==3,"out-of-range wrapping cursor clamped");
 doc.build(std::string("Caption: ")+flat,true);check(doc.block(0).kind==Kind::Body,"flattened long prose not all reduced to caption size");
 WikiArchive archive;check(archive.open((hostRoot+"/wikipedia.cdb").c_str()),"archive open");
 check(archive.search("Albert Einstein").key=="albert-einstein","multiword exact search");
 bool more=false;auto titles=archive.titles("earth",more);check(titles.size()==16&&more,"bounded search results and more indicator");
 titles=archive.titles("Albert Ein",more);check(titles.size()==1&&titles[0].label=="Albert Einstein"&&!more,"friendly multiword prefix results");
 check(archive.titles("",more).empty(),"empty query no scan");archive.close();
 GfxRenderer gfx;MappedInputManager input;WikiActivity wiki(gfx,input);wiki.onEnter();wiki.render(RenderLock{});
 check(gfx.has("Search Wikipedia...")&&!gfx.has("fixture sentence"),"Wiki opens search home, not an article");
 check(gfx.has("Random article")&&gfx.has("Bookmarks"),"visible Random and Bookmarks actions");
 using B=MappedInputManager::Button;
 auto tap=[&](B b){input.pressed=int(b);input.released=-1;input.held=0;wiki.loop();input.pressed=-1;input.released=int(b);wiki.loop();input.released=-1;};
 auto show=[&](){wiki.render(RenderLock{});};
 tap(B::Confirm);check(bool(hostKeyboard),"search opens keyboard");
 auto handler=hostKeyboard;hostKeyboard={};handler(ActivityResult{false,KeyboardResult{"Earth"}});show();
 check(gfx.has("Search results")&&gfx.has("More matches"),"prefix results screen");tap(B::Confirm);show();
 check(gfx.has("Page 1")&&gfx.has("Earth")&&!gfx.has("Search results"),"result opens article");
 tap(B::Down);show();check(gfx.has("Page 2"),"article next page");tap(B::Up);show();check(gfx.has("Page 1"),"article previous page");
 tap(B::Confirm);show();check(gfx.has("Save bookmark")&&gfx.has("Random article"),"article options discoverable");tap(B::Confirm);show();
 check(gfx.has("Bookmark saved")&&gfx.has("Saved"),"article saved");
 tap(B::Back);tap(B::Right);tap(B::Right);tap(B::Confirm);show();check(gfx.has("Bookmarks")&&gfx.has("Earth"),"saved list opens from home");
 tap(B::Confirm);show();check(gfx.has("Page 1")&&gfx.has("Earth"),"saved article opens");
 tap(B::Confirm);show();check(gfx.has("Remove bookmark"),"remove action on saved entry");
 tap(B::Right);tap(B::Confirm);show();check(gfx.has("Page 1"),"visible random action opens an article");
 // Reference image was not provided; this exercises screen transitions, not a
 // visual or pixel-perfect comparison with the original WikiReader device.
 tap(B::Back);tap(B::Confirm);handler=hostKeyboard;hostKeyboard={};handler(ActivityResult{true,{}});show();check(gfx.has("Search Wikipedia..."),"cancel search returns to home");
 tap(B::Confirm);handler=hostKeyboard;hostKeyboard={};handler(ActivityResult{false,KeyboardResult{"Water"}});tap(B::Confirm);show();check(!gfx.has("thumb|")&&!gfx.has("250px|"),"clean article hides raw display switches");
 tap(B::Confirm);for(int i=0;i<4;++i)tap(B::Right);tap(B::Confirm);show();check(gfx.has("ORIGINAL PACK TEXT")&&gfx.has("thumb|"),"original pack text remains accessible");
 tap(B::Back);tap(B::Back);check(activityManager.homes>0,"return to CrossPoint home");
 check(gfx.badBounds==0,"portrait text/globe vertical bounds");
 gfx.width=800;gfx.height=480;gfx.badBounds=0;wiki.onExit();wiki.onEnter();show();check(gfx.has("Random article")&&gfx.badBounds==0,"compact search home fits landscape bounds");
 tap(B::Confirm);handler=hostKeyboard;hostKeyboard={};handler(ActivityResult{false,KeyboardResult{"Moon"}});show();check(gfx.has("Search results"),"landscape search results");tap(B::Confirm);show();
 auto hold=[&](B b){input.pressed=int(b);input.released=-1;input.held=700;wiki.loop();input.pressed=-1;input.released=int(b);wiki.loop();input.released=-1;input.held=0;};
 hold(B::Confirm);show();check(gfx.has("Bookmark saved")&&gfx.has("Saved")&&!gfx.has("Article options"),"long Confirm saves without opening menu on release");
 hold(B::Back);show();check(gfx.has("Text size changed")&&gfx.has("Page 1"),"long Back changes font without navigating home");
 check(gfx.badBounds==0,"landscape article and result vertical bounds");
 wiki.onExit();
 if(argc>2){check(archive.open(argv[2]),"published pack opens");check(archive.search("Albert Einstein").found,"published multiword article");auto rows=archive.titles("Albert Ein",more);check(!rows.empty()&&rows[0].label=="Albert Einstein","published human-friendly title result");auto article=archive.search("Water");auto text=article.text;clean(text,article.key);check(text.find("thumb|")==std::string::npos&&text.find("Water")!=std::string::npos,"published caption/prose cleanup");}
 std::cout<<checks<<" beta 2 assertions passed; 10,000 seeded text cases; real UI C++ with host storage, font and keyboard adapters under ASan/UBSan. NOT device tests.\n";
}catch(const std::exception&e){std::cerr<<"FAILED after "<<checks<<" checks: "<<e.what()<<"\n";return 1;}}
''')
    prev=ROOT/'wiki-test-build/stubs'
    if not (prev/'InflateReader.h').exists():
        old=sys.argv[:];sys.argv=[sys.argv[0],'--skip-real'];wiki_host_tests.main();sys.argv=old
    source=ROOT/'src/activities/wiki'
    args=['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',
          '-I'+str(S),'-I'+str(prev),'-I'+str(ROOT/'src'),'-I'+str(source)]
    args += [str(source/n) for n in ['WikiActivity.cpp','WikiArchive.cpp','WikiText.cpp','WikiBookmarks.cpp']]
    args += [str(WORK/'tests.cpp'),'-lz','-o',str(WORK/'tests')]
    subprocess.run(args,check=True)
    run=[str(WORK/'tests'),str(fixture)]
    real=ROOT/'wiki-test-build/published-wikipedia.cdb'
    if real.exists():run.append(str(real))
    subprocess.run(run,check=True)
if __name__=='__main__':main()
