# First-run setup for tk-3de4: installs PySide6 locally, in the background.
#
# 3DE 8.1 ships Python 3.11 without Qt. tk-core 0.21.7 needs the *full* PySide6
# (it also loads QtWebEngine), about 500 MB, so it is installed once per computer:
#   %LOCALAPPDATA%\NFA\3de\pyside6\6.5.3\
# Local disk, not a network share: Qt loads hundreds of DLLs at every start.
# This module must not import Qt or sgtk — it runs before either exists.
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


class Installer(object):
    """pip install into a .partial folder; renamed into place only when it succeeded,
    so a cancelled or failed install never looks complete."""

    def __init__(self):
        self.proc = None
        self.state = "idle"          # idle | running | busy | done | failed
        self.message = ""
        self._log = None
        self._lock = install_dir() + ".lock"
        self._partial = install_dir() + ".partial"

    def start(self):
        os.makedirs(base_dir(), exist_ok=True)
        if os.path.isfile(self._lock) and time.time() - os.path.getmtime(self._lock) < LOCK_MAX_AGE:
            self.state = "busy"      # another 3DE on this computer is already installing
            return self.state
        py = python_exe()
        if not py:
            self.state, self.message = "failed", "3DE's python.exe was not found next to %s" % sys.executable
            return self.state
        with open(self._lock, "w") as f:
            f.write(str(os.getpid()))
        shutil.rmtree(self._partial, ignore_errors=True)
        self._log = open(log_path(), "w")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        env = dict(os.environ)
        for key in ("PYTHONPATH", "PYTHONHOME"):
            env.pop(key, None)
        self.proc = subprocess.Popen(
            [py, "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location",
             "PySide6==%s" % PYSIDE_VERSION, "--target", self._partial],
            stdout=self._log, stderr=subprocess.STDOUT, creationflags=flags, env=env)
        self.state = "running"
        return self.state

    def poll(self):
        """Call regularly. Returns the state; 'done' once PySide6 is in place."""
        if self.state == "busy":
            if find_pyside():
                self.state = "done"
            elif not os.path.isfile(self._lock):
                self.state = "failed"
                self.message = "The install in the other 3DE stopped. Restart 3DE to try again."
            return self.state
        if self.state != "running" or self.proc.poll() is None:
            return self.state
        try:
            self._log.close()
        except Exception:
            pass
        if self.proc.returncode == 0 and _complete(self._partial):
            target = install_dir()
            shutil.rmtree(target, ignore_errors=True)
            os.replace(self._partial, target)
            with open(os.path.join(target, MARKER), "w") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            self.state = "done"
        else:
            self.state = "failed"
            self.message = "pip stopped with code %s. See %s" % (self.proc.returncode, log_path())
        try:
            os.remove(self._lock)
        except OSError:
            pass
        return self.state
