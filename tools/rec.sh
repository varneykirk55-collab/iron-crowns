#!/bin/bash
# Record one demo to rec/<name>_demo.mp4 (+ shots in shots/<name>/). Usage: tools/rec.sh <name> [timeout_s] -- <game args...>
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
n=$1; shift; to=${1:-600}; shift; [ "$1" == "--" ] && shift
mkdir -p rec shots/$n
timeout $to xvfb-run -a -s "-screen 0 ${RES:-1280x720}x24" tools/godot --path game --resolution ${RES:-1280x720} --fixed-fps 30 --write-movie "$ROOT/rec/$n.avi" -- --shots="$ROOT/shots/$n" "$@" > rec/$n.log 2>&1
echo "exit $?" >> rec/$n.log
ffmpeg -y -loglevel error -i rec/$n.avi -c:v libx264 -preset medium -crf 24 -pix_fmt yuv420p -movflags +faststart rec/${n}_demo.mp4 && rm -f rec/$n.avi
echo "DONE $n" >> rec/rec.log
