from pathlib import Path
R=Path(__file__).resolve().parents[1]
BASE={'platformio.local.ini': '18d61a2ecf9b81dfed6529553561b7a10cc7c71881dedea2c7feefdbf251dadc', '.github/wiki464_host/tests.cpp': '0beef7269b5553f2dc38de59ccbbd6e1a4530b72fdd12c80894d70f41e0522e1', 'src/activities/wiki/WikiIndexJob.h': 'aff02fd760600a74a3eccdfb70f409c1be920ed1dbd112be99713d40641209d2', 'src/activities/wiki/WikiIndexJob.cpp': '19319e2d1d7e75d09ae5222221a4860690191540a90c4a632c3e27964d1f22b3', 'src/activities/wiki/WikiActivity.h': 'dff3351bf622cdc19a3ed29a1931add186ea560f6c3db02133229581b14ab05e', 'src/activities/wiki/WikiActivity.cpp': '2d0443d16add8a006a7f87e2ae2cc670f250baceda79ae763468dada0b3f8df7'}
AFTER={'platformio.local.ini': 'e79c7d651531433f4917f59256eb9e0e5684a0f3583748633f41cafe93c9544b', '.github/wiki464_host/tests.cpp': '4a3942212e87a4ec80b3053fd9220ab87e8d57591f3924cdfd45866efebce635', 'src/activities/wiki/WikiIndexJob.h': '6f496633d3aa632ca95c73e7ebeb7068f88d32e0bf56a4c3ae9349075dc6b3c2', 'src/activities/wiki/WikiIndexJob.cpp': '8d0fa359727aaa51c0282f27c7492e58c0f38bf100955df43e3745ab75c4962a', 'src/activities/wiki/WikiActivity.h': 'fb30f7c3a697a9c1f480beb8558ebe0cfa968c284d9a65ae5f282fad03f56330', 'src/activities/wiki/WikiActivity.cpp': '3c2a82ebccecdf01b6c439fe598d3a47d48aa84079b4ebe42b2f0dc726a79b86'}
import hashlib
for f,digest in BASE.items():
 assert hashlib.sha256((R/f).read_bytes()).hexdigest()==digest, f
def edit(file,a,b):
 p=R/file;s=p.read_text();assert s.count(a)==1,(file,a[:70],s.count(a));p.write_text(s.replace(a,b))
h='src/activities/wiki/WikiIndexJob.h';j='src/activities/wiki/WikiIndexJob.cpp';a='src/activities/wiki/WikiActivity.cpp'
edit(h,'  static constexpr uint32_t RUN = 64;', '''  // Keep RUN and every on-disk/checkpoint layout compatible with 4.6.4.1.
  static constexpr uint32_t RUN = 64;
  static constexpr size_t SCAN_STEP_BYTES = READ_BYTES * 8;
  static constexpr uint32_t STEP_MS = 8;
  static constexpr uint32_t SORT_STEP_RECORDS = 256;
  static constexpr uint32_t CACHE_RECORDS = 64;''')
edit(h,'std::array<uint8_t,60*32> bytes{}','std::array<uint8_t,60*CACHE_RECORDS> bytes{}')
s=(R/j).read_text();start=s.index('bool WikiIndexJob::scanStep(){');end=s.index('\nbool WikiIndexJob::finishScan()',start)
s=s[:start]+'''bool WikiIndexJob::scanStep(){
 // Refill the same 8 KiB buffer within a bounded work quantum. Previously even
 // a cheap buffer forced a trip through input/USB/battery handling and delay(1).
 // Start timing BEFORE read(): a slow card must not grant a fresh CPU budget.
 const uint32_t start=millis();size_t processed=0,checked=0;
 while(processed<SCAN_STEP_BYTES){
  if(inputPos_==inputSize_){
   if(scanned_==size_)return finishScan();
   if(processed&&uint32_t(millis()-start)>=STEP_MS)break;
   size_t n=size_t(std::min<uint64_t>(input_.size(),size_-scanned_));
   // A resumed page boundary may be unaligned. Align the next full transfer
   // without changing saved offsets or reading outside the source file.
   if(scanned_&511u)n=std::min(n,size_t(512-(scanned_&511u)));
   const int got=source_.read(input_.data(),n);
   if(got<=0||size_t(got)>n){fail("XML read failed; check SD card and resume");return false;}
   inputPos_=0;inputSize_=size_t(got);
  }
  if(lex_==Lex::Text&&!inTitle_){
   const auto* begin=input_.data()+inputPos_;
   const size_t remaining=std::min(inputSize_-inputPos_,SCAN_STEP_BYTES-processed);
   const auto* next=static_cast<const uint8_t*>(std::memchr(begin,'<',remaining));
   const size_t span=next?size_t(next-begin):remaining;
   if(std::memchr(begin,0,span)){fail("XML contains a NUL byte; use plain UTF-8 XML");return false;}
   inputPos_+=span;scanned_+=span;processed+=span;
   if(processed-checked>=256){checked=processed;if(uint32_t(millis()-start)>=STEP_MS)break;}
   if(inputPos_==inputSize_||processed==SCAN_STEP_BYTES)continue;
  }
  if(!parse(char(input_[inputPos_++]),scanned_))return false;
  ++scanned_;++processed;
  if(processed-checked>=256){checked=processed;if(uint32_t(millis()-start)>=STEP_MS)break;}
 }
 // Preserve both the byte and time checkpoint intervals and all sync checks.
 if(scanned_-lastCheckpointWork_>=8*1024*1024||uint32_t(millis()-lastCheckpointAt_)>=15000){if(!checkpoint()){fail("Checkpoint write failed; free SD space then resume");return false;}}
 return true;
}''' + s[end:];(R/j).write_text(s)
edit(j,'if(id<cache.start||uint64_t(id)>=uint64_t(cache.start)+cache.count){cache.start=id;cache.count=std::min<uint32_t>(32,count_-id);if(!f.seek64(SH+uint64_t(id)*SR)||!readAll(f,cache.bytes.data(),size_t(cache.count)*SR)){cache.count=0;return false;}}', '''if(id<cache.start||uint64_t(id)>=uint64_t(cache.start)+cache.count){
  // Each cache owns one handle. A consecutive refill is already positioned;
  // avoid a redundant FAT seek. Reopened handles always reset cache.count.
  const bool consecutive=cache.count&&uint64_t(id)==uint64_t(cache.start)+cache.count;
  cache.start=id;cache.count=std::min<uint32_t>(CACHE_RECORDS,count_-id);
  if((!consecutive&&!f.seek64(SH+uint64_t(id)*SR))||!readAll(f,cache.bytes.data(),size_t(cache.count)*SR)){cache.count=0;return false;}
 }''')
