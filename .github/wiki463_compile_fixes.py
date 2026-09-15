#!/usr/bin/env python3
from pathlib import Path
p=Path('src/activities/reader/EpubReaderActivity.h');s=p.read_text();a='#include <Epub/Section.h>';assert s.count(a)==1;p.write_text(s.replace(a,a+'\n#include <Epub/Page.h>',1))
p=Path('.github/wiki463_finish.py');s=p.read_text();a=" result=run([sys.executable,'.github/wiki463_host/run.py','--json',str(deps)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)\n print(result.stdout);(R/'wiki463-host-tests.log').write_text(result.stdout)";b=" result=subprocess.run([sys.executable,'.github/wiki463_host/run.py','--json',str(deps)],cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)\n print(result.stdout,flush=True);(R/'wiki463-host-tests.log').write_text(result.stdout);result.check_returncode()";assert s.count(a)==1;p.write_text(s.replace(a,b,1))
print('Fixed complete Page type for the inline EPUB-reader constructor; host failure output is retained.')
