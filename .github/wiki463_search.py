#!/usr/bin/env python3
from pathlib import Path
R=Path('.')
(R/'src/activities/wiki/DiskTitleIndex.h').write_text('''#pragma once
#include <HalStorage.h>
#include <array>
#include <cstdint>
#include <string>
// Disposable secondary index; canonical article order and bookmark IDs stay intact.
class DiskTitleIndex {
 public:
  static constexpr uint32_t KEY_BYTES=52;
  struct Record {std::array<char,KEY_BYTES> key{};uint32_t id=0;};
  using Provider=bool(*)(void*,uint32_t,Record&);
  bool open(const std::string&,const std::array<uint8_t,32>&,uint32_t);
  bool build(const std::string&,const std::array<uint8_t,32>&,uint32_t,Provider,void*);
  void close();bool ready()const{return bool(file_);}
  bool record(uint32_t,Record&);bool lowerBound(const std::string&,uint32_t&);
 private:
  static bool less(const Record&,const Record&);
  static bool readRecord(HalFile&,uint32_t,uint32_t,Record&);
  static bool writeRecord(HalFile&,const Record&);
  HalFile file_;uint32_t count_=0;
};
''')
(R/'src/activities/wiki/DiskTitleIndex.cpp').write_text(r'''#include "DiskTitleIndex.h"
#include <Arduino.h>
#include <RecoverableFile.h>
#include <algorithm>
#include <cstring>
#include <memory>
#include <new>
namespace {
constexpr uint32_t HEADER=64,RECORD=60,RUN=64;
uint32_t hashBytes(const uint8_t* p,size_t n){uint32_t h=2166136261u;while(n--){h^=*p++;h*=16777619u;}return h;}
void put32(uint8_t* p,uint32_t v){for(unsigned i=0;i<4;++i)p[i]=uint8_t(v>>(8*i));}
uint32_t get32(const uint8_t* p){return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
bool readExact(HalFile& f,uint8_t* p,size_t n){while(n){const int got=f.read(p,n);if(got<=0||size_t(got)>n)return false;p+=got;n-=got;}return true;}
bool writeExact(HalFile& f,const uint8_t* p,size_t n){while(n){const size_t got=f.write(p,n);if(!got||got>n)return false;p+=got;n-=got;}return true;}
std::array<uint8_t,HEADER> header(const std::array<uint8_t,32>& source,uint32_t count){
 std::array<uint8_t,HEADER> h{};std::memcpy(h.data(),"WXSEARCH",8);std::memcpy(h.data()+8,source.data(),32);
 put32(h.data()+40,count);put32(h.data()+44,RECORD);put32(h.data()+48,1);put32(h.data()+60,hashBytes(h.data(),60));return h;
}
bool finish(HalFile& f,uint64_t expected){const bool sizeOK=f.fileSize64()==expected;const bool synced=f.sync();f.close();return sizeOK&&synced;}
}
bool DiskTitleIndex::less(const Record& a,const Record& b){const int c=std::memcmp(a.key.data(),b.key.data(),KEY_BYTES);return c<0||(c==0&&a.id<b.id);}
void DiskTitleIndex::close(){if(file_)file_.close();count_=0;}
bool DiskTitleIndex::open(const std::string& path,const std::array<uint8_t,32>& source,uint32_t count){
 close();HalStorage::Transaction transaction;if(!RecoverableFile::recoverMissing(path.c_str()))return false;
 file_=Storage.open(path.c_str(),O_RDONLY);std::array<uint8_t,HEADER> got{};
 if(!file_||file_.fileSize64()!=uint64_t(HEADER)+uint64_t(count)*RECORD||!readExact(file_,got.data(),got.size())||got!=header(source,count)){close();return false;}
 count_=count;return true;
}
bool DiskTitleIndex::writeRecord(HalFile& f,const Record& r){
 std::array<uint8_t,RECORD> data{};std::memcpy(data.data(),r.key.data(),KEY_BYTES);data[KEY_BYTES-1]=0;
 put32(data.data()+52,r.id);put32(data.data()+56,hashBytes(data.data(),56));return writeExact(f,data.data(),data.size());
}
bool DiskTitleIndex::readRecord(HalFile& f,uint32_t i,uint32_t count,Record& r){
 if(i>=count)return false;const uint64_t off=uint64_t(HEADER)+uint64_t(i)*RECORD;std::array<uint8_t,RECORD> data{};
 if((f.position()!=off&&!f.seek64(off))||!readExact(f,data.data(),data.size())||data[KEY_BYTES-1]!=0||
    get32(data.data()+56)!=hashBytes(data.data(),56))return false;
 std::memcpy(r.key.data(),data.data(),KEY_BYTES);r.id=get32(data.data()+52);return r.id<count;
}
bool DiskTitleIndex::record(uint32_t i,Record& r){if(!file_||!readRecord(file_,i,count_,r)){close();return false;}return true;}
bool DiskTitleIndex::lowerBound(const std::string& key,uint32_t& index){
 if(!file_)return false;std::array<char,KEY_BYTES> needle{};std::memcpy(needle.data(),key.data(),std::min<size_t>(key.size(),KEY_BYTES-1));
 uint32_t lo=0,hi=count_;while(lo<hi){const uint32_t mid=lo+(hi-lo)/2;Record r;if(!record(mid,r))return false;
 if(std::memcmp(r.key.data(),needle.data(),KEY_BYTES)<0)lo=mid+1;else hi=mid;}index=lo;return true;
}
bool DiskTitleIndex::build(const std::string& path,const std::array<uint8_t,32>& source,uint32_t count,Provider provider,void* context){
 close();std::unique_ptr<std::array<Record,RUN>> run(new(std::nothrow)std::array<Record,RUN>);if(!run||!provider)return false;
 const auto h=header(source,count);const uint64_t expected=uint64_t(HEADER)+uint64_t(count)*RECORD;
 std::string input=path+".sort-a",output=path+".sort-b";
 auto out=Storage.open(input.c_str(),O_WRONLY|O_CREAT|O_TRUNC);if(!out||!writeExact(out,h.data(),h.size()))return false;
 // Fixed 3.5 KiB sort run; no array proportional to library size.
 for(uint64_t base=0;base<count;base+=RUN){const uint32_t n=std::min<uint64_t>(RUN,uint64_t(count)-base);
   for(uint32_t i=0;i<n;++i){if(!provider(context,uint32_t(base+i),(*run)[i])||(*run)[i].id>=count)return false;(*run)[i].key[KEY_BYTES-1]=0;}
   std::sort(run->begin(),run->begin()+n,less);for(uint32_t i=0;i<n;++i)if(!writeRecord(out,(*run)[i]))return false;delay(1);
 }
 if(!finish(out,expected))return false;run.reset();
 for(uint64_t width=RUN;width<count;width*=2){
   auto left=Storage.open(input.c_str(),O_RDONLY);auto right=Storage.open(input.c_str(),O_RDONLY);
   out=Storage.open(output.c_str(),O_WRONLY|O_CREAT|O_TRUNC);if(!left||!right||!out||!writeExact(out,h.data(),h.size()))return false;
   for(uint64_t base=0;base<count;base+=width*2){uint64_t a=base,b=std::min<uint64_t>(base+width,count);
     const uint64_t endA=b,endB=std::min<uint64_t>(base+2*width,count);Record ra{},rb{};bool haveA=false,haveB=false;
     while(a<endA||b<endB){
       if(!haveA&&a<endA){if(!readRecord(left,uint32_t(a),count,ra))return false;haveA=true;}
       if(!haveB&&b<endB){if(!readRecord(right,uint32_t(b),count,rb))return false;haveB=true;}
       if(haveA&&(!haveB||less(ra,rb))){if(!writeRecord(out,ra))return false;++a;haveA=false;}
       else{if(!writeRecord(out,rb))return false;++b;haveB=false;}
       if(((a+b)&511u)==0)delay(1);
     }
   }
   left.close();right.close();if(!finish(out,expected))return false;std::swap(input,output);
 }
 auto verify=Storage.open(input.c_str(),O_RDONLY);if(!verify)return false;Record previous{},current{};
 for(uint32_t i=0;i<count;++i){if(!readRecord(verify,i,count,current)||(i&&less(current,previous)))return false;
   previous=current;if((i&511u)==0)delay(1);}
 verify.close();
 {HalStorage::Transaction transaction;if(!RecoverableFile::recoverMissing(path.c_str())||!RecoverableFile::commit(path.c_str(),input.c_str()))return false;}
 Storage.remove(output.c_str());return open(path,source,count);
}
''')
p=R/'src/activities/wiki/WikiArchive.h';s=p.read_text().replace('#include <HalStorage.h>','#include <HalStorage.h>\n#include "DiskTitleIndex.h"');assert '  HalFile indexFile_;' in s;s=s.replace('  HalFile indexFile_;','  HalFile indexFile_;\n  DiskTitleIndex titleSearchIndex_;');p.write_text(s)
p=R/'src/activities/wiki/WikiArchive.cpp';s=p.read_text().replace('#include "WikiArchive.h"','#include "WikiArchive.h"\n#include <RecoverableFile.h>')
s=s.replace('void WikiArchive::close() {','void WikiArchive::close() {\n  titleSearchIndex_.close();')
s=s.replace('  indexFile_=Storage.open(xmlIndexPath_.c_str(),O_RDONLY);','  {HalStorage::Transaction transaction;if(!RecoverableFile::recoverMissing(xmlIndexPath_.c_str()))return false;}\n  indexFile_=Storage.open(xmlIndexPath_.c_str(),O_RDONLY);')
s=s.replace('  auto out=Storage.open(xmlIndexPath_.c_str(),O_WRONLY|O_CREAT|O_TRUNC);','  const std::string temporary=xmlIndexPath_+".tmp";\n  auto out=Storage.open(temporary.c_str(),O_WRONLY|O_CREAT|O_TRUNC);')
a='  out.flush(); if(!out.close()) return false; entries_=count; builtIndexOnOpen_=true; return true;';assert s.count(a)==1
s=s.replace(a,'''  if(absolute!=fileSize_){out.close();return false;}
  const bool synced=out.sync();out.close();if(!synced)return false;
  HalStorage::Transaction transaction;
  if(!RecoverableFile::recoverMissing(xmlIndexPath_.c_str())||!RecoverableFile::commit(xmlIndexPath_.c_str(),temporary.c_str()))return false;
  entries_=count;builtIndexOnOpen_=true;return true;''')
