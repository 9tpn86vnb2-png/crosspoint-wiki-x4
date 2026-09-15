#!/usr/bin/env python3
"""Final-tree test and packaging gates. Never edits or flashes firmware bytes."""
from pathlib import Path
import argparse,base64,hashlib,json,lzma,os,re,shutil,subprocess,sys,tarfile
R=Path('.').resolve();sys.path.insert(0,str(R/'scripts'))
VERSION='1.6.0-wiki-4.6.3'
FILES=['platformio.local.ini','lib/hal/HalStorage.h','lib/hal/HalStorage.cpp','lib/Serialization/PersistableStore.cpp','lib/Serialization/RecoverableFile.h','src/FinishedBooksStore.cpp','src/FinishedBooksStore.h','src/RecentBooksStore.cpp','src/RecentBooksStore.h','src/activities/reader/ReaderActivity.cpp','src/activities/reader/ReaderActivity.h','src/activities/reader/EpubReaderActivity.cpp','src/activities/reader/EpubReaderActivity.h','src/activities/reader/ReaderNavigationQueue.h','src/activities/wiki/WikiArchive.cpp','src/activities/wiki/WikiArchive.h','src/activities/wiki/DiskTitleIndex.cpp','src/activities/wiki/DiskTitleIndex.h','src/activities/wiki/WikiActivity.cpp','src/activities/wiki/WikiHeading.cpp','src/activities/wiki/WikiText.cpp','lib/Epub/Epub/Page.cpp','lib/Epub/Epub/blocks/TextBlock.cpp','lib/Epub/Epub/blocks/TextBlock.h','lib/hal/HalPowerManager.h','src/main.cpp']
FLAGS=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie','-ffunction-sections','-fdata-sections','-Wl,--gc-sections']
def hashes():return {n:hashlib.sha256((R/n).read_bytes()).hexdigest() for n in FILES}
def run(args,**kw):return subprocess.run(args,cwd=R,check=True,**kw)
def prepare():
 # Recover ONLY complete, new-file test entries from the previously persisted
 # partial patch. Its firmware edits are NOT applied. The readable recovered
 # test sources are retained in the artifact for inspection and reproducibility.
 chunk=(R/'.github/wiki463.delta.xz.b64.0').read_text().strip()
 prefix=lzma.LZMADecompressor().decompress(base64.b64decode(chunk)).decode('utf-8',errors='ignore')
 recovered=[]
 for entry in prefix.split('diff --git ')[1:-1]:
  head=entry.splitlines()[0];m=re.fullmatch(r'a/(\S+) b/(\S+)',head)
  if not m or m[1]!=m[2] or not m[1].startswith('.github/wiki463_host/'):continue
  assert 'new file mode' in entry
  lines=entry.splitlines(keepends=True);at=next(i for i,s in enumerate(lines) if s.startswith('@@ '))
  h=re.fullmatch(r'@@ -0,0 \+1,(\d+) @@\n',lines[at]);assert h
  body=''.join(s[1:] for s in lines[at+1:] if s.startswith('+'))
  assert len(body.splitlines())==int(h[1]),m[1]
  p=R/m[1];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body);recovered.append(m[1])
 required=['HalStorage.h','Print.h','Arduino.h','Logging.h','RecentBooksStore.h','ObfuscationUtils.h','tests.cpp','run.py']
 for name in required:assert (R/'.github/wiki463_host'/name).is_file(),('Missing recovered host fixture',name,recovered)
 print('Recovered readable host tests:',recovered,flush=True)
 (R/'wiki463-source-hashes.json').write_text(json.dumps(hashes(),indent=2)+'\n')


