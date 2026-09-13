#!/usr/bin/env bash
set -euo pipefail
git diff --check
git -C freeink-sdk diff --check
python .github/wiki441_contract_tests.py
