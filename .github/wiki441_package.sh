#!/usr/bin/env bash
set -euo pipefail
sed -i 's/crosspoint-1.6.0-wiki-beta1-x4-UNTESTED.bin/crosspoint-1.6.0-wiki-4.4.1-x4-UNTESTED.bin/' scripts/wiki_package.py
sed -i 's/1.6.0-wiki-beta1/1.6.0-wiki-4.4.1/' scripts/wiki_package.py
python scripts/wiki_package.py 2>&1 | tee wiki-package.log
