#!/usr/bin/env python3
"""Compile the REAL HalStorage.cpp with a mock SD driver, not a mock HalFile.
The assertion, unique_ptr ownership, moves, destructors and close API are production.
FreeRTOS serialization and SD media are host adapters, NOT device emulation.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, signal, subprocess, tempfile
R = Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--expect-bug', action='store_true')
args=ap.parse_args()
S=['src/activities/wiki/'+n for n in ['WikiArchive.cpp','WikiArchive.h','WikiIndexJob.cpp','WikiIndexJob.h','DiskTitleIndex.cpp','DiskTitleIndex.h','WikiText.cpp','WikiText.h']]
S+=['lib/Serialization/RecoverableFile.h','lib/InflateReader/InflateReader.cpp','lib/InflateReader/InflateReader.h','lib/uzlib/src/tinflate.c','lib/hal/HalStorage.cpp','lib/hal/HalStorage.h']
def hashes():return {p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in S}
before=hashes()
cases=['normal','readonly-reopen','scan-resume','scan-crash','checkpoint-crc','runs-resume','merge-resume','verify-resume','short-write','sync-fault','rename-fault','read-fault','accepted-generation','search-corrupt','source-change','lexer','split-boundary','oversized-title','large-article','malformed','dtd','empty']
extra=['unused-job','failed-job','missing-source','failed-open','paused-job','repeat-close','failed-open-handle','moved-handle','raw-empty-close']
flags=['-O0','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-ffunction-sections','-fdata-sections']
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
with tempfile.TemporaryDirectory(prefix='wiki4641-real-hal-') as tmp:
 w=Path(tmp)
 for n in ['Print.h','Logging.h','esp_random.h']:
  shutil.copyfile(R/'.github/wiki464_host'/n,w/n)
 # Arduino String must be a distinct type for real HalStorage overloads.
 with (w/'Print.h').open('a') as f:f.write('\n#include <string>\nclass String : public std::string { public: using std::string::string; String()=default; String(const std::string& s):std::string(s){} };\n')
 (w/'Arduino.h').write_text('#pragma once\n#include <cstdint>\n#include "Print.h"\ninline unsigned long millis(){static unsigned long t=0;return ++t;}\ninline void delay(unsigned long){}\n')
 (w/'FS.h').write_text('#pragma once\n')
 (w/'common').mkdir();(w/'common/FsApiConstants.h').write_text('#pragma once\n#include <fcntl.h>\nusing oflag_t=int;\n')
 (w/'freertos').mkdir();(w/'freertos/semphr.h').write_text('''#pragma once
#include <mutex>
using SemaphoreHandle_t=std::recursive_mutex*;
constexpr unsigned portMAX_DELAY=~0u;
inline SemaphoreHandle_t xSemaphoreCreateRecursiveMutex(){static std::recursive_mutex m;return &m;}
inline int xSemaphoreTakeRecursive(SemaphoreHandle_t m,unsigned){m->lock();return 1;}
inline int xSemaphoreGiveRecursive(SemaphoreHandle_t m){m->unlock();return 1;}
''')
 # Reuse ONLY the low-level simulated media. No HalFile adapter is compiled.
 sd=(R/'.github/wiki464_host/HalStorage.h').read_text().replace('HalFile','FsFile').replace('HalStorage','SDCardManager')
 sd=sd.replace('#define Storage SDCardManager::getInstance()','')
 sd=sd.replace('  explicit operator bool() const', '''  bool isOpen() const { return bool(data_); }
  size_t getName(char* out,size_t n){if(n)out[0]=0;return 0;}
  uint64_t fileSize() const { return size(); }
  bool seekSet(uint64_t p){return seek64(p);}
  int available() const { return data_ ? int(std::min<size_t>(INT32_MAX,data_->size()-pos_)):0; }
  bool rename(const char*){return false;}
  bool isDirectory() const {return false;}
  void rewindDirectory(){}
  FsFile openNextFile(){return {};}
  explicit operator bool() const''')
 sd=sd.replace('  struct Transaction {};','''  struct Transaction {};
  bool begin(){return true;} bool ready()const{return true;} void shutdown(){}
  std::vector<String> listFiles(const char*,int){return {};}
  String readFile(const char*){return {};}
  bool readFileToStream(const char*,Print&,size_t){return false;}
  size_t readFileToBuffer(const char*,char*,size_t,size_t){return 0;}
  bool writeFile(const char*,const String&){return false;}
  bool rmdir(const char*){return false;} bool removeDir(const char*){return false;}
  bool openFileForRead(const char*,const char* p,FsFile& f){f=open(p,O_RDONLY);return bool(f);}
  bool openFileForWrite(const char*,const char* p,FsFile& f){f=open(p,O_WRONLY|O_CREAT|O_TRUNC);return bool(f);}
''')
 (w/'SDCardManager.h').write_text(sd)
 test=(R/'.github/wiki464_host/tests.cpp').read_text()
 anchor=' if(name=="normal"||name=="readonly-reopen")'
 assert test.count(anchor)==1
 test=test.replace(anchor,''' if(name=="unused-job"){WikiIndexJob job;}
 else if(name=="failed-job"){WikiIndexJob job;job.fail("injected-before-open");job.fail("repeated-cleanup");}
 else if(name=="missing-source"){WikiIndexJob job;auto norm=+[](const std::string& s){return s;};check(!job.begin("/missing.xml","/.crosspoint/wiki/missing-464.xwi",100,0,norm,false,0),"missing source error");}
 else if(name=="failed-open"){WikiArchive a;check(!a.open("/test.xml")&&a.indexRequired(),"prompt");faults.failOpen=true;check(!a.beginIndex(),"failed source open reports error");faults.failOpen=false;check(a.beginIndex(),"retry succeeds");finish(a);validate(a);}
 else if(name=="paused-job"){WikiArchive a;start(a);check(a.pauseIndex(),"pause");check(a.pauseIndex(),"repeat pause");a.close();a.close();}
 else if(name=="repeat-close"){auto f=Storage.open("/test.xml");check(f.isOpen(),"open");check(f.close(),"first close");check(!f.isOpen(),"closed");f.close();}
 else if(name=="failed-open-handle"){auto f=Storage.open("/absent.xml");check(!f,"failed open");f.close();}
 else if(name=="moved-handle"){auto f=Storage.open("/test.xml");auto moved=std::move(f);check(!f&&moved,"ownership transferred");if(f)f.close();check(moved.close(),"new owner closes");}
 else if(name=="raw-empty-close"){HalFile empty;empty.close();throw std::runtime_error("Production assertion was disabled");}
 else if(name=="normal"||name=="readonly-reopen")''')
 (w/'tests.cpp').write_text(test)
 def run(cmd):subprocess.run(cmd,cwd=R,check=True)
 run(['gcc','-std=c99',*flags,'-Ilib/uzlib/src','-c','lib/uzlib/src/tinflate.c','-o',str(w/'tinflate.o')])
 run(['g++','-std=c++20',*flags,'-no-pie','-Wl,--gc-sections','-I'+str(w),'-Ilib/hal','-Isrc/activities/wiki','-Ilib/Serialization','-Ilib/InflateReader','-Ilib/uzlib/src','-include',str(w/'SDCardManager.h'),*[str(R/p) for p in S if p.endswith('.cpp')],str(w/'tinflate.o'),str(w/'tests.cpp'),'-o',str(w/'test')])
 results=[]
 selected=['normal','unused-job','failed-job','raw-empty-close'] if args.expect_bug else cases+extra
 for case in selected:
  p=subprocess.run([str(w/'test'),case],cwd=R,capture_output=True,text=True,timeout=120,env=env)
  expected_abort=args.expect_bug or case=='raw-empty-close'
  ok=(p.returncode==-signal.SIGABRT and 'impl != nullptr' in p.stderr and 'HalStorage.cpp' in p.stderr) if expected_abort else p.returncode==0
  result={'case':case,'passed':ok,'expected_production_assert':expected_abort,'returncode':p.returncode,'output':p.stdout+p.stderr}
  results.append(result);print(('PASS ' if ok else 'FAIL ')+case+': '+(p.stdout+p.stderr).strip(),flush=True)
 report={'source_hashes':before,'source_unchanged':before==hashes(),'cases':results,'production_HAL_compiled':True,'HalFile_mock_used':False,'SD_driver':'memory/fault adapter','mutex':'host recursive mutex','sanitizers':['ASan','UBSan'],'baseline_bug_reproduction':args.expect_bug,'hardware_tested':False}
 name='wiki4641-before.json' if args.expect_bug else 'wiki4641-real-hal-results.json'
 (R/name).write_text(json.dumps(report,indent=2)+'\n')
 assert report['source_unchanged'] and all(r['passed'] for r in results),'Real HAL regression failed'
 print(f'{len(results)}/{len(results)} cases passed',flush=True)
