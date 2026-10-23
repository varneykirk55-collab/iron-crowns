#!/bin/sh
# usage: run_suite.sh <worktree> <outdir>
W=$1; O=$2; mkdir -p $O; cd $W
timeout 900 tools/godot --headless --path game --import > $O/import.log 2>&1
timeout 900 tools/godot --headless --path game --import > $O/import_b.log 2>&1
timeout 900 tools/godot --headless --path game res://tests/test_runner.tscn > $O/tests.log 2>&1
timeout 900 tools/godot --headless --path game res://tests/sim_hash.tscn > $O/simhash.log 2>&1
timeout 600 tools/godot --headless --path game res://tests/test_audio.tscn > $O/audio.log 2>&1
echo ALLDONE >> $O/simhash.log
