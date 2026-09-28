# First-run setup for tk-3de4: installs PySide6 locally, in the background.
#
# The install runs as its own detached process (this file with --install, in 3DE's
# python.exe), started by the ShotGrid Desktop launcher before 3DE opens. 3DE itself
# never waits for it: its startup script only polls for the finished install and then
# starts the engine. (v1.0.0 ran pip from inside 3DE's startup, which froze 3DE and
# kept the File > ShotGrid entry from registering until a restart.)
#
# 3DE 8.1 ships Python 3.11 without Qt. tk-core 0.21.7 needs the *full* PySide6
# (it also loads QtWebEngine), about 500 MB, so it is installed once per computer:
#   %LOCALAPPDATA%\NFA\3de\pyside6\6.5.3\
# Local disk, not a network share: Qt loads hundreds of DLLs at every start.
# This module must not import Qt or sgtk — it runs before either exists, and it must
# stay Python 3.7 compatible (ShotGrid Desktop imports it in the launcher).
import os
import shutil
import subprocess
import sys
import time

PYSIDE_VERSION = "6.5.3"
LOCK_MAX_AGE = 30 * 60          # a lock older than this is a crashed install
MARKER = ".nfa_complete"


def base_dir():
    root = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(root, "NFA", "3de", "pyside6")


def install_dir():
    return os.path.join(base_dir(), PYSIDE_VERSION)


def _complete(path):
    """A usable PySide6 install: the package itself plus the WebEngine module tk-core needs."""
    pkg = os.path.join(path, "PySide6")
    return (os.path.isfile(os.path.join(pkg, "__init__.py"))
            and os.path.isfile(os.path.join(pkg, "QtWebEngineWidgets.pyd")))


def candidates():
    out = []
    env = os.environ.get("NFA_3DE_PYSIDE_PATH")
    if env:
        out.append(os.path.expandvars(env))
    out.append(install_dir())
    # The manual install from the proof of concept, still valid on that one machine.
    out.append(os.path.join(os.path.expanduser("~"), "nfa_3de", "pyside6"))
    return out


def find_pyside():
    """Path of a complete PySide6 install, or None."""
    for path in candidates():
        if path == install_dir():
            if os.path.isfile(os.path.join(path, MARKER)) and _complete(path):
                return path
        elif _complete(path):
            return path
    return None


def add_to_path(path):
    if path and path not in sys.path:
        sys.path.insert(0, path)


def python_exe():
    """3DE's own python.exe (…\\3DE4_win64_r8.1\\sys_data\\py311_inst\\python.exe)."""
    root = os.path.dirname(os.path.dirname(sys.executable))
    exe = os.path.join(root, "sys_data", "py311_inst", "python.exe")
    return exe if os.path.isfile(exe) else None


def log_path():
    return os.path.join(base_dir(), "install_%s.log" % PYSIDE_VERSION)


def installing():
    """True while an install is running somewhere on this computer (fresh lock file)."""
    lock = install_dir() + ".lock"
    return os.path.isfile(lock) and time.time() - os.path.getmtime(lock) < LOCK_MAX_AGE


def python_for_3de(exec_path):
    """3DE's python.exe, derived from the 3DE executable (…\\bin\\3DE4.exe)."""
    root = os.path.dirname(os.path.dirname(exec_path))
    exe = os.path.join(root, "sys_data", "py311_inst", "python.exe")
    return exe if os.path.isfile(exe) else None


def start_detached_install(py):
    """Start the install as its own process, detached from whoever calls this.

    Called from the ShotGrid Desktop launcher *before* 3DE starts, so 3DE never
    waits for pip. Returns True when an install was started or is already running."""
    if find_pyside():
        return False
    if installing():
        return True
    if not py or not os.path.isfile(py):
        return False
    os.makedirs(base_dir(), exist_ok=True)
    flags = 0
    for name in ("DETACHED_PROCESS", "CREATE_NEW_PROCESS_GROUP", "CREATE_NO_WINDOW"):
        flags |= getattr(subprocess, name, 0)
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(key, None)
    subprocess.Popen([py, os.path.abspath(__file__), "--install"],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=flags, close_fds=True, env=env)
    return True


def run_install():
    """The install itself. Runs in 3DE's python.exe as a separate process (--install)."""
    os.makedirs(base_dir(), exist_ok=True)
    lock = install_dir() + ".lock"
    partial = install_dir() + ".partial"
    if installing():
        return 0
    with open(lock, "w") as f:
        f.write(str(os.getpid()))
    code = 1
    try:
        shutil.rmtree(partial, ignore_errors=True)
        with open(log_path(), "w") as log:
            log.write("NFA tk-3de4: installing PySide6 %s into %s\n" % (PYSIDE_VERSION, install_dir()))
            log.flush()
            code = subprocess.call(
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                 "--no-warn-script-location", "PySide6==%s" % PYSIDE_VERSION, "--target", partial],
                stdout=log, stderr=subprocess.STDOUT)
            if code == 0 and _complete(partial):
                target = install_dir()
                shutil.rmtree(target, ignore_errors=True)
                os.replace(partial, target)
                with open(os.path.join(target, MARKER), "w") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
                log.write("\nDone.\n")
            else:
                log.write("\nFailed (pip exit code %s).\n" % code)
                code = code or 1
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass
    return code


if __name__ == "__main__" and "--install" in sys.argv:
    sys.exit(run_install())