def parser_tests():
 import wiki_table_tests as table
 original=table.write_stubs
 def adapters(work):
  stubs=original(work)
  p=stubs/'HalStorage.h';s=p.read_text()
  s=s.replace('uint64_t size()const{return bytes_;}', 'uint64_t size()const{return bytes_;}uint64_t fileSize64()const{return bytes_;}uint64_t position(){if(!f_)return 0;return writable_?uint64_t(f_->tellp()):uint64_t(f_->tellg());}bool seek64(uint64_t p){return seek(p);}')
  s=s.replace('void flush(){if(f_)f_->flush();}', 'bool sync(){if(!f_)return false;f_->flush();return bool(*f_);}void flush(){if(f_)f_->flush();}')
  s=s.replace('struct HostStorage{','class HalStorage{public:struct Transaction{};};\nstruct HostStorage{bool exists(const char*p){return std::filesystem::exists(map(p));}bool remove(const char*p){return std::filesystem::remove(map(p));}bool rename(const char*a,const char*b){std::error_code ec;if(exists(b))return false;std::filesystem::rename(map(a),map(b),ec);return !ec;}')
  p.write_text(s);return stubs
 def compile_actual(work,srcdir,cpp,name):
  obj=work/'tinflate.o'
  run(['gcc','-std=c99',*FLAGS,'-Ilib/uzlib/src','-c','lib/uzlib/src/tinflate.c','-o',str(obj)])
  out=work/name
  run(['g++','-std=c++20',*FLAGS,'-Ilib/InflateReader','-Ilib/uzlib/src','-Ilib/Serialization','-I'+str(work/'stubs'),'-I'+str(srcdir),str(srcdir/'WikiArchive.cpp'),str(srcdir/'WikiText.cpp'),str(srcdir/'DiskTitleIndex.cpp'),'lib/InflateReader/InflateReader.cpp',str(obj),str(cpp),'-o',str(out)])
  return out
 table.write_stubs=adapters;table.compile_test=compile_actual
 saved=sys.argv;sys.argv=['wiki_table_tests.py']
 try:table.main()
 finally:sys.argv=saved
 # Exercise the actual firmware inflater, not the zlib adapter used by the old tests.
 w=R/'wiki-table-test-build';p=w/'fuzz.cpp'
 p.write_text('''#include <InflateReader.h>
#include <array>
#include <cassert>
#include <random>
#include <iostream>
int main(){std::mt19937 rng(463);std::array<uint8_t,512>src{};std::array<uint8_t,32769>dst{};
for(unsigned i=0;i<50000;++i){size_t n=1+rng()%src.size(),cap=1+rng()%dst.size();for(size_t j=0;j<n;++j)src[j]=uint8_t(rng());InflateReader d;assert(d.init(false));d.setSource(src.data(),n);size_t out=0;d.readAtMost(dst.data(),cap,&out);assert(out<=cap);}
std::cout<<"PASS 50,000 seeded malformed-input firmware-inflater trials (ASan/UBSan)\\n";}
''')
 run(['g++','-std=c++20',*FLAGS,'-Ilib/InflateReader','-Ilib/uzlib/src','lib/InflateReader/InflateReader.cpp',str(w/'tinflate.o'),str(p),'-o',str(w/'fuzz')]);run([str(w/'fuzz')])


def heading_tests():
 path=R/'scripts/wiki_heading_tests.py';source=path.read_text()
 adapter='''
 enum RenderMode{BW,GRAYSCALE_MSB,GRAYSCALE_LSB};RenderMode mode=BW;
 RenderMode getRenderMode()const{return mode;}
 int getTextWidth(int id,const char*t,EpdFontFamily::Style s=EpdFontFamily::REGULAR)const{int w=0,h=0;auto it=fonts.find(id);if(it!=fonts.end())it->second.getTextDimensions(t,&w,&h,s);return w;}
 int getTextHeight(int id)const{return getLineHeight(id);}
 void drawLine(int x0,int y0,int x1,int y1,int thick=1,bool state=true)const{if(y0!=y1)throw std::runtime_error("unsupported host line");for(int x=x0;x<=x1;++x)for(int dy=0;dy<thick;++dy)if(x>=0&&x<width&&y0+dy>=0&&y0+dy<height)drawPixel(x,y0+dy,state);}
'''
 source=source.replace('struct GfxRenderer {','struct GfxRenderer {'+adapter,1)
 source=source.replace("src=['src/activities/wiki/WikiHeading.cpp'","src=['src/activities/wiki/WikiText.cpp','src/activities/wiki/WikiHeading.cpp'",1)
 source=source.replace("common=['-O0'","common=['-fno-pie','-no-pie','-O0'",1)
 a='check(gfx.pixels.size()==7,"2-bit coverage polarity");';assert source.count(a)==1
 source=source.replace(a,a+'''gfx.mode=GfxRenderer::GRAYSCALE_MSB;gfx.pixels.clear();WikiHeading::draw(gfx,7,0,0,"A",1,1,400,600);check(gfx.pixels.size()==5,"MSB coverage");gfx.mode=GfxRenderer::GRAYSCALE_LSB;gfx.pixels.clear();WikiHeading::draw(gfx,7,0,0,"A",1,1,400,600);check(gfx.pixels.size()==3,"LSB coverage");gfx.mode=GfxRenderer::BW;''',1)
 namespace={'__file__':str(path),'__name__':'wiki463_heading_adapter'};exec(compile(source,str(path),'exec'),namespace);namespace['main']()


