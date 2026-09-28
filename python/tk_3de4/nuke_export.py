# LD_3DE4-node van de huidige camera exporteren voor Nuke (na het undistorten in 3DE).
# Gebruikt 3DE's eigen exporter, dus de node is gelijk aan File > Export > Nuke LD_3DE4.
# Doel: 04_publish/shots/<seq>/<shot>/<Step>/nuke/<werkbestand>_LD_<camera>.nk
import importlib.util
import os
import re
import sys

EXPORTER = "export_nuke_LD_3DE4_Lens_Distortion_Node.py"


def _load_exporter():
    base = os.path.dirname(os.path.dirname(sys.executable))   # ...\3DE4_win64_r8.1
    path = os.path.join(base, "sys_data", "py_scripts", EXPORTER)
    if not os.path.isfile(path):
        raise RuntimeError("3DE exporter not found: %s" % path)
    spec = importlib.util.spec_from_file_location("nfa_ld_exporter", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def current_camera():
    import tde4
    cam = tde4.getCurrentCamera()
    if cam is None:
        raise RuntimeError("No camera is selected in 3DE.")
    first = tde4.getCameraSequenceAttr(cam)[0]
    try:
        offset = tde4.getCameraFrameOffset(cam)
    except Exception:
        offset = first
    return {"cam": cam, "name": tde4.getCameraName(cam), "first": int(first), "offset": int(offset)}


def safe(s):
    return re.sub(r"[^A-Za-z0-9]+", "", s or "") or "cam"


def export_dir(engine):
    """<shot_publish_area_3de>/../nuke — de publish-map van deze stap."""
    tk, ctx = engine.sgtk, engine.context
    tmpl = tk.templates.get("shot_publish_area_3de")
    if tmpl is None or not ctx.entity or ctx.entity.get("type") != "Shot":
        raise RuntimeError("Only available from a shot task.")
    fields = ctx.as_template_fields(tmpl, validate=True)
    return os.path.join(os.path.dirname(tmpl.apply_fields(fields)), "nuke")


def export_path(engine, cam_name):
    """Naam volgt het geopende werkbestand, zodat LD-node en track dezelfde versie hebben."""
    import tde4
    work = tde4.getProjectPath() or ""
    if not work:
        raise RuntimeError("Save the 3DE project first (File Save), so the export gets the same version.")
    stem = os.path.splitext(os.path.basename(work))[0]
    m = re.search(r"_work_(.+)_v(\d+)$", stem)
    if m:
        stem = "%s_LD_%s_%s_v%s" % (stem[:m.start()], m.group(1), safe(cam_name), m.group(2))
    else:
        stem = "%s_LD_%s" % (stem, safe(cam_name))
    return os.path.join(export_dir(engine), stem + ".nk")


def export_ld_node(cam, nuke_first_frame, out_path, fov_mode=2):
    """Schrijft de LD_3DE4-node. fov_mode 2 = 'relative to Display Window' (aanbevolen)."""
    import tde4
    mod = _load_exporter()
    # exportNukeDewarpNode leest de FOV-modus uit de requester van zijn dialoog;
    # we maken die aan zonder hem te tonen.
    req = tde4.createCustomRequester()
    tde4.addOptionMenuWidget(req, "option_menu_fov_mode", "FOV mode",
                             "Export FOV as is (legacy)", "Export FOV relative to Display Window (recommended)")
    tde4.setWidgetValue(req, "option_menu_fov_mode", str(fov_mode))
    mod.nuke_node_req = req
    folder = os.path.dirname(out_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    try:
        mod.exportNukeDewarpNode(cam, int(nuke_first_frame), out_path)
    finally:
        try:
            tde4.deleteCustomRequester(req)
        except Exception:
            pass
    return out_path
