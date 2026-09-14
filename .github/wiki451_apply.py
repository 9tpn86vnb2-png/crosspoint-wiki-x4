#!/usr/bin/env python3
from pathlib import Path

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'4.5.1: {label} anchor not found')
    return text.replace(old, new, 1)

FILES = {