def test():
 before=hashes();assert before==json.loads((R/'wiki463-source-hashes.json').read_text()),'Build changed reviewed production source'
 deps=R/'.pio/libdeps/wiki_x4_beta/ArduinoJson/src';assert (deps/'ArduinoJson.h').is_file()
 result=run([sys.executable,'.github/wiki463_host/run.py','--json',str(deps)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(result.stdout);(R/'wiki463-host-tests.log').write_text(result.stdout)
 parser_tests();heading_tests()
 if (R/'.github/wiki463_text_tests.py').is_file():run([sys.executable,'.github/wiki463_text_tests.py'])
 get=lambda p:(R/p).read_text()
 e=get('src/activities/reader/EpubReaderActivity.cpp');h=get('src/activities/reader/EpubReaderActivity.h');w=get('src/activities/wiki/WikiActivity.cpp');p=get('lib/Serialization/PersistableStore.cpp');f=get('src/FinishedBooksStore.cpp');t=get('lib/Epub/Epub/blocks/TextBlock.cpp')
 loop=e[e.index('void EpubReaderActivity::loop()'):e.index('float EpubReaderActivity::displayedBookProgress')]
 compact=lambda s:re.sub(r'\s+','',s)
 checks={
 'version':get('platformio.local.ini').count(VERSION)==2,
 'original-X4':'-DFREEINK_DEVICE_X4=1' in get('platformio.local.ini'),
 '10ms-power-save':bool(re.search(r'READER_POWER_SAVE_POLL_MS\s*=\s*10\s*;',get('lib/hal/HalPowerManager.h'))),
 'no-light-sleep':'esp_light_sleep_start' not in get('src/main.cpp'),
 'capture-before-dispatch':loop.index('detectPageTurn(mappedInput)')<loop.index('pendingManualTurns.front()'),
 'optional-work-after-input':loop.index('pendingManualTurns.front()')<loop.index('performIdlePreparation()'),
 'no-single-slot-overwrite':not re.search(r'pendingManualTurn\b',e+h),
 'long-press-queue':'Action::SkipNext' in loop and 'Action::RotateNext' in loop,
 'bounded-overflow-report':'navigationQueueFull.store(true' in loop,
 'prepared-page-consumed':'p=std::move(preparedNextPage)' in compact(e),
 'centralized-cache-invalidation':e.count('section.reset();')==1,
 'heap-gates':'ESP.getMaxAllocHeap()<32*1024' in compact(e),
 'completion-inclusive':'float(section->currentPage+1)' in compact(e) and 'displayedBookProgress()>=99.5f' in compact(e),
 'completion-success-only':'finishedRecorded=RECENT_BOOKS.markFinished' in compact(get('src/activities/reader/ReaderActivity.cpp')),
 'bounded-save-retry':'finishedSaveAttempts>=3' in compact(get('src/activities/reader/ReaderActivity.cpp')),
 'verified-JSON':'measureJson(doc)' in p and 'out.sync()' in p and 'matchesFile(tmp.c_str(),doc,expected)' in compact(p),
 'catalog-rollback':'rollback.truncate(previousSize)' in f and 'repair.truncate(validEnd)' in f,
 'duplicate-read-errors-propagated':'if(!findPath(book.path,found))returnfalse' in compact(f),
 'bounded-search-index':'DiskTitleIndex' in get('src/activities/wiki/WikiArchive.h'),
 'fallback-linear-search':'for(uint32_ti=0;i<entries_;++i)' in compact(get('src/activities/wiki/WikiArchive.cpp')),
 'geometry-clip':get('lib/Epub/Epub/Page.cpp').count('glyphIntersectsStrip')==3,
 'bidi-same-allocation':'size + numWords' in t and 'size + wc' in t,
 'ruby-cache':'preparedRubyOffsets' in t,
 'Wiki-font-controls':'TextSettingsActivity' in w and 'sdFontFamilyName' in w,
 'Wiki-logo-heading-save':'WikiLogo::draw' in w and 'WikiHeading::drawRich' in w and 'Save Article' in w,
 'tables-retained':'renderTableBlock' in w,
 'no-global-LTO':'-flto' not in get('platformio.local.ini'),
 'source-unchanged-by-tests':before==hashes(),
 }
 for name,ok in checks.items():print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 report={'version':VERSION,'checks':checks,'kind':'Static final-source integration checks, not hardware emulation','hardware_tested':False,'production_sources_unchanged_by_tests':before==hashes()}
 (R/'wiki463-final-contracts.json').write_text(json.dumps(report,indent=2)+'\n');assert all(checks.values())


def package():
 from wiki_package import inspect,partitions
 b=R/'.pio/build/wiki_x4_beta';out=R/'wiki463-dist';image=(b/'firmware.bin').read_bytes();info=inspect(image)
 assert info['app_descriptor_version']==VERSION and VERSION.encode()+b'\0' in image
 table=partitions((b/'partitions.bin').read_bytes());apps=[p for p in table if p['type']==0]
 assert apps and all(len(image)<=p['size'] for p in apps)
 app0=next(p for p in apps if p['label']=='app0');assert app0['offset']==0x10000 and app0['size']==0x640000
 bad=bytearray(image);bad[256]^=1
 try:inspect(bytes(bad))
 except ValueError:pass
 else:raise AssertionError('Modified image was not rejected')
 checks=json.loads((R/'wiki463-final-contracts.json').read_text());host=json.loads((R/'wiki463-host-results.json').read_text())
 assert all(checks['checks'].values()) and all(c['pass'] for c in host['cases']) and host['real_arduinojson']
 assert hashes()==json.loads((R/'wiki463-source-hashes.json').read_text())
 out.mkdir(exist_ok=False);name='CrossPoint-Wiki-4.6.3-X4-experimental.bin';(out/name).write_bytes(image)
 for n in ['firmware.elf','firmware.map']:
  assert (b/n).is_file(),n;shutil.copy2(b/n,out/n)
 for n in ['wiki-build.log','wiki463-host-tests.log','wiki463-host-results.json','wiki463-final-contracts.json','wiki463-source-hashes.json']:
  shutil.copy2(R/n,out/n)
 for p in R.glob('wiki463-text-*.json'):shutil.copy2(p,out/p.name)
 packages=Path.home()/'.platformio/packages';size=list(packages.glob('toolchain-riscv*/bin/riscv32*-size'));nm=list(packages.glob('toolchain-riscv*/bin/riscv32*-nm'));assert size and nm
 (out/'elf-sections.txt').write_text(subprocess.check_output([str(size[0]),'-A',str(b/'firmware.elf')],text=True))
 symbols=subprocess.check_output([str(nm[0]),'-S','--size-sort','--radix=d','-C',str(b/'firmware.elf')],text=True)
 (out/'largest-symbols.txt').write_text('\n'.join(symbols.splitlines()[-100:][::-1])+'\n')
 (out/'image-info.txt').write_text(subprocess.check_output([sys.executable,'-m','esptool','image-info',str(b/'firmware.bin')],text=True))
 run(['pio','run','-e','wiki_x4_beta','-t','compiledb'],stdout=subprocess.DEVNULL)
 if (R/'compile_commands.json').is_file():shutil.copy2(R/'compile_commands.json',out/'compile_commands.json')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 manifest={'version':VERSION,'artifact':name,'image':info,'application_only':True,'original_X4_only':True,'hardware_tested':False,'partition_table_on_device_read':False,'build_app0_offset':hex(app0['offset']),'app_slot_bytes':app0['size'],'app_slot_headroom_bytes':app0['size']-len(image),'baseline_462_bytes':5539824,'size_delta_from_462':len(image)-5539824,'source_commit':commit,'github_run_id':os.getenv('GITHUB_RUN_ID'),'partitions':table,'source_sha256':hashes(),'host_algorithm_cases':len(host['cases']),'static_contracts':len(checks['checks']),'actual_firmware_inflater_fuzz_cases':50000,'host_sanitizers':['ASan','UBSan'],'measured_hardware_speed_or_current':False,'all_fonts_languages_and_features_retained':True}
 (out/'build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 source_files=FILES+[str(p.relative_to(R)) for p in (R/'.github').glob('wiki463_*.py')]+[str(p.relative_to(R)) for p in (R/'.github/wiki463_host').glob('*') if p.is_file()]+['.github/workflows/wiki463.yml','LICENSE','platformio.ini']
 with tarfile.open(out/'4.6.3-changed-source-and-tests.tar.gz','w:gz') as tar:
  for n in sorted(set(source_files)):
   assert not any(x in n.lower() for x in ['builtinfonts/','.ttf','.otf','.woff','.epub'])
   if (R/n).is_file():tar.add(R/n,arcname=n)
 (out/'README.txt').write_text(f'''CrossPoint Wiki 4.6.3 EXPERIMENTAL - original Xteink X4 / ESP32-C3

APPLICATION: {name}
DISPLAY/SDK VERSION: {VERSION}
SIZE: {len(image):,} bytes
SHA256: {info['sha256']}
COMMIT: {commit}
REPOSITORY: 9tpn86vnb2-png/crosspoint-wiki-x4
BRANCH: wiki-x4-4.6.3-experimental

INSTALL
Back up the SD card, particularly /.crosspoint/, and retain your working 4.6.2
application BIN. Charge the original X4. Copy this BIN to the SD card and use
the existing SD firmware-update picker. Select the BIN and confirm; keep power
connected and do not interrupt the update. Do not select the ELF, map or ZIP.
This is application-only, NOT factory/merged firmware. Never flash it to 0x0.
The compiled app0 offset is 0x10000 and slot size 0x640000. Your physical device's
partition table was not read. Do not erase or repartition to install this build.
Not for X4 Pro, X4 Classic, X3, or other hardware. Rollback uses your saved working
application through the same SD updater.

CHANGES
Ordered 32-command navigation queue with explicit overflow reporting; current
input captured before dispatch; optional pagination/prewarm after input;
cooperative one-page/four-text-element idle work; memory-gated prepared-next-Page
reuse and reflow invalidation; cached chapter titles; inclusive displayed-percent
completion and success-aware Finished Books saving with bounded retries;
512-byte buffered JSON write/compare/read, exact length and readback verification,
backup recovery and recoverable replacement; interrupted catalog tail repair,
append readback/rollback and checked replacements; bounded Bloom negative-lookup
accelerator with full-path verification; externally sorted SD title sidecar with
binary search, record checksums and full-title verification, retaining the original
linear fallback; exact off-strip image/table-rule culling; same-arena bidi cache
and reusable ruby geometry. 10ms eligible Power Saving polling and no-light-sleep
behavior stay intact. Existing Wiki logo, headings, tables, font controls, saved
articles and large Finished Books support remain. No font assets/data packs are
included separately. Times New Roman still uses your installed SD font family.

EXPERIMENTAL LIMITS
No physical-X4 boot, display, battery/current, timing or SD power-cut test occurred.
No speed percentage, battery-life improvement, or hardware stability is claimed.
The host tests are algorithms with mocked storage/pixels, NOT a full device emulator.
One synchronous SD/parser operation can exceed a cooperative idle budget. A full
queue rejects the newest command visibly; leaving the reading screen cancels its
pending commands. First XML open may build a title sidecar, using about 60 bytes
per article plus merge temporaries; it can be slow. Missing space keeps linear
search available. FAT backup replacement is recoverable, not guaranteed atomic
under every power loss or defective SD controller. Same-length arbitrary corruption
of old XFB1 payloads has no legacy per-record checksum; new appends are read back.
Existing source XML freshness uses the canonical index's sampled fingerprint.

VALIDATION
ESP32-C3 compilation/linking, real image checksum and appended SHA256, application
descriptor and UI version, slot bounds and corruption-rejection self-test.
{len(host['cases'])} host production-algorithm cases with ASan/UBSan and real ArduinoJson;
actual Wiki XML/WCDB/WCTB parser/table fixtures; actual inflater with 50,000 seeded
malformed inputs; heading native font/UTF8/BiDi code with synthetic glyph/pixel tests;
{len(checks['checks'])} static final-tree checks and unchanged source hashes across tests.
ELF, map, section sizes, symbols, source changes and build/test evidence retained.
No feature, language or font was removed to force a size reduction. The new safety
and search code can increase net size; unproven global LTO/asset removal is not enabled.

DEVICE ACCEPTANCE
Test rapid repeated/mixed page turns across chapter boundaries, long presses,
orientation/font/reflow changes, grayscale/Unicode/ruby/tables/images, XML and CDB,
saved articles, Finished Books after reboot, settings, and sleep/wake. Preserve your
4.6.2 fallback until those checks pass on your own X4.
''')
 (out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
 print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['prepare','test','package']);args=ap.parse_args();globals()[args.mode]()
