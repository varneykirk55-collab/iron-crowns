#!/usr/bin/env python3
"""Assemble deliverables/v0.2/ from the `main` branch build (no graphics pass) + lead worktree evidence."""
import os, shutil, zipfile, glob, subprocess
R = "/workspace/grand_strategy"; L = "/workspace/ironcrowns-lead"; D = f"{R}/deliverables/v0.2"
os.makedirs(D, exist_ok=True)
for sub in ("screenshots", "videos", "evidence"):
    os.makedirs(f"{D}/{sub}", exist_ok=True)
os.chdir(R)
for f in ("README.md", "FEATURE_STATUS.md", "CHANGELOG.md", "PROGRESS.md", "COLLAB.md"):
    shutil.copy(f, D)
for f in glob.glob("evidence/*"):
    shutil.copy(f, f"{D}/evidence/")
for extra, name in (("/tmp/perf_summaries.md", "perf_summaries.md"), ("/tmp/full_gfx.log", "lead-dev_with_graphics_pass_full_tests.log"),
                    ("/tmp/smoke.log", "linux_export_smoke_run.log")):
    if os.path.exists(extra): shutil.copy(extra, f"{D}/evidence/{name}")
for f in glob.glob(f"{L}/rec/*.log"):
    shutil.copy(f, f"{D}/evidence/rec_{os.path.basename(f)}")
for d in glob.glob(f"{L}/shots/*/"):
    n = os.path.basename(d.rstrip("/"))
    if n.startswith(("era_", "v02", "camera")):
        os.makedirs(f"{D}/screenshots/{n}", exist_ok=True)
        for f in glob.glob(d + "*.png"): shutil.copy(f, f"{D}/screenshots/{n}/")
for f in glob.glob(f"{L}/rec/*.mp4"):
    shutil.copy(f, f"{D}/videos/")
# project: exact tree of `main` (tracked files only)
subprocess.run(["git", "archive", "--format=zip", "--prefix=IronCrowns_v0.2/", "-o", f"{D}/IronCrowns_v0.2_project.zip", "main", "--", ".", ":!deliverables"], check=True)
def zipdir(out, item, base):
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(os.path.join(base, item)):
            for fn in files:
                fp = os.path.join(root, fn); z.write(fp, os.path.relpath(fp, base))
zipdir(f"{D}/IronCrowns_v0.2_linux_x86_64.zip", "linux", f"{R}/build")
zipdir(f"{D}/IronCrowns_v0.2_windows_x86_64.zip", "windows", f"{R}/build")
