#!/usr/bin/env bash
# Clone the 13 main cohort repos into raw/ (gitignored; contains un-anonymized student data).
set -u
cd "$(dirname "$0")/../raw"
REPOS="20171003-FullStack-Day 20180116-FullStack-Day class_ocelot class_platypus class_iguana class_sheep class_emu class_honeybadger class_raccoon class_mountain_goat class_armadillo class_bumble_bee class_eagle"
for r in $REPOS; do
  if [ -d "$r/.git" ]; then echo "skip $r"; continue; fi
  ( git -c core.longpaths=true clone -q "https://github.com/PdxCodeGuild/$r.git" "$r" && echo "done $r" || echo "FAIL $r" ) &
done
wait
