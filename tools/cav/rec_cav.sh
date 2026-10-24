#!/bin/bash
# Offline normal-speed recording of one cavalry demo (anim_demo.tscn) to deliverables/cavalry-overhaul/<name>.mp4
# usage: tools/cav/rec_cav.sh <name> <dur_s> <anim_demo args...>     (xvfb, --fixed-fps 30 --write-movie, 1280x720)
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
n=$1; d=$2; shift 2
O=deliverables/cavalry-overhaul; mkdir -p $O /tmp/cavrec
timeout 3000 xvfb-run -a -s "-screen 0 1280x720x24" tools/godot --path game --resolution 1280x720 --fixed-fps 30 \
  --write-movie /tmp/cavrec/$n.avi res://tests/anim_demo.tscn -- --out=/tmp/cavrec/$n --tag=$n --dur=$d "$@" > /tmp/cavrec/$n.log 2>&1
echo "exit $?" >> /tmp/cavrec/$n.log
ffmpeg -y -loglevel error -i /tmp/cavrec/$n.avi -c:v libx264 -preset medium -crf 23 -pix_fmt yuv420p -movflags +faststart $O/$n.mp4 && rm -f /tmp/cavrec/$n.avi
echo "DONE $n" >> /tmp/cavrec/rec.log
