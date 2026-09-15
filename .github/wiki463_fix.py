#!/usr/bin/env python3
"""Resolve compile-time compatibility issues without changing runtime behavior."""
from pathlib import Path
import hashlib,json,re
root=Path('.').resolve()
p=root/'lib/Serialization/PersistableStore.cpp'
s=p.read_text()
assert len(re.findall(r'\bJsonBuffer\b',s))==4, 'Unexpected persistence source'
p.write_text(re.sub(r'\bJsonBuffer\b','BufferedJsonSink',s))
h=root/'src/activities/reader/EpubReaderActivity.h'
s=h.read_text()
assert s.count('#include <Epub/PageLink.h>')==1 and '#include <Epub/Page.h>' not in s
h.write_text(s.replace('#include <Epub/PageLink.h>', '#include <Epub/Page.h>\n#include <Epub/PageLink.h>',1))
manifest_path=root/'wiki463-source-sha256.json'
manifest=json.loads(manifest_path.read_text())
for path in [p,h]:
    manifest[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('Resolved ArduinoJson macro collision and completed the Page type at owner construction.')
print(json.dumps({str(path.relative_to(root)):manifest[str(path.relative_to(root))] for path in [p,h]},indent=2))
