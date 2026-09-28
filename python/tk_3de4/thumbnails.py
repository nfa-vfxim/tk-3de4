# Missing thumbnails, rendered by the NFA Shot Manager's own code in a background Nuke.
# 3DE cannot read EXR/ACES itself, so it starts `Nuke -t` with the pipeline's NUKE_PATH,
# imports nfa_shot_manager and calls the same functions the Shot Manager uses
# (thumbnail_source_for / thumbnail_needs_regen / _render_single_thumbnail /
# _record_thumbnail_version). Same picture, same file, same .ver sidecar.
import glob
import os
import re
import tempfile

NUKE_GLOBS = [r"C:\Program Files\Nuke*\Nuke*.exe"]
PIPELINE_NUKE_PATH = r"C:\pipeline\nuke"
LINE_RE = re.compile(r"^NFA_THUMB\s+(\S+)\s+(ok|fail|skip)\s*(.*)$")

NUKE_SCRIPT = r'''
import os, sys, json
import nuke
import nfa_shot_manager as sm

root = sys.argv[1]
only = set(s for s in sys.argv[2].split(",") if s) if len(sys.argv) > 2 else None
scanner = sm.ProjectScanner(root)
try:
    cfg = sm._read_json(scanner.config_path()) or {}
    scanner.full_cg = bool(cfg.get("full_cg", False))
except Exception:
    pass
shots = scanner.discover_shots()
td = scanner.thumb_dir()
for sid, sd in sorted(shots.items()):
    if only is not None and sid not in only:
        continue
    source = sm.thumbnail_source_for(sd, full_cg=scanner.full_cg)
    if not source:
        print("NFA_THUMB %s skip no source" % sid, flush=True)
        continue
    if not sm.thumbnail_needs_regen(td, sid, source):
        print("NFA_THUMB %s skip up to date" % sid, flush=True)
        continue
    try:
        ok, err = sm._render_single_thumbnail(source, os.path.join(td, sid + ".jpg"))
    except Exception as e:
        ok, err = False, str(e)
    if ok:
        sm._record_thumbnail_version(td, sid, source)
        print("NFA_THUMB %s ok" % sid, flush=True)
    else:
        print("NFA_THUMB %s fail %s" % (sid, str(err).replace(chr(10), " ")), flush=True)
'''


def find_nuke():
    found = []
    for pattern in NUKE_GLOBS:
        for exe in glob.glob(pattern):
            m = re.search(r"Nuke(\d+)\.(\d+)v(\d+)", exe)
            if m and re.match(r"^Nuke\d+\.\d+\.exe$", os.path.basename(exe), re.IGNORECASE):
                found.append((tuple(int(x) for x in m.groups()), exe))
    return sorted(found)[-1][1] if found else None


def nuke_environment():
    """Clean environment for Nuke: nothing of 3DE's Python, but the pipeline plugins."""
    env = dict(os.environ)
    for key in list(env):
        k = key.upper()
        if k in ("PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
                 "PYTHON_CUSTOM_SCRIPTS_3DE4", "NFA_3DE_PYSIDE_PATH") \
                or k.startswith("SGTK_") or k.startswith("TANK_"):
            env.pop(key)
    paths = [p for p in env.get("NUKE_PATH", "").split(os.pathsep) if p]
    if os.path.isdir(PIPELINE_NUKE_PATH) and PIPELINE_NUKE_PATH.lower() not in [p.lower() for p in paths]:
        paths.append(PIPELINE_NUKE_PATH)
    env["NUKE_PATH"] = os.pathsep.join(paths)
    return env


def write_script():
    path = os.path.join(tempfile.gettempdir(), "nfa_3de_thumbnails.py")
    with open(path, "w") as f:
        f.write(NUKE_SCRIPT)
    return path


def command(nuke_exe, root, sids):
    return [nuke_exe, "-t", write_script(), root, ",".join(sids)]
