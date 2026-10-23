#!/usr/bin/env python3
"""Summarise BATTLERESULT lines from recorded era battles: tools/era_summary.py rec/era_*.log"""
import sys, json
for f in sys.argv[1:]:
    for l in open(f):
        if "BATTLERESULT" in l:
            d = json.loads(l.split("BATTLERESULT", 1)[1])
            print(f"{f}: era={d['era']} sides={d['codes']} winner_side={d['winner']} battle_s={d['battle_s']} men {d.get('start_men')}->{d.get('end_men')}")
            print(f"   projectiles={d['projectiles']} models={d['render_models']} melee_share={d['melee_share']}")
            for u in d["units"]:
                print(f"   side{u.get('side','?')} {u['id']:12s} era={u['era']} model={u['model']} role={u['role']} armor={u['armor']} men {u['men0']}->{u['men']} kills={u['kills']} melee_kills={u['mkills']}")
