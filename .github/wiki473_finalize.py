#!/usr/bin/env python3
"""Release the old article's string capacity before destination navigation."""
from pathlib import Path
import hashlib
R=Path(__file__).resolve().parents[1]
def change(name,old,new):
 p=R/name;s=p.read_text();assert s.count(old)==1,(name,'anchor count')
 p.write_text(s.replace(old,new,1))
change('src/activities/wiki/WikiLinkNavigation.cpp',
 ' entry_={};document_.clear();std::string().swap(title_);',
 ' // Empty-string assignment may retain a multi-KiB allocation. Move all old\n'
 ' // storage into a temporary whose destructor runs before the next lookup.\n'
 ' { WikiArchive::Entry empty; std::swap(entry_,empty); }\n'
 ' document_.clear();std::string().swap(title_);')
change('.github/wiki473_test.py',"'legacy-uncaught-control','repeat-links']", "'legacy-uncaught-control','repeat-links','release-storage']")
change('.github/wiki473_tests.cpp',
 ' }else if(c=="repeat-links"){',
 ' }else if(c=="release-storage"){\n'
 '  WikiActivity w;prepareLink(w);w.entry_.text.assign(32768,\'x\');\n'
 '  w.entry_.title.assign(1024,\'t\');w.entry_.key.assign(1024,\'k\');\n'
 '  check(w.entry_.text.capacity()>=32768,"large source allocation exists");\n'
 '  w.releaseArticleMemory();const WikiArchive::Entry empty;\n'
 '  check(w.entry_.text.capacity()==empty.text.capacity(),"source body capacity released, not only length cleared");\n'
 '  check(w.entry_.title.capacity()==empty.title.capacity()&&w.entry_.key.capacity()==empty.key.capacity(),"source key/title capacity released");\n'
 '  check(w.entry_.links.capacity()==0&&w.entry_.tables.capacity()==0&&!w.entry_.found,"source metadata storage released");\n'
 ' }else if(c=="repeat-links"){')
change('.github/wiki473_README.md',
 'A piped/inflected label is not substituted for the actual target:',
 'The release uses swap/destruction: empty-string assignment alone can keep the\n'
 'old allocation. A dedicated 32 KiB source-buffer regression checks capacity release.\n'
 'A piped/inflected label is not substituted for the actual target:')
change('.github/wiki473_CRASH-AND-POWER.md',
 '4.7.3 changes the lifetime/order and guards those allocating boundaries.',
 'A final capacity test also showed that assigning an empty Entry clears string\n'
 'length but can retain the old 32 KiB allocation. Explicit swap/destruction now\n'
 'releases all source-body storage; the new release-storage regression covers it.\n\n'
 '4.7.3 changes the lifetime/order and guards those allocating boundaries.')
print('Applied explicit source-capacity release and regression test.')
