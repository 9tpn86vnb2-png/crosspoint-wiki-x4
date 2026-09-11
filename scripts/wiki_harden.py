#!/usr/bin/env python3
"""Guarded fix for malformed raw-DEFLATE input in the pinned uzlib source.
A seeded ASan/UBSan test found that tinf_decode_symbol's negative error return
could index dist_base[-3]. Reject negative literal/distance symbols explicitly.
No compression-format or valid-stream behavior is intentionally changed.
"""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'lib/uzlib/src/tinflate.c'
ORIGINAL = '9e7bc88b7441870d2a5092b1a0c9732d0554420e'
PATCHED = 'd7b26f4f3294aebabc6690cb7a674c3ba78eb6f7'

def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def harden(check_only=False):
    data = TARGET.read_bytes()
    digest = blob(data)
    if digest == PATCHED:
        print('Verified malformed-DEFLATE bounds fix.')
        return
    if digest != ORIGINAL or check_only:
        raise RuntimeError('Missing bounds fix or unreviewed uzlib source: ' + digest)
    text = data.decode()
    changes = [
        ('        if (d->eof) {',
         '        /* Wiki beta hardening: a negative decoded symbol is an error, not a literal. */\n        if (d->eof || sym < 0) {'),
        ('        if (dist >= 30) {',
         '        /* Reject decoder errors before indexing the distance tables. */\n        if (dist < 0 || dist >= 30) {'),
    ]
    for old, new in changes:
        if text.count(old) != 1:
            raise RuntimeError('Ambiguous decoder-fix anchor')
        text = text.replace(old, new, 1)
    output = text.encode()
    if blob(output) != PATCHED:
        raise RuntimeError('Unexpected decoder-fix output')
    TARGET.write_bytes(output)
    print('Applied checked malformed-DEFLATE bounds fix to pinned uzlib source.')

if __name__ == '__main__':
    harden(check_only='--check' in sys.argv)
