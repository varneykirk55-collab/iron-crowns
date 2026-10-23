#!/bin/sh
# usage: hash_demo.sh <worktree> <outdir> [extra user args]   rendered-battle (BattleView) check, headless
W=$1; O=$2; shift 2; mkdir -p $O; cd $W
for cfg in "SWE 1300" "SWE 1650" "SWE 1800" "USA 1914"; do
  set -- $cfg "$@"; N=$1; Y=$2; shift 2
  timeout 900 tools/godot --headless --fixed-fps 30 --path game res://scenes/main.tscn -- --demo=battle --nation=$N --year=$Y --shots=/tmp/hd_shots "$@" > $O/battle_${N}_${Y}.log 2>&1
  grep -h BATTLERESULT $O/battle_${N}_${Y}.log | head -1 > $O/battle_${N}_${Y}.result
done
echo ALLDONE > $O/done
