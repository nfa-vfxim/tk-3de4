# tk-multi-workfiles2 scene operations voor 3DEqualizer 4 (tk-3de4).
import os

import sgtk
from sgtk.platform.qt import QtGui

HookClass = sgtk.get_hook_baseclass()


def _tde4():
    import tde4
    return tde4


class SceneOperation(HookClass):
    """Openen/opslaan/nieuw voor 3DE-projecten (.3de)."""

    def execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        tde4 = _tde4()
        self.logger.debug("3DE scene operation: %s %s", operation, file_path)

        if file_path:
            file_path = file_path.replace("/", os.sep)

        if operation == "current_path":
            return self._current_path(tde4)

        elif operation == "open":
            self._load(tde4, file_path)
            return True

        elif operation == "save":
            path = self._current_path(tde4)
            if not path:
                raise sgtk.TankError("This 3DE project has not been saved yet; use File Save As.")
            self._save(tde4, path)
            return True

        elif operation == "save_as":
            folder = os.path.dirname(file_path)
            if folder and not os.path.isdir(folder):
                self.parent.ensure_folder_exists(folder)
            self._save(tde4, file_path)
            return True

        elif operation == "reset":
            # Vraag bij onopgeslagen wijzigingen; daarna leeg project.
            if self._is_modified(tde4):
                res = QtGui.QMessageBox.question(
                    None,
                    "Save?",
                    "The current 3DE project has unsaved changes.\nSave first?",
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel,
                )
                if res == QtGui.QMessageBox.Cancel:
                    return False
                if res == QtGui.QMessageBox.Yes:
                    path = self._current_path(tde4)
                    if not path:
                        # Geen pad: laat de gebruiker eerst via Save As opslaan.
                        QtGui.QMessageBox.information(
                            None, "Save", "This project has no file name yet. Use File Save As first."
                        )
                        return False
                    self._save(tde4, path)
            if parent_action == "new_file":
                self._new(tde4)
            return True

        elif operation == "prepare_new":
            return True

        return True

    # ------------------------------------------------------------------ helpers
    def _current_path(self, tde4):
        for name in ("getProjectPath",):
            if hasattr(tde4, name):
                path = getattr(tde4, name)()
                return path or ""
        return ""

    def _load(self, tde4, path):
        ok = tde4.loadProject(path)
        if ok is False or ok == 0:
            raise sgtk.TankError("3DE could not open the project: %s" % path)

    def _save(self, tde4, path):
        ok = tde4.saveProject(path)
        if ok is False or ok == 0:
            raise sgtk.TankError("3DE could not save the project: %s" % path)

    def _is_modified(self, tde4):
        if hasattr(tde4, "isProjectUpToDate"):
            try:
                return not tde4.isProjectUpToDate()
            except Exception:
                pass
        return False

    def _new(self, tde4):
        if hasattr(tde4, "newProject"):
            tde4.newProject()
        else:
            self.logger.warning("tde4.newProject does not exist; the current project stays open.")
