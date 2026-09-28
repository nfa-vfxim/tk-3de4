#
# 3DE4.script.name:    tk-3de4 startup
#
# 3DE4.script.startup: true
#
# 3DE4.script.hide:    true
#
# 3DE4.script.comment: Starts the ShotGrid engine when 3DE starts (installs PySide6 on first use).
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


def _tk3de4_start_engine():
    import sgtk
    if not sgtk.platform.current_engine():
        ctx = sgtk.context.deserialize(os.environ["SGTK_CONTEXT"])
        sgtk.platform.start_engine(os.environ.get("SGTK_ENGINE", "tk-3de4"), ctx.sgtk, ctx)
        _tk3de4_log("engine started")


def _tk3de4_startup():
    import __main__
    import tde4
    root = os.environ.get("NFA_TK3DE4_ROOT")
    for p in (os.path.join(root, "python") if root else None, os.environ.get("SGTK_MODULE_PATH")):
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)
    import nfa_3de_bootstrap as boot

    found = boot.find_pyside()
    if found:
        boot.add_to_path(found)
        _tk3de4_start_engine()
        return

    # First start on this computer. The launcher already started the PySide6 install
    # (detached); start it here only if it did not. Nothing in here may block or open a
    # requester: 3DE is still starting up. A light timer checks every few seconds and
    # starts the engine once PySide6 is in place (the engine then takes over the timer).
    if not boot.installing():
        boot.start_detached_install(boot.python_exe())
    _tk3de4_log("PySide6 not installed yet; waiting for the background install")

    def _poll(*args):
        try:
            path = boot.find_pyside()
            if not path:
                return
            boot.add_to_path(path)
            _tk3de4_start_engine()
            _tk3de4_log("PySide6 installed; engine started")
        except Exception:
            _tk3de4_log("install poll error:\n" + traceback.format_exc())

    __main__._nfa_3de_install_poll = _poll
    tde4.setTimerCallbackFunction("_nfa_3de_install_poll", 3000)


_tk3de4_log("startup script started")
try:
    if "SGTK_CONTEXT" in os.environ:
        _tk3de4_startup()
except Exception:
    _tk3de4_log("Starting the engine at startup failed:\n" + traceback.format_exc())
