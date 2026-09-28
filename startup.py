# tk-3de4 launcher: prepares the environment so 3DE loads the Toolkit engine on start.
import glob
import os
import re
import sys

import sgtk
from sgtk.platform import LaunchInformation, SoftwareLauncher, SoftwareVersion


class TDE4Launcher(SoftwareLauncher):

    EXECUTABLE_GLOBS = {
        "win32": ["C:/Program Files/3DE4_win64_r*/bin/3DE4.exe"],
        "linux2": ["/opt/3DE4_linux64_r*/bin/3DE4"],
        "linux": ["/opt/3DE4_linux64_r*/bin/3DE4"],
    }

    @property
    def minimum_supported_version(self):
        return "8.0"

    def prepare_launch(self, exec_path, args, file_to_open=None):
        env = {}

        # 3DE loads Python scripts from PYTHON_CUSTOM_SCRIPTS_3DE4 (several folders, ;-separated)
        startup = os.path.join(self.disk_location, "startup")
        paths = [startup]
        existing = os.environ.get("PYTHON_CUSTOM_SCRIPTS_3DE4")
        if existing:
            paths += [p for p in existing.split(os.pathsep) if p and p != startup]
        env["PYTHON_CUSTOM_SCRIPTS_3DE4"] = os.pathsep.join(paths)

        env["SGTK_ENGINE"] = self.engine_name
        env["SGTK_CONTEXT"] = sgtk.context.serialize(self.context)
        env["SGTK_MODULE_PATH"] = sgtk.get_sgtk_module_path()

        # Where the 3DE startup scripts find the bootstrap (python/nfa_3de_bootstrap.py).
        env["NFA_TK3DE4_ROOT"] = self.disk_location

        # First start on this computer: begin the PySide6 install now, detached, so 3DE
        # opens straight away and never waits for pip. The engine starts once it is done.
        try:
            pydir = os.path.join(self.disk_location, "python")
            if pydir not in sys.path:
                sys.path.insert(0, pydir)
            import nfa_3de_bootstrap as boot
            if boot.start_detached_install(boot.python_for_3de(exec_path)):
                self.logger.info("tk-3de4: PySide6 install running in the background")
        except Exception:
            self.logger.exception("tk-3de4: could not start the PySide6 install")
        pyside = self.get_setting("pyside_path")
        if pyside:
            env["NFA_3DE_PYSIDE_PATH"] = os.path.expandvars(pyside)

        if file_to_open:
            env["SGTK_FILE_TO_OPEN"] = file_to_open

        return LaunchInformation(exec_path, args, env)

    def scan_software(self):
        platform = "win32" if sgtk.util.is_windows() else "linux"
        found = []
        for pattern in self.EXECUTABLE_GLOBS.get(platform, []):
            for path in sorted(glob.glob(pattern)):
                m = re.search(r"_r(\d+(?:\.\d+)*)", path)
                if not m:
                    continue
                version = m.group(1)
                sw = SoftwareVersion(
                    version,
                    "3DEqualizer",
                    path,
                    os.path.join(self.disk_location, "icon_256.png"),
                )
                supported, reason = self._is_supported(sw)
                if supported:
                    found.append(sw)
                else:
                    self.logger.debug(reason)
        return found
