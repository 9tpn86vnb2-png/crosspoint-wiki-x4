from pathlib import Path
import hashlib

p=Path('platformio.local.ini')
text=p.read_text()
base_sha=hashlib.sha256(p.read_bytes()).hexdigest()
if base_sha!='2d1e5f8dc36440d051d4b9d6f6d448075d3f5f4c419615abc86e8b3897135f33':
    raise SystemExit('Unexpected 4.4.1 pre-exception profile: '+base_sha)
anchor='[env:wiki_x4_beta]\nextends = base, firmware_tuned\nbuild_flags =\n'
replacement='''[env:wiki_x4_beta]\nextends = base, firmware_tuned\n; Wiki 4.4.1 catches std::bad_alloc/length_error at the XML article boundary.\n; The base profile disables C++ exceptions globally, so this X4 Wiki profile\n; explicitly removes that flag and re-enables exceptions for its translation units.\nbuild_unflags =\n  -std=gnu++11\n  -fno-exceptions\nbuild_flags =\n'''
if text.count(anchor)!=1: raise SystemExit('Wiki 4.4.1 exception-profile anchor mismatch')
text=text.replace(anchor,replacement,1)
flag='  -DLOG_LEVEL=1\n'
if text.count(flag)!=1: raise SystemExit('Wiki 4.4.1 -fexceptions anchor mismatch')
text=text.replace(flag,flag+'  -fexceptions\n',1)
p.write_text(text)
out=hashlib.sha256(p.read_bytes()).hexdigest()
if out!='f5081d27d5b9fbca52418e214d8909615e35996de0ac7ebb1cf970afd0711a82':
    raise SystemExit('Unexpected 4.4.1 exception-profile output: '+out)
print('Wiki 4.4.1 Wiki-only C++ exception profile applied and verified.')
