import re, subprocess, sys
for it in range(80):
    out = subprocess.run(["tools/godot", "--headless", "--path", "game", "--quit-after", "2", *(sys.argv[1:] or ["res://tests/test_runner.tscn", "--", "--only=none"])], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120).stdout
    out += ""
    m = re.findall(r'Cannot infer the type of "(\w+)" variable.*?\n\s+at: GDScript::reload \(res://(.+?):(\d+)\)', out)
    for path, line in re.findall(r'inferred from a Variant value.*?\n\s+at: GDScript::reload \(res://(.+?):(\d+)\)', out):
        L = open("game/" + path).read().split("\n")
        mm = re.search(r'var (\w+) :=', L[int(line)-1])
        if mm: m.append((mm.group(1), path, line))
    if not m:
        errs = [l for l in out.splitlines() if "ERROR" in l or "Error" in l]
        print("\n".join(out.splitlines()[:40]))
        break
    for var, path, line in m:
        p = "game/" + path; ln = int(line)
        L = open(p).read().split("\n")
        L[ln-1] = re.sub(r'var %s :=' % var, 'var %s =' % var, L[ln-1], count=1)
        open(p, "w").write("\n".join(L))
        print("fixed", path, ln, var)
