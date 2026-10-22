#!/bin/bash
# Records demo movies and converts to mp4. Usage: tools/record_all.sh demo1 demo2 ...
cd /workspace/grand_strategy
rec() { n=$1; shift
  timeout 1500 xvfb-run -a -s "-screen 0 1280x720x24" tools/godot --path game --resolution 1280x720 --fixed-fps 30 --write-movie /workspace/grand_strategy/rec/$n.avi -- "$@" > rec/$n.log 2>&1
  ffmpeg -y -loglevel error -i rec/$n.avi -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -movflags +faststart rec/${n}_demo.mp4 && rm -f rec/$n.avi
  echo "DONE $n" >> rec/record_all.log; }
for d in "$@"; do
  case $d in
    campaign) rec campaign --demo=campaign --nation=USA & ;;
    diplomacy) rec diplomacy --demo=diplomacy --nation=SWE & ;;
    era) rec era --demo=era --nation=JPN --timeout=200 & ;;
    battle) rec battle --demo=battle --nation=USA --reinforce=1 --closeup & ;;
  esac
done
wait
echo ALLDONE >> rec/record_all.log
