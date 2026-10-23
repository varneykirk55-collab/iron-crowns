#!/bin/bash
# Task 5: record one complete battle per era (960x540 to keep llvmpipe recording time sane)
cd "$(dirname "$0")/.."
export RES=960x540
for cfg in "1300 SWE" "1500 JPN" "1800 SWE" "1914 USA" "1980 USA"; do
  set -- $cfg
  tools/rec.sh era_$1_$2 1500 -- --demo=battle --year=$1 --nation=$2 --closeup --timeout=600
done
echo "ALL ERAS DONE" >> rec/rec.log
