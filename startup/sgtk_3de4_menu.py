#
# 3DE4.script.name:    ShotGrid...
#
# 3DE4.script.version: v1.0.0
#
# 3DE4.script.gui:     Main Window::3DE4::File::ShotGrid
#
# 3DE4.script.comment: NFA ShotGrid panel (tk-3de4). Starts the engine if it is not running yet.
#
import os
import sys
import traceback


def _tk3de4_log(msg):
    import tempfile, time
    try:
        with open(os.path.join(tempfile.gettempdir(), "tk-3de4_debug.log"), "a", encoding="utf-8") as _f:
            _f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass
    print("[tk-3de4] " + msg)


def _sgtk_3de4_engine():
    import __main__
    import tde4
    root = os.environ.get("NFA_TK3DE4_ROOT")
    for p in (os.path.join(root, "python") if root else None, os.environ.get("SGTK_MODULE_PATH")):
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    if "SGTK_CONTEXT" not in os.environ:
        tde4.postQuestionRequester("NFA ShotGrid",
                                   "3DE was not started from ShotGrid Desktop.\n"
                                   "Close 3DE and start it from ShotGrid Desktop.", "OK")
        return None
    import sgtk
    engine = sgtk.platform.current_engine()
    if engine:
        return engine
    import nfa_3de_bootstrap as boot
    found = boot.find_pyside()
    if not found:
        inst = getattr(__main__, "_nfa_3de_installer", None)
        if inst is not None and inst.state in ("running", "busy"):
            tde4.postQuestionRequester("NFA ShotGrid",
                                       "The ShotGrid components are still being installed.\n"
                                       "This happens only once; please try again in a few minutes.", "OK")
        else:
            tde4.postQuestionRequester("NFA ShotGrid",
                                       "The ShotGrid components are not installed.\n"
                                       "Restart 3DE from ShotGrid Desktop to install them.", "OK")
        return None
    boot.add_to_path(found)
    ctx = sgtk.context.deserialize(os.environ["SGTK_CONTEXT"])
    return sgtk.platform.start_engine(os.environ.get("SGTK_ENGINE", "tk-3de4"), ctx.sgtk, ctx)


_tk3de4_log("menu clicked")
try:
    _eng = _sgtk_3de4_engine()
    _tk3de4_log("engine: %r" % (_eng,))
    if _eng:
        _eng.show_menu()
except Exception:
    _tk3de4_log("Error in menu:\n" + traceback.format_exc())
