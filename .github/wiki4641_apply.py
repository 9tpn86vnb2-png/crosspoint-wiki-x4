#!/usr/bin/env python3
"""Targeted 4.6.4.1 cleanup hotfix; do not change HAL assertions or index formats."""
from pathlib import Path
import hashlib,re
R=Path(__file__).resolve().parents[1]
expected={'src/activities/wiki/WikiIndexJob.cpp':'b1fb68c66d294c0f1b5dbc47cc0f9dfd069884f42d7538dbee51038829a7a2bb','src/activities/wiki/WikiArchive.cpp':'9c0b2e93ee820f6aec02fbe074311601a6b8e4a203d23af00941270adb66dafa','platformio.local.ini':'99ce0c2d69517ffe2be6cded169a79715c8dcbd7cbf1f229cbc6ebf04e48221c'}
for name,digest in expected.items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,name
p=R/'src/activities/wiki/WikiIndexJob.cpp';s=p.read_text()
s,n=re.subn(r'\b([A-Za-z_]\w*)\.close\(\);',r'closeIfOpen(\1);',s)
assert n==21,n
anchor='namespace {\n';assert s.count(anchor)==1
s=s.replace(anchor,'''namespace {
// 4.6.4.1: default and moved-from HalFile handles have no Impl. The real
// HAL asserts when close() is called on them. Cleanup runs before begin(),
// between phases, after failed opens, and from the destructor; test first.
// Leave the HAL assertion and all explicit sync/commit checks unchanged.
void closeIfOpen(HalFile& file) {
  if (file) file.close();
}
''',1);p.write_text(s)
p=R/'src/activities/wiki/WikiArchive.cpp';s=p.read_text();a='  const bool haveArticles=!restart&&openXmlIndex(true);\n  indexFile_.close();';assert s.count(a)==1
s=s.replace(a,'  const bool haveArticles=!restart&&openXmlIndex(true);\n  if (indexFile_) indexFile_.close();',1);p.write_text(s)
p=R/'platformio.local.ini';s=p.read_text();assert s.count('1.6.0-wiki-4.6.4')==2;p.write_text(s.replace('1.6.0-wiki-4.6.4','1.6.0-wiki-4.6.4.1'))
print('Applied 4.6.4.1: guarded indexer cleanup, guarded archive cleanup, UI/SDK version. HAL unchanged.')
