#!/usr/bin/env python3
"""Resolve ArduinoJson 7's reserved legacy macro name in the reviewed delta."""
from pathlib import Path
import hashlib,json,re
root=Path('.').resolve()
p=root/'lib/Serialization/PersistableStore.cpp'
s=p.read_text()
assert len(re.findall(r'\bJsonBuffer\b',s))==4, 'Unexpected persistence source'
p.write_text(re.sub(r'\bJsonBuffer\b','BufferedJsonSink',s))
manifest_path=root/'wiki463-source-sha256.json'
manifest=json.loads(manifest_path.read_text())
manifest['lib/Serialization/PersistableStore.cpp']=hashlib.sha256(p.read_bytes()).hexdigest()
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('Reserved ArduinoJson macro collision resolved; reviewed source hash refreshed.')
print(manifest['lib/Serialization/PersistableStore.cpp'])
