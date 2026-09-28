# Plates vinden in 02_source en als camera in 3DE laden.
# Zoeklogica gelijk aan de NFA Shot Manager:
#   <root>/02_source/<seq>/<shot>/<plate_id>/plates/[<format>/]<beelden>
#   <root>/02_source/<seq>/<shot>/<plate_id>/undistort/v###/<beelden>   (undistorted, uit Nuke)
import os
import re

SOURCE_DIRNAME = "02_source"
PLATES_LEAF = "plates"
UNDISTORT_LEAF = "undistort"
IMAGE_EXTENSIONS = {".exr", ".dpx", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".cin"}
FRAME_NUM_RE = re.compile(r"[._](\d{3,8})\.[A-Za-z0-9]+$")
SEQ_PREFIX_RE = re.compile(r"^[A-Za-z]+(?=\d)")
VERSION_RE = re.compile(r"v(\d+)", re.IGNORECASE)


def _listdirs(path):
    out = []
    try:
        with os.scandir(path) as entries:
            for e in entries:
                try:
                    if e.is_dir() and not e.name.startswith("."):
                        out.append((e.name, e.path))
                except OSError:
                    pass
    except (OSError, ValueError):
        return []
    return sorted(out)


def _listfiles(path):
    try:
        with os.scandir(path) as entries:
            return sorted(e.name for e in entries if e.is_file() and not e.name.startswith("."))
    except (OSError, ValueError):
        return []


def _child(parent, name):
    for n, p in _listdirs(parent):
        if n.lower() == name.lower():
            return p
    return None


def normalize_seq(name):
    return SEQ_PREFIX_RE.sub("", name or "").lower()


def scan_image_sequence(folder):
    """(pad-pad met #, eerste, laatste, aantal) van de grootste reeks in *folder*, of None."""
    groups = {}
    for name in _listfiles(folder):
        if os.path.splitext(name)[1].lower() not in IMAGE_EXTENSIONS:
            continue
        m = FRAME_NUM_RE.search(name)
        if not m:
            continue
        s, e = m.span(1)
        groups.setdefault((name[:s], e - s, name[e:]), []).append(int(m.group(1)))
    if not groups:
        return None
    key = max(groups, key=lambda k: (len(groups[k]), k[0]))
    stem, pad, ext = key
    frames = groups[key]
    path = os.path.join(folder, "%s%s%s" % (stem, "#" * pad, ext)).replace("\\", "/")
    return {"path": path, "first": min(frames), "last": max(frames), "count": len(frames),
            "ext": ext.lstrip(".").lower()}


def _scan_leaf(leaf):
    """Beelden direct in de map, anders in de eerste submap die een reeks bevat."""
    info = scan_image_sequence(leaf)
    if info:
        return info
    for _, sub in _listdirs(leaf):
        info = scan_image_sequence(sub)
        if info:
            return info
    return None


def _scan_undistort(plate_dir):
    """Nieuwste versie in <plate_id>/undistort/ (v###-mappen of direct)."""
    und = _child(plate_dir, UNDISTORT_LEAF)
    if not und:
        return None
    best = None
    for name, sub in _listdirs(und):
        m = VERSION_RE.search(name)
        info = _scan_leaf(sub)
        if info:
            info["version"] = int(m.group(1)) if m else 0
            if best is None or info["version"] > best["version"]:
                best = info
    if best is None:
        best = scan_image_sequence(und)
        if best:
            best["version"] = 0
    return best


def find_shot_source_dirs(project_root, shot_name, seq_name=None):
    """Alle 02_source/<seq>/<shot>-mappen die bij dit shot horen."""
    src = _child(project_root, SOURCE_DIRNAME) if project_root else None
    if not src or not shot_name:
        return []
    shot_l = shot_name.lower()
    seq_n = normalize_seq(seq_name) if seq_name else None
    hits = []
    for seq, seq_path in _listdirs(src):
        if seq_n and normalize_seq(seq) != seq_n:
            continue
        for shot, shot_path in _listdirs(seq_path):
            sl = shot.lower()
            # Shotcode in ShotGrid is soms "0010", soms "sc003_0010".
            if sl == shot_l or shot_l.endswith("_" + sl) or shot_l.endswith(sl) and len(sl) >= 3:
                hits.append(shot_path)
    return hits


def find_plates(project_root, shot_name, seq_name=None):
    """[{plate_id, path, first, last, count, ext, undistort}] voor dit shot."""
    plates = []
    for shot_dir in find_shot_source_dirs(project_root, shot_name, seq_name):
        for plate_id, plate_dir in _listdirs(shot_dir):
            leaf = _child(plate_dir, PLATES_LEAF)
            if not leaf:
                continue
            info = _scan_leaf(leaf)
            if not info:
                continue
            info["plate_id"] = plate_id
            info["plate_dir"] = plate_dir
            info["undistort"] = _scan_undistort(plate_dir)
            plates.append(info)
    return plates


# ------------------------------------------------------------------ 3DE
def load_into_3de(plate, fps=25.0, first_frame=1001, gamma=2.2, name=None, log=None):
    """Maakt (of hergebruikt een lege) sequence-camera en zet de wiki-instellingen.

    Geeft (camera_id, [niet-gelukte stappen]) terug. Elke tde4-aanroep is los
    afgevangen: een ontbrekende functie mag de rest niet tegenhouden."""
    import tde4

    skipped = []

    def call(fn, *args):
        f = getattr(tde4, fn, None)
        if f is None:
            skipped.append(fn)
            return None
        try:
            return f(*args)
        except Exception as exc:  # noqa: BLE001
            skipped.append("%s (%s)" % (fn, exc))
            return None

    cam = None
    # Hergebruik de standaardcamera (seq#1) als die nog geen beelden heeft.
    for c in (call("getCameraList") or []):
        path = call("getCameraPath", c)
        if not path:
            cam = c
            break
    if cam is None:
        cam = call("createCamera", "SEQUENCE")
    if cam is None:
        raise RuntimeError("3DE could not create a camera.")

    call("setCameraName", cam, name or plate["plate_id"])
    call("setCameraPath", cam, plate["path"].replace("/", os.sep))
    call("setCameraSequenceAttr", cam, plate["first"], plate["last"], 1)
    call("setCameraFrameOffset", cam, first_frame)
    call("setCameraFPS", cam, float(fps))
    call("setCamera8BitColorGamma", cam, float(gamma))
    call("setCurrentCamera", cam)
    if log:
        log("Plate loaded: %s (%d-%d) → camera %s; skipped: %s"
            % (plate["path"], plate["first"], plate["last"], cam, skipped or "-"))
    return cam, skipped