edit(j,'for(uint32_t work=0;work<RUN;++work)', 'for(uint32_t work=0;work<SORT_STEP_RECORDS;++work)')
edit(j,'uint32_t(millis()-start)>=8)break;\n }return true;', 'uint32_t(millis()-start)>=STEP_MS)break;\n }return true;')
edit(j,'case Phase::Runs:ok=runStep();break;', '''case Phase::Runs:{
  const uint32_t start=millis();
  for(unsigned group=0;group<SORT_STEP_RECORDS/RUN;++group){
   ok=runStep();
   if(!ok||phase_!=Phase::Runs||uint32_t(millis()-start)>=STEP_MS)break;
  }
  break;}''')
edit(a,'uint32_t(millis()-indexRefreshAt_) >= 3000','uint32_t(millis()-indexRefreshAt_) >= 8000')
edit('src/activities/wiki/WikiActivity.h','  uint32_t indexRefreshAt_ = 0;', '''  uint32_t indexRefreshAt_ = 0;
  uint64_t indexRateStartBytes_ = 0;
  uint32_t indexRateStartAt_ = 0, indexRateKBs_ = 0;''')
edit(a,'      indexRefreshAt_ = millis(); requestUpdate();', '''      const uint32_t now = millis(), elapsed = now - indexRateStartAt_;
      if (oldPhase == WikiIndexJob::Phase::Scan && indexProgress_.phase == oldPhase &&
          elapsed && indexProgress_.scanned >= indexRateStartBytes_) {
        // Bytes/ms equals decimal kB/s. Include UI/input/SD overhead in the rate.
        indexRateKBs_ = uint32_t((indexProgress_.scanned - indexRateStartBytes_) / elapsed);
      } else indexRateKBs_ = 0;
      indexRateStartBytes_ = indexProgress_.scanned; indexRateStartAt_ = now;
      indexRefreshAt_ = now; requestUpdate();''')
edit(a,'  resetKeys(); requestUpdate();\n}\n\nvoid WikiActivity::renderIndex()', '''  indexRateStartAt_ = indexRefreshAt_; indexRateStartBytes_ = indexProgress_.scanned; indexRateKBs_ = 0;
  resetKeys(); requestUpdate();
}

void WikiActivity::renderIndex()''')
edit(a,'  renderer.drawCenteredText(SMALL_FONT_ID,y,stage);y+=fh+14;', '''  if(indexProgress_.phase==WikiIndexJob::Phase::Scan && indexRateKBs_){
    std::snprintf(bytes,sizeof(bytes),"Scanning XML - %lu kB/s",static_cast<unsigned long>(indexRateKBs_));
    stage=bytes;
  }
  renderer.drawCenteredText(SMALL_FONT_ID,y,stage);y+=fh+14;''')
p=R/'platformio.local.ini';p.write_text(p.read_text().replace('1.6.0-wiki-4.6.4.1','1.6.0-wiki-4.6.4.2'))
p=R/'.github/wiki464_host/tests.cpp';p.write_text(p.read_text().replace('<=WikiIndexJob::READ_BYTES,"bounded scan quantum"','<=WikiIndexJob::SCAN_STEP_BYTES,"bounded scan quantum"'))
for f,digest in AFTER.items():
 assert hashlib.sha256((R/f).read_bytes()).hexdigest()==digest, f
print('Applied and hash-verified 4.6.4.2 speed changes.')
