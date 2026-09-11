#!/usr/bin/env python3
"""Compile the real WikiArchive.cpp on a host. Storage/Arduino are host adapters;
raw DEFLATE is supplied by host zlib, not the ESP32 uzlib implementation.
These are not display or device tests. --skip-real avoids the public pack download.
"""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'wiki-test-build'
STUBS = WORK / 'stubs'
PACK_URL = 'https://github.com/Sparkadium/crosspoint-reader-almanac/releases/download/v1.1.0-almanac/wikipedia.cdb'
PACK_SHA = 'c994f024322352de9e8ec96092834b2296f2304400337a016dc7a8eedf0e2b30'

def pack_blocks(blocks):
    offset = 12 + 44 * len(blocks)
    index, payload = [], []
    count = 0
    for raw in blocks:
        compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
        compressed = compressor.compress(raw) + compressor.flush()
        first = raw.split(b'\t', 1)[0][:31].ljust(32, b'\0')
        index.append(struct.pack('<32sIII', first, offset, len(compressed), len(raw)))
        payload.append(compressed)
        count += raw.count(b'\n')
        offset += len(compressed)
    return struct.pack('<4sII', b'WCDB', len(blocks), count) + b''.join(index + payload)

def main():
    STUBS.mkdir(parents=True, exist_ok=True)
    (STUBS / 'Arduino.h').write_text('#pragma once\ninline void delay(unsigned) {}\n')
    (STUBS / 'esp_random.h').write_text('#pragma once\n#include <cstdint>\ninline uint32_t esp_random() { static uint32_t s=123; s=s*1664525u+1013904223u; return s; }\n')
    (STUBS / 'HalStorage.h').write_text(r'''#pragma once
#include <cstdint>
#include <fcntl.h>
#include <fstream>
#include <memory>
class HalFile {
 std::shared_ptr<std::ifstream> file;
 uint64_t bytes = 0;
 public:
 HalFile() = default;
 explicit HalFile(const char* path) {
  auto stream = std::make_shared<std::ifstream>(path, std::ios::binary);
  if (stream->is_open()) { stream->seekg(0, std::ios::end); bytes = uint64_t(stream->tellg()); stream->seekg(0); file=stream; }
 }
 explicit operator bool() const { return bool(file) && file->is_open(); }
 uint64_t size() const { return bytes; }
 bool seek(uint64_t position) { if (!file || position>bytes) return false; file->clear(); file->seekg(position); return bool(*file); }
 int read(void* destination, size_t length) { if (!file) return -1; file->read(static_cast<char*>(destination), length); return int(file->gcount()); }
 void close() { file.reset(); bytes=0; }
};
struct HostStorage { HalFile open(const char* path, int) { return HalFile(path); } };
inline HostStorage Storage;
''')
    (STUBS / 'InflateReader.h').write_text(r'''#pragma once
#include <cstddef>
#include <cstdint>
#include <zlib.h>
enum class InflateStatus { Ok, Done, Error };
class InflateReader {
 z_stream stream{};
 bool initialized=false;
 public:
 ~InflateReader() { if(initialized) inflateEnd(&stream); }
 bool init(bool = false) { initialized = inflateInit2(&stream, -15) == Z_OK; return initialized; }
 void setSource(const uint8_t* source, size_t size) { stream.next_in=const_cast<Bytef*>(source); stream.avail_in=size; }
 InflateStatus readAtMost(uint8_t* out, size_t length, size_t* produced) {
  stream.next_out=out; stream.avail_out=length;
  int result=inflate(&stream, Z_FINISH); *produced=length-stream.avail_out;
  return result==Z_STREAM_END ? InflateStatus::Done : (result==Z_OK ? InflateStatus::Ok : InflateStatus::Error);
 }
};
''')
    entries = [('Alpha','First fixture article.'), ('Alphabet','Prefix fixture.'), ('Beta','>Earth'),
        ('Earth','Fixture Earth body, not Wikipedia content.'), ('Moon','Long fixture body. ' * 1500),
        ('Redirect A','>Redirect B'), ('Redirect B','>Redirect A'), ('Zulu','Last fixture article.')]
    prefix = 'This title shares more than thirty one bytes '
    entries += [(prefix + str(i), 'Long title fixture ' + str(i)) for i in range(6)]
    entries.sort(key=lambda entry: entry[0].lower())
    good = pack_blocks([(title+'\t'+body+'\n').encode() for title,body in entries])
    (WORK/'valid.cdb').write_bytes(good)
    bad = {'short': b'WCDB', 'magic': b'NOPE'+good[4:]}
    for label, position, value in [('blocks',4,0xffffffff), ('zero',4,0), ('entries',8,0),
        ('raw_large',52,32769), ('raw_wrong',52,3), ('compressed_large',48,40000), ('offset',44,0)]:
        mutated = bytearray(good); struct.pack_into('<I',mutated,position,value); bad[label]=bytes(mutated)
    bad['no_tab'] = pack_blocks([b'Bad record\n'])
    bad['nul'] = pack_blocks([b'Alpha\tBad\x00text\n'])
    bad['no_newline'] = pack_blocks([b'Alpha\tBad text'])
    for label,data in bad.items(): (WORK/(label+'.cdb')).write_bytes(data)
    damaged = bytearray(good)
    second_offset = struct.unpack_from('<I', damaged, 12+44+32)[0]
    struct.pack_into('<I', damaged, 12+44+36, 1)
    damaged[second_offset]=6
    (WORK/'cache.cdb').write_bytes(damaged)
    invalid_names = ','.join('"'+name+'.cdb"' for name in bad)
    cpp = r'''#include "WikiArchive.h"
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
int checks=0;
void check(bool value, const char* label) { ++checks; if(!value) throw std::runtime_error(label); }
int main(int argc, char** argv) {
 try {
  if(argc<2) return 2;
  std::filesystem::path root(argv[1]);
  auto path=[&](const char* name) { return (root/name).string(); };
  WikiArchive archive;
  check(!archive.ready(), "initially closed");
  check(!archive.open(path("missing.cdb").c_str()), "missing file rejected");
  check(archive.open(path("valid.cdb").c_str()), "open valid fixture");
  check(archive.entryCount()==14, "entry count");
  check(archive.first().title=="Alpha", "first title");
  check(archive.next().title=="Alphabet", "next title");
  check(archive.previous().title=="Alpha", "previous title");
  check(archive.previous().title=="Zulu", "previous wraps");
  check(archive.next().title=="Alpha", "next wraps");
  check(archive.search("eArTh").text=="Fixture Earth body, not Wikipedia content.", "ASCII case folding");
  check(archive.search("alph",true).title=="Alpha", "prefix match");
  check(!archive.search("not present").found, "absent exact match");
  check(!archive.search("").found, "empty query");
  check(!archive.search(std::string(1025,'x')).found, "oversized query");
  auto redirect=archive.search("Beta");
  check(redirect.found && redirect.title=="Beta -> Earth", "redirect title");
  check(redirect.text=="Fixture Earth body, not Wikipedia content.", "redirect body");
  check(archive.search("Redirect A").text.find("cyclic")!=std::string::npos, "redirect cycle bounded");
  const std::string prefix="This title shares more than thirty one bytes ";
  for(int i=0;i<6;++i) check(archive.search(prefix+std::to_string(i)).title==prefix+std::to_string(i), "duplicate truncated index key");
  check(archive.search(prefix,true).title==prefix+"0", "prefix across duplicated keys");
  check(archive.search("Moon").text.size()==27000, "large bounded article");
  for(int i=0;i<20;++i) check(archive.random().found, "random entry");
  const char* invalid[]={INVALID_NAMES};
  for(const char* name:invalid) { check(!archive.open(path(name).c_str()), name); check(!archive.ready(), "failure closes archive"); }
  check(archive.open(path("cache.cdb").c_str()), "open partially damaged fixture");
  check(!archive.search("Alphabet").found, "bad later DEFLATE block rejected");
  check(archive.first().text=="First fixture article.", "failed load invalidates cache");
  archive.close();
  check(!archive.first().found && !archive.next().found && !archive.previous().found && !archive.random().found, "closed navigation safe");
  if(argc>2) {
   check(archive.open(argv[2]), "open published Wikipedia WCDB");
   for(const char* title:{"Earth","Moon","Water","Canada"}) {
    auto entry=archive.search(title);
    check(entry.found && entry.text.size()>50, title);
    std::cout<<"REAL PACK lookup: "<<title<<" -> "<<entry.title<<" ("<<entry.text.size()<<" bytes)\n";
   }
  }
  std::cout<<checks<<" archive assertions passed (host adapters and zlib; not device tests).\n";
 } catch(const std::exception& error) { std::cerr<<"FAILED after "<<checks<<" checks: "<<error.what()<<"\n"; return 1; }
}
'''.replace('INVALID_NAMES',invalid_names)
    (WORK/'tests.cpp').write_text(cpp)
    command=['g++','-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',
        '-I'+str(STUBS), '-I'+str(ROOT/'src/activities/wiki'), str(ROOT/'src/activities/wiki/WikiArchive.cpp'),
        str(WORK/'tests.cpp'),'-lz','-o',str(WORK/'tests')]
    subprocess.run(command,check=True)
    subprocess.run([str(WORK/'tests'),str(WORK)],check=True)
    if '--skip-real' not in sys.argv:
        destination=WORK/'published-wikipedia.cdb'
        request=urllib.request.Request(PACK_URL,headers={'User-Agent':'crosspoint-wiki-x4-beta-build/1.0'})
        with urllib.request.urlopen(request, timeout=120) as response, destination.open('wb') as output:
            while chunk:=response.read(1024*1024): output.write(chunk)
        data=destination.read_bytes()
        if hashlib.sha256(data).hexdigest()!=PACK_SHA: raise ValueError('Published pack digest changed')
        magic,blocks,count=struct.unpack_from('<4sII',data)
        if magic!=b'WCDB': raise ValueError('Not WCDB')
        seen,max_raw=0,0
        for i in range(blocks):
            first,offset,compressed,raw=struct.unpack_from('<32sIII',data,12+44*i)
            if not 0<raw<=32768 or not 0<compressed<=34880 or offset<12+44*blocks or offset+compressed>len(data):
                raise ValueError('Published pack contains unsupported block bounds')
            decoded=zlib.decompress(data[offset:offset+compressed],-15)
            if len(decoded)!=raw or not decoded.endswith(b'\n') or b'\0' in decoded: raise ValueError('Bad published block')
            seen+=decoded.count(b'\n'); max_raw=max(max_raw,raw)
        if seen!=count: raise ValueError('Published entry count mismatch')
        report={'url':PACK_URL,'sha256':PACK_SHA,'bytes':len(data),'blocks':blocks,'entries':count,
            'max_raw_block_bytes':max_raw,'all_blocks_checked_with_host_zlib':True,'device_tested':False}
        (ROOT/'wiki-real-pack-report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
        subprocess.run([str(WORK/'tests'),str(WORK),str(destination)],check=True)

if __name__=='__main__': main()