a='  ready_=true; cursorRecord_=0; return true;';assert s.count(a)==1
s=s.replace(a,'''  ready_=true;cursorRecord_=0;
  std::array<uint8_t,32> signature{};
  if(indexFile_.seek64(0)&&indexFile_.read(signature.data(),signature.size())==int(signature.size())) {
    const std::string searchPath=xmlIndexPath_+".search";
    if(!titleSearchIndex_.open(searchPath,signature,entries_)) {
      const auto provider=[](void* ctx,uint32_t id,DiskTitleIndex::Record& out) {
        auto* self=static_cast<WikiArchive*>(ctx);XmlRecord rec;if(!self->xmlRecord(id,rec))return false;
        std::memcpy(out.key.data(),rec.key,XML_KEY_BYTES);out.id=id;return true;
      };
      // SD-full, OOM, or corrupt derived index preserves the original linear path.
      titleSearchIndex_.build(searchPath,signature,entries_,provider,this);
    }
  }
  return true;''')
a=s.index('WikiArchive::Entry WikiArchive::xmlLookup(');b=s.index('\nstd::vector<WikiArchive::Title> WikiArchive::xmlTitles',a)
old=s[a:b];at=old.index('{')+1
fast='''
  if(ready_&&format_==Format::MediaWikiXml&&!query.empty()&&query.size()<=XML_MAX_TITLE&&titleSearchIndex_.ready()) {
    const std::string key=queryKey(query),needle=key.substr(0,XML_KEY_BYTES-1);uint32_t begin=0;
    if(!needle.empty()&&titleSearchIndex_.lowerBound(needle,begin)) {
      bool failed=false;
      for(uint32_t i=begin;i<entries_;++i){DiskTitleIndex::Record rec;
        if(!titleSearchIndex_.record(i,rec)){failed=true;break;}
        const std::string shortTitle(rec.key.data());
        if(prefix?shortTitle.compare(0,needle.size(),needle)!=0:shortTitle!=needle)return {};
        Entry meta=xmlEntryAt(rec.id,false);if(!meta.found)continue;const std::string actual=queryKey(meta.title);
        if(actual==key||(prefix&&actual.compare(0,key.size(),key)==0))return xmlEntryAt(rec.id,true);
        if((i&511u)==0)delay(1);
      }
      if(!failed)return {};
    }
  }
'''
s=s[:a]+old[:at]+fast+old[at:]+s[b:]
a=s.index('std::vector<WikiArchive::Title> WikiArchive::xmlTitles(');b=s.index('\nWikiArchive::Entry WikiArchive::resolve',a);old=s[a:b];at=old.index('{')+1
fast='''
  if(ready_&&format_==Format::MediaWikiXml&&!query.empty()&&query.size()<=XML_MAX_TITLE&&limit&&titleSearchIndex_.ready()) {
    more=false;limit=std::min<size_t>(limit,16);const std::string key=queryKey(query),needle=key.substr(0,XML_KEY_BYTES-1);uint32_t begin=0;
    if(!needle.empty()&&titleSearchIndex_.lowerBound(needle,begin)) {
      std::vector<Title> found;bool failed=false;
      for(uint32_t i=begin;i<entries_;++i){DiskTitleIndex::Record rec;
        if(!titleSearchIndex_.record(i,rec)){failed=true;break;}
        if(std::string(rec.key.data()).compare(0,needle.size(),needle)!=0)return found;
        Entry meta=xmlEntryAt(rec.id,false);if(!meta.found||queryKey(meta.title).compare(0,key.size(),key)!=0)continue;
        if(found.size()>=limit){more=true;return found;}found.push_back({meta.title,meta.title});
        if((i&511u)==0)delay(1);
      }
      if(!failed)return found;
    }
  }
'''
s=s[:a]+old[:at]+fast+old[at:]+s[b:];p.write_text(s)
print('4.6.3 XML: fixed-memory external sort, binary title search, checked derived records, verified full-title match and linear fallback')
