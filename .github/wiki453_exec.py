#!/usr/bin/env python3
from pathlib import Path
import base64
import gzip
import re
import sys

if len(sys.argv) != 2:
    raise SystemExit('usage: wiki453_exec.py <compressed-wrapper.py>')
path = Path(sys.argv[1])
text = path.read_text()
match = re.search(r"b64decode\('([^']+)'\)", text)
if not match:
    raise SystemExit(f'{path}: compressed payload not found')
payload = match.group(1)

def decode(candidate):
    raw = base64.b64decode(candidate, validate=True)
    return gzip.decompress(raw).decode('utf-8')

try:
    source = decode(payload)
except Exception as first_error:
    # The staged 4.5.3 wrapper picked up one extra Base64 character while being
    # transported through the GitHub write path. Recover deterministically by
    # deleting one character and accepting only a candidate whose Base64, gzip
    # stream, CRC, and UTF-8 source all validate.
    source = None
    repaired_at = -1
    for i in range(len(payload)):
        candidate = payload[:i] + payload[i + 1:]
        try:
            source = decode(candidate)
            repaired_at = i
            break
        except Exception:
            continue
    if source is None:
        raise SystemExit(f'{path}: payload recovery failed: {first_error}')
    print(f'{path}: recovered compressed payload by removing transport character at offset {repaired_at}')

exec(compile(source, str(path), 'exec'))
