#!/usr/bin/env python3
"""Assemble deliverables/: project ZIP, builds, docs, screenshots, videos."""
import os, shutil, zipfile, glob
R = "/workspace/grand_strategy"; D = f"{R}/deliverables"
os.chdir(R)
for sub in ("screenshots", "videos"):
    os.makedirs(f"{D}/{sub}", exist_ok=True)
for f in ("README.md", "FEATURE_STATUS.md", "PROGRESS.md", "test_results.txt"):
    shutil.copy(f, D)
for f in glob.glob("shots/*.png"):
    if "debug_" not in f:
        shutil.copy(f, f"{D}/screenshots/")
for f in glob.glob("rec/*.mp4"):
    shutil.copy(f, f"{D}/videos/")

def zipdir(out, items, base=R, skip=lambda p: False):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for it in items:
            p = os.path.join(base, it)
            if os.path.isfile(p):
                z.write(p, it); continue
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in (".godot", "__pycache__")]
                for fn in files:
                    fp = os.path.join(root, fn); rel = os.path.relpath(fp, base)
                    if not skip(rel):
                        z.write(fp, rel)
zipdir(f"{D}/IronCrowns_project.zip",
       ["README.md", "FEATURE_STATUS.md", "PROGRESS.md", "test_results.txt", "game", "pipeline", "blend",
        "tools/package.py", "tools/fix_infer.py"],
       skip=lambda r: r.endswith(".blend1"))
zipdir(f"{D}/IronCrowns_linux_x86_64.zip", ["linux"], base=f"{R}/build")
zipdir(f"{D}/IronCrowns_windows_x86_64.zip", ["windows"], base=f"{R}/build")
for root, _, files in os.walk(D):
    for fn in sorted(files):
        fp = os.path.join(root, fn); print(f"{os.path.getsize(fp)/1e6:8.1f} MB  {os.path.relpath(fp, D)}")
