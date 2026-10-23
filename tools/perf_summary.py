#!/usr/bin/env python3
"""Summarise a --perfout JSON (per-frame samples) into per-phase CPU vs render stats (markdown)."""
import json, sys, statistics as st
def pct(v, p):
    v = sorted(v); return v[min(len(v)-1, int(len(v)*p))] if v else 0
data = json.load(open(sys.argv[1]))
label = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
phases = {}
for d in data[5:]:
    phases.setdefault(d["phase"], []).append(d)
keys = ["frame_ms", "process_ms", "sim_tick_ms", "battle_sim_ms", "battle_units_ms", "battle_fx_ms", "render_cpu_ms", "render_gpu_ms", "draw_calls", "objects", "primitives", "instances"]
print(f"### {label}\n")
print("| phase | frames | fps (mean) | " + " | ".join(keys) + " |")
print("|---|---|---|" + "---|" * len(keys))
for ph, rows in phases.items():
    cells = []
    for k in keys:
        v = [r[k] for r in rows if k in r]
        cells.append("-" if not v else f"{st.mean(v):.2f} (p95 {pct(v,0.95):.2f})" if k.endswith("_ms") else f"{st.mean(v):.0f}")
    fps = st.mean([r["fps"] for r in rows])
    print(f"| {ph} | {len(rows)} | {fps:.1f} | " + " | ".join(cells) + " |")
print()
