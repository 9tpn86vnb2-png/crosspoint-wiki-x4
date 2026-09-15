#!/usr/bin/env python3
"""Apply the 4.6.3 storage changes to the reconstructed, not raw, 4.6.2 tree."""
from pathlib import Path
R=Path('.')
def edit(p,a,b):
 f=R/p;s=f.read_text();assert s.count(a)==1,(p,a[:120],s.count(a));f.write_text(s.replace(a,b,1))
def write(p,s):
 f=R/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
edit('lib/hal/HalStorage.h','  class StorageLock;  // private class, used internally','''  // Whole-operation lock; individual HAL calls already use this recursive mutex.
  class Transaction {
   public:
    Transaction();
    ~Transaction();
    Transaction(const Transaction&) = delete;
    Transaction& operator=(const Transaction&) = delete;
  };
  class StorageLock;  // private class, used internally''')
edit('lib/hal/HalStorage.h','  void flush();','  void flush();\n  bool sync();\n  bool truncate(uint64_t length);')
edit('lib/hal/HalStorage.cpp','void HalStorage::prepareForDeepSleep() {','''HalStorage::Transaction::Transaction() {
  xSemaphoreTakeRecursive(HalStorage::getInstance().storageMutex, portMAX_DELAY);
}
HalStorage::Transaction::~Transaction() {
  xSemaphoreGiveRecursive(HalStorage::getInstance().storageMutex);
}
void HalStorage::prepareForDeepSleep() {''')
edit('lib/hal/HalStorage.cpp','void HalFile::flush() { HAL_FILE_WRAPPED_CALL(flush, ); }','''void HalFile::flush() { HAL_FILE_WRAPPED_CALL(flush, ); }
bool HalFile::sync() { HAL_FILE_WRAPPED_CALL(sync, ); }
bool HalFile::truncate(uint64_t length) { HAL_FILE_WRAPPED_CALL(truncate, length); }''')
write('lib/Serialization/RecoverableFile.h','''#pragma once
#include <HalStorage.h>
#include <string>
// Call under HalStorage::Transaction. An uncommitted .tmp is never promoted.
// This preserves a recoverable generation; FAT is not a journaled filesystem.
namespace RecoverableFile {
inline bool recoverMissing(const char* path) {
  if (Storage.exists(path)) return true;
  const std::string backup = std::string(path) + ".bak";
  return !Storage.exists(backup.c_str()) || Storage.rename(backup.c_str(), path);
}
inline bool commit(const char* path, const char* temporary) {
  const std::string backup = std::string(path) + ".bak";
  const bool existed = Storage.exists(path);
  if (existed) {
    if (Storage.exists(backup.c_str()) && !Storage.remove(backup.c_str())) return false;
    if (!Storage.rename(path, backup.c_str())) return false;
  }
  if (Storage.rename(temporary, path)) return true;
  if (existed && !Storage.exists(path)) Storage.rename(backup.c_str(), path);
  return false; // Keep .bak and .tmp when rollback itself failed.
}
}
''')
p=R/'lib/Serialization/PersistableStore.cpp';s=p.read_text();tail=s[s.index('std::string PersistableStoreBase::extractPassword'):]
p.write_text(r'''#include "PersistableStore.h"
#include "RecoverableFile.h"
#include <HalStorage.h>
#include <Logging.h>
#include <ObfuscationUtils.h>
#include <algorithm>
#include <cstring>
#include <limits>
namespace {
class JsonBufferedPrint final : public Print {
 public:
  JsonBufferedPrint(HalFile& file, bool compare) : file_(file), compare_(compare) {}
  size_t write(uint8_t b) override { return write(&b,1); }
  size_t write(const uint8_t* data,size_t size) override {
    const size_t requested=size;
    while(size && ok_) {
      const size_t n=std::min(size,sizeof(buffer_)-used_);
      std::memcpy(buffer_+used_,data,n); used_+=n;data+=n;size-=n;
      if(used_==sizeof(buffer_)) drain();
    }
    return compare_ ? requested : requested-size;
  }
  bool finish() { drain();return ok_; }
 private:
  void drain() {
    if(!used_ || !ok_) return;
    if(compare_) {
      uint8_t scratch[512];size_t n=0;
      while(n<used_) {
        const int got=file_.read(scratch+n,used_-n);
        if(got<=0 || size_t(got)>used_-n) {ok_=false;break;}
        n+=size_t(got);
      }
      ok_=ok_ && std::memcmp(buffer_,scratch,used_)==0;
    } else {
      size_t n=0;
      while(n<used_) {
        const size_t got=file_.write(buffer_+n,used_-n);
        if(!got || got>used_-n) {ok_=false;break;}
        n+=got;
      }
    }
    used_=0;
  }
  HalFile& file_;bool compare_;bool ok_=true;uint8_t buffer_[512];size_t used_=0;
};
class JsonBufferedReader {
 public:
  explicit JsonBufferedReader(HalFile& f):file_(f),remaining_(f.fileSize64()) {}
  int read() {
    if(at_==used_) {
      if(!remaining_) return -1;
      const int got=file_.read(buffer_,std::min<uint64_t>(sizeof(buffer_),remaining_));
      if(got<=0 || uint64_t(got)>remaining_) {failed_=true;return -1;}
      remaining_-=got;used_=size_t(got);at_=0;
    }
    return buffer_[at_++];
  }
  size_t readBytes(char* p,size_t count) {
    size_t n=0;while(n<count){const int c=read();if(c<0)break;p[n++]=char(c);}return n;
  }
  bool failed()const{return failed_;}
 private:
  HalFile& file_;uint64_t remaining_;uint8_t buffer_[512];size_t at_=0,used_=0;bool failed_=false;
};
enum class JsonState { Missing, Invalid, IoError, Valid };
JsonState parseFile(const char* path,JsonDocument& doc) {
  doc.clear();if(!Storage.exists(path))return JsonState::Missing;
  auto file=Storage.open(path,O_RDONLY);if(!file)return JsonState::IoError;
  JsonBufferedReader reader(file);
  const bool parsed=!deserializeJson(doc,reader) && !doc.overflowed();
  bool clean=true;
  for(int c=reader.read();c>=0;c=reader.read())if(c!=' '&&c!='\t'&&c!='\r'&&c!='\n')clean=false;
  file.close();
  if(reader.failed())return JsonState::IoError;
  return parsed&&clean ? JsonState::Valid : JsonState::Invalid;
}
bool matchesFile(const char* path,const JsonDocument& doc,size_t expected) {
  auto file=Storage.open(path,O_RDONLY);if(!file)return false;
  if(file.fileSize64()!=expected){file.close();return false;}
  JsonBufferedPrint compare(file,true);const size_t n=serializeJson(doc,compare);
  const bool ok=compare.finish() && n==expected;file.close();return ok;
}
}
bool PersistableStoreBase::writeDocToFile(const char* path,const JsonDocument& doc) {
  if(!path||!*path||doc.overflowed())return false;
  HalStorage::Transaction transaction;
  Storage.mkdir("/.crosspoint");
  if(!RecoverableFile::recoverMissing(path))return false;
  const size_t expected=measureJson(doc);if(!expected)return false;
  if(Storage.exists(path)&&matchesFile(path,doc,expected))return true;
  const std::string backup=std::string(path)+".bak";
  if(Storage.exists(path)&&Storage.exists(backup.c_str())) {
    JsonDocument previous;const auto state=parseFile(path,previous);
    if(state==JsonState::IoError)return false;
    if(state!=JsonState::Valid) {
      if(parseFile(backup.c_str(),previous)!=JsonState::Valid)return false;
      const std::string damaged=std::string(path)+".damaged";
      if(Storage.exists(damaged.c_str())&&!Storage.remove(damaged.c_str()))return false;
      if(!Storage.rename(path,damaged.c_str()))return false;
      if(!Storage.rename(backup.c_str(),path)) {Storage.rename(damaged.c_str(),path);return false;}
    }
  }
  const std::string tmp=std::string(path)+".tmp";
  auto out=Storage.open(tmp.c_str(),O_WRONLY|O_CREAT|O_TRUNC);if(!out)return false;
  JsonBufferedPrint writer(out,false);const size_t n=serializeJson(doc,writer);
  const bool complete=writer.finish()&&n==expected&&out.fileSize64()==expected;
  const bool synced=out.sync();out.close();
  if(!complete||!synced||!matchesFile(tmp.c_str(),doc,expected)) {
    Storage.remove(tmp.c_str());LOG_ERR("PERSIST","Incomplete JSON write: %s",path);return false;
  }
  return RecoverableFile::commit(path,tmp.c_str());
}
bool PersistableStoreBase::readDocFromFile(const char* path,JsonDocument& doc) {
  if(!path||!*path)return false;
  HalStorage::Transaction transaction;
  if(!RecoverableFile::recoverMissing(path))return false;
  if(parseFile(path,doc)==JsonState::Valid)return true;
  const std::string backup=std::string(path)+".bak";
  if(parseFile(backup.c_str(),doc)==JsonState::Valid)return true;
  doc.clear();return false;
}

'''+tail)
p=R/'src/FinishedBooksStore.cpp';s=p.read_text().replace('#include <Logging.h>','#include <Logging.h>\n#include <RecoverableFile.h>')
a=s.index('bool ensureCatalogFile() {');b=s.index('bool stringFitsRecord',a)
s=s[:a]+'''std::array<uint8_t,2048> pathBloom{};
uint64_t knownCatalogSize=0;
bool catalogCacheValid=false;
uint32_t pathHash(const std::string& path){uint32_t h=2166136261u;for(unsigned char c:path){h^=c;h*=16777619u;}return h;}
void bloomAdd(const std::string& path){uint32_t h=pathHash(path),step=(h>>16)|1u;for(int i=0;i<3;++i,h+=step){const uint32_t b=h&16383u;pathBloom[b>>3]|=uint8_t(1u<<(b&7));}}
bool bloomMaybe(const std::string& path){uint32_t h=pathHash(path),step=(h>>16)|1u;for(int i=0;i<3;++i,h+=step){const uint32_t b=h&16383u;if(!(pathBloom[b>>3]&(1u<<(b&7))))return false;}return true;}
bool ensureCatalogFile();

'''+s[b:]
a=s.index('bool pathMatchesAndSkip(');b=s.index('bool rewriteCatalog(',a)
s=s[:a]+'''// Structural tail repair is performed once on cold load or a size change.
// A failed read is not permission to truncate. The Bloom filter never proves a
// duplicate: possible matches always use the complete stored path.
bool ensureCatalogFile() {
  Storage.mkdir("/.crosspoint");
  if(!RecoverableFile::recoverMissing(FinishedBooksStore::FILE_PATH))return false;
  if(!Storage.exists(FinishedBooksStore::FILE_PATH)) {
    auto fresh=Storage.open(TEMP_PATH,O_WRONLY|O_CREAT|O_TRUNC);if(!fresh)return false;
    const bool wrote=writeMagic(fresh);const bool synced=fresh.sync();fresh.close();
    if(!wrote||!synced||!RecoverableFile::commit(FinishedBooksStore::FILE_PATH,TEMP_PATH))return false;
    catalogCacheValid=false;
  }
  auto file=Storage.open(FinishedBooksStore::FILE_PATH,O_RDONLY);if(!file)return false;
  const uint64_t size=file.fileSize64();
  std::array<uint8_t,4> magic{};
  if(size<4||!readExact(file,magic.data(),4)){file.close();return false;}
  if(magic!=MAGIC) {
    file.close();const std::string backup=std::string(FinishedBooksStore::FILE_PATH)+".bak";
    auto old=Storage.open(backup.c_str(),O_RDONLY);if(!old||!readMagic(old))return false;old.close();
    const std::string damaged=std::string(FinishedBooksStore::FILE_PATH)+".damaged";
    if(Storage.exists(damaged.c_str())&&!Storage.remove(damaged.c_str()))return false;
    if(!Storage.rename(FinishedBooksStore::FILE_PATH,damaged.c_str()))return false;
    if(!Storage.rename(backup.c_str(),FinishedBooksStore::FILE_PATH)){Storage.rename(damaged.c_str(),FinishedBooksStore::FILE_PATH);return false;}
    catalogCacheValid=false;return ensureCatalogFile();
  }
  if(catalogCacheValid&&knownCatalogSize==size){file.close();return true;}
  catalogCacheValid=false;pathBloom.fill(0);uint64_t validEnd=4;
  while(validEnd<size) {
    if(size-validEnd<RECORD_HEADER_BYTES)break;
    uint8_t raw[8];if(!readExact(file,raw,8)){file.close();return false;}
    RecordLengths len;
    len.path=uint16_t(raw[0]|uint16_t(raw[1])<<8);len.title=uint16_t(raw[2]|uint16_t(raw[3])<<8);
    len.author=uint16_t(raw[4]|uint16_t(raw[5])<<8);len.cover=uint16_t(raw[6]|uint16_t(raw[7])<<8);
    if(!len.path||len.payloadBytes()>MAX_RECORD_BYTES||len.payloadBytes()>size-validEnd-8)break;
    std::string path;
    if(!readString(file,len.path,path)||!file.seekCur(uint32_t(len.title)+len.author+len.cover)){file.close();return false;}
    bloomAdd(path);validEnd+=8+len.payloadBytes();
  }
  file.close();
  if(validEnd!=size) {
    auto repair=Storage.open(FinishedBooksStore::FILE_PATH,O_WRONLY);if(!repair)return false;
    const bool repaired=repair.truncate(validEnd);const bool synced=repair.sync();repair.close();
    if(!repaired||!synced)return false;
  }
  knownCatalogSize=validEnd;catalogCacheValid=true;return true;
}
bool findPath(const std::string& path,bool& found) {
  found=false;if(!bloomMaybe(path))return true;
  auto file=Storage.open(FinishedBooksStore::FILE_PATH,O_RDONLY);if(!file||!readMagic(file))return false;
  const uint64_t size=file.fileSize64();
  while(file.position()<size) {
    RecordLengths len;std::string stored;
    if(size-file.position()<8||!readLengths(file,len)||len.payloadBytes()>size-file.position()||
       !readString(file,len.path,stored)||!file.seekCur(uint32_t(len.title)+len.author+len.cover))return false;
    if(stored==path){found=true;file.close();return true;}
  }
  file.close();return true;
}

'''+s[b:]
s=s.replace('  if (!Storage.exists(FinishedBooksStore::FILE_PATH)) return false;','  if (!Storage.exists(FinishedBooksStore::FILE_PATH) || !ensureCatalogFile()) return false;',1)
s=s.replace('O_WRONLY | O_CREAT);','O_WRONLY | O_CREAT | O_TRUNC);')
s=s.replace('  out.flush();\n  out.close();\n  in.close();','  ok = ok && in.position() == fileSize;\n  const bool synced = out.sync();\n  out.close();\n  in.close();\n  ok = ok && synced;',1)
s=s.replace('  if (!changed) {\n    Storage.remove(TEMP_PATH);\n    return false;\n  }','  if (!changed) {\n    Storage.remove(TEMP_PATH);\n    return true;\n  }',1)
a=s.index('  if (!Storage.remove(FinishedBooksStore::FILE_PATH) ||');b=s.index('\n  return true;\n}',a)
s=s[:a]+'''  catalogCacheValid=false;
  if(!RecoverableFile::commit(FinishedBooksStore::FILE_PATH,TEMP_PATH))return false;'''+s[b:]
