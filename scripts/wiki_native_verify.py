#!/usr/bin/env python3
"""Additional host verification using the exact firmware decompressor sources.
Runs existing host tests, then actual InflateReader/uzlib tests. Still not device tests.
"""
from pathlib import Path
import subprocess
import sys
import wiki_host_tests

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'wiki-test-build'
NATIVE = WORK / 'native'
FLAGS = ['-O1', '-g', '-Wall', '-Wextra', '-fsanitize=address,undefined',
         '-fno-omit-frame-pointer', '-ffunction-sections', '-fdata-sections']

def main():
    wiki_host_tests.main()
    NATIVE.mkdir(exist_ok=True)
    subprocess.run(['gcc', '-std=c99', *FLAGS, '-Ilib/uzlib/src', '-c',
        'lib/uzlib/src/tinflate.c', '-o', str(NATIVE/'tinflate.o')], cwd=ROOT, check=True)
    tests=(WORK/'tests.cpp').read_text().replace('host adapters and zlib', 'host adapters and actual CrossPoint uzlib')
    (NATIVE/'tests.cpp').write_text(tests)
    def compile_cpp(source, destination, extra=()):
        subprocess.run(['g++', '-std=c++20', *FLAGS, '-Werror',
            '-Ilib/InflateReader', '-Ilib/uzlib/src', '-I'+str(WORK/'stubs'),
            '-Isrc/activities/wiki', 'src/activities/wiki/WikiArchive.cpp',
            'lib/InflateReader/InflateReader.cpp', str(source), str(NATIVE/'tinflate.o'),
            '-Wl,--gc-sections', *extra, '-o', str(destination)], cwd=ROOT, check=True)
    compile_cpp(NATIVE/'tests.cpp', NATIVE/'tests')
    args=[str(NATIVE/'tests'),str(WORK)]
    real=WORK/'published-wikipedia.cdb'
    if '--skip-real' not in sys.argv: args.append(str(real))
    subprocess.run(args,check=True)
    if '--skip-real' in sys.argv: return
    program=r'''#include <InflateReader.h>
#include <zlib.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
uint32_t u32(const uint8_t* p) { return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24); }
void check(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
int main(int argc,char** argv) {
 try {
  check(argc==2,"Pass the published pack path");
  std::ifstream file(argv[1],std::ios::binary); check(bool(file),"Open pack");
  std::array<uint8_t,12> header{}; file.read(reinterpret_cast<char*>(header.data()),header.size());
  check(file.gcount()==12&&!std::memcmp(header.data(),"WCDB",4),"Pack header");
  const uint32_t blocks=u32(header.data()+4);
  std::vector<uint8_t> compressed(34880), expected(32769), actual(32769);
  uint64_t total=0;
  for(uint32_t index=0;index<blocks;++index) {
   file.clear(); file.seekg(12+uint64_t(index)*44);
   std::array<uint8_t,44> record{}; file.read(reinterpret_cast<char*>(record.data()),record.size());
   check(file.gcount()==44,"Read index");
   uint32_t offset=u32(record.data()+32), count=u32(record.data()+36), raw=u32(record.data()+40);
   check(count>0&&count<=34880&&raw>0&&raw<=32768,"Block bounds");
   file.seekg(offset); file.read(reinterpret_cast<char*>(compressed.data()),count);
   check(file.gcount()==count,"Read compressed block");
   z_stream z{}; check(inflateInit2(&z,-15)==Z_OK,"Initialize host reference decoder");
   z.next_in=compressed.data();z.avail_in=count;z.next_out=expected.data();z.avail_out=expected.size();
   int result=inflate(&z,Z_FINISH); auto expectedSize=z.total_out; inflateEnd(&z);
   check(result==Z_STREAM_END&&expectedSize==raw,"Reference block decoding");
   InflateReader decoder; check(decoder.init(false),"Initialize actual firmware decoder");
   decoder.setSource(compressed.data(),count);
   size_t produced=0;
   check(decoder.readAtMost(actual.data(),raw+1,&produced)==InflateStatus::Done&&produced==raw,
         "Firmware block decoding");
   check(std::memcmp(actual.data(),expected.data(),raw)==0,"Firmware/reference bytes differ");
   total+=raw;
  }
  std::cout<<"Actual CrossPoint InflateReader/uzlib matches host zlib for ALL "<<blocks
           <<" published Wikipedia blocks ("<<total<<" uncompressed bytes). Host ASan/UBSan; not device tests.\n";
 } catch(const std::exception& error) { std::cerr<<error.what()<<"\n";return 1; }
}
'''
    (NATIVE/'all-blocks.cpp').write_text(program)
    compile_cpp(NATIVE/'all-blocks.cpp',NATIVE/'all-blocks',['-lz'])
    subprocess.run([str(NATIVE/'all-blocks'),str(real)],check=True)

if __name__=='__main__': main()
