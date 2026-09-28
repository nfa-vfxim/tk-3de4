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

    # First run on this computer: install PySide6 in the background, start the engine after.
    inst = boot.Installer()
    state = inst.start()
    __main__._nfa_3de_installer = inst
    _tk3de4_log("PySide6 missing, installer: %s %s" % (state, inst.message))
    if state == "failed":
        tde4.postQuestionRequester("NFA ShotGrid", "Could not install the ShotGrid components:\n%s" % inst.message, "OK")
        return
    tde4.postQuestionRequester(
        "NFA ShotGrid",
        "First start on this computer: the ShotGrid components (PySide6, about 500 MB)\n"
        "are being installed in the background. This happens only once and takes a few minutes.\n\n"
        "You can keep working. The ShotGrid menu becomes available when it is done.",
        "OK")

    def _poll(*args):
        try:
            s = inst.poll()
            if s in ("running", "busy"):
                return
            try:
                tde4.removeTimerCallback()
            except Exception:
                pass
            if s == "done":
                boot.add_to_path(boot.find_pyside())
                _tk3de4_start_engine()      # the engine installs its own Qt timer
                tde4.postQuestionRequester("NFA ShotGrid",
                                           "ShotGrid is ready. Open it with File > ShotGrid...", "OK")
            else:
                _tk3de4_log("PySide6 install failed: %s" % inst.message)
                tde4.postQuestionRequester("NFA ShotGrid",
                                           "Installing the ShotGrid components failed.\n%s" % inst.message, "OK")
        except Exception:
            _tk3de4_log("install poll error:\n" + traceback.format_exc())

    __main__._nfa_3de_install_poll = _poll
    tde4.setTimerCallbackFunction("_nfa_3de_install_poll", 2000)


_tk3de4_log("startup script started")
try:
    if "SGTK_CONTEXT" in os.environ:
        _tk3de4_startup()
except Exception:
    _tk3de4_log("Starting the engine at startup failed:\n" + traceback.format_exc())
