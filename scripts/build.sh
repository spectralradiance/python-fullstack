#!/usr/bin/env bash
# Full pipeline: clone -> inventory -> merge -> sanitize -> PII/secret gate.
# The gate must pass (exit 0) before anything is committed.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/clone_all.sh
for r in raw/_reference/PythonFullStack raw/_reference/PythonFullStack2; do
  [ -d "$r/.git" ] || git clone -q "https://github.com/PdxCodeGuild/$(basename "$r").git" "$r"
done
python -I scripts/inventory.py > /dev/null
for r in raw/*/ raw/_reference/*/; do [ -d "$r/.git" ] && git -C "$r" log --format='%an|%ae'; done \
  | sort | uniq -c | sort -rn > raw/_inventory/git_authors.txt
python -I scripts/build_curriculum.py
python -I scripts/sanitize.py curriculum
python -I scripts/pii_scan.py curriculum inventory
