#!/usr/bin/env python3
"""Align the remaining catalog footer with the new tested controls."""
from pathlib import Path
import hashlib,difflib
R=Path(__file__).resolve().parents[1]
p=R/'src/activities/wiki/WikiActivity.cpp'
old=p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='01ae9f0117834bd284190dc77e27b750db545f8cc153d089c8a38333ac27fb04'
a='Hold side Up/Down: jump letter; Next/Previous: list page'
b='L/R: page; hold L/R: letter; hold side: 10 pages'
assert old.count(a)==1
new=old.replace(a,b,1);p.write_text(new)
patch=R/'4.7.1-to-4.7.2.patch'
with patch.open('a') as f:f.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/activities/wiki/WikiActivity.cpp',tofile='b/src/activities/wiki/WikiActivity.cpp'))
print('Final catalog footer matches the tap/hold actions.')