a=s.index('bool FinishedBooksStore::add(');b=s.index('bool FinishedBooksStore::removeByPath',a)
s=s[:a]+'''bool FinishedBooksStore::add(const RecentBook& book) {
  HalStorage::Transaction transaction;
  RecordLengths len;if(!makeLengths(book,len)||!ensureCatalogFile())return false;
  bool found=false;if(!findPath(book.path,found))return false;if(found)return true;
  const uint64_t previousSize=knownCatalogSize,expectedSize=previousSize+8+len.payloadBytes();
  auto file=Storage.open(FILE_PATH,O_WRONLY);if(!file)return false;
  bool ok=file.seek64(previousSize)&&writeRecord(file,book)&&file.fileSize64()==expectedSize;
  const bool synced=file.sync();file.close();ok=ok&&synced;
  if(ok) {
    auto check=Storage.open(FILE_PATH,O_RDONLY);RecordLengths gotLen;RecentBook got;
    ok=check&&check.fileSize64()==expectedSize&&check.seek64(previousSize)&&readLengths(check,gotLen)&&
       readRecordPayload(check,gotLen,got)&&got.path==book.path&&got.title==book.title&&
       got.author==book.author&&got.coverBmpPath==book.coverBmpPath;
    if(check)check.close();
  }
  if(!ok) {
    auto rollback=Storage.open(FILE_PATH,O_WRONLY);
    if(rollback){rollback.truncate(previousSize);rollback.sync();rollback.close();}
    catalogCacheValid=false;return false;
  }
  bloomAdd(book.path);knownCatalogSize=expectedSize;catalogCacheValid=true;return true;
}
bool FinishedBooksStore::contains(const std::string& path) {
  HalStorage::Transaction transaction;
  if(!RecoverableFile::recoverMissing(FILE_PATH)||!Storage.exists(FILE_PATH)||!ensureCatalogFile())return false;
  bool found=false;return findPath(path,found)&&found;
}

'''+s[b:]
s=s.replace('bool FinishedBooksStore::removeByPath(const std::string& path) {','bool FinishedBooksStore::removeByPath(const std::string& path) {\n  HalStorage::Transaction transaction;')
s=s.replace('  bool changed = false;\n  const bool ok = rewriteCatalog(oldPath','  HalStorage::Transaction transaction;\n  bool changed = false;\n  const bool ok = rewriteCatalog(oldPath')
s=s.replace('return !changed || ok;','return ok;')
s=s.replace('bool FinishedBooksStore::buildCatalog(FinishedBooksCatalog& catalog) {\n  catalog.clear();\n  if (!Storage.exists(FILE_PATH)) return true;','''bool FinishedBooksStore::buildCatalog(FinishedBooksCatalog& catalog) {
  HalStorage::Transaction transaction;
  catalog.clear();
  if(!RecoverableFile::recoverMissing(FILE_PATH))return false;
  if(!Storage.exists(FILE_PATH))return true;
  if(!ensureCatalogFile())return false;''')
s=s.replace('      break;\n    }\n    catalog.count++;','      file.close();\n      catalog.clear();\n      return false;\n    }\n    catalog.count++;')
s=s.replace('uint16_t count, std::vector<RecentBook>& out) {','uint16_t count, std::vector<RecentBook>& out) {\n  HalStorage::Transaction transaction;')
p.write_text(s)
edit('src/RecentBooksStore.h','  void markFinished(', '  bool markFinished(')
edit('src/RecentBooksStore.cpp','void RecentBooksStore::markFinished(', 'bool RecentBooksStore::markFinished(')
edit('src/RecentBooksStore.cpp','''    LOG_ERR("RBS", "Failed to persist finished book: %s", path.c_str());
    return;
  }
  removeByPath(path);
}''','''    LOG_ERR("RBS", "Failed to persist finished book: %s", path.c_str());
    return false;
  }
  removeByPath(path);
  return true;
}''')
print('4.6.3 storage: complete verified writes, backup recovery, repaired catalog append, checked completion result')
