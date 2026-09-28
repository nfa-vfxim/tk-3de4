# tk-3de4 engine: ShotGrid Toolkit in 3DEqualizer 4 R8+ (Python 3.11, external PySide6).
#
# Deliberately thin. The engine does what rarely changes: Qt next to 3DE (events pumped
# through tde4.setTimerCallbackFunction), the quit guard, the File > ShotGrid entry and the
# Workfiles hook. The tools themselves (panel, Shot Overview, Load Plate, Export to Nuke,
# thumbnails) live in the pipeline repo, C:/pipeline/3de/python/tk_3de4, and are loaded
# from there, so tool updates ship with the pipeline, not with an engine release.
# A copy is bundled in python/tk_3de4 as a fallback.
import os
import sys

import sgtk

PUMP_NAME = "_sgtk_3de_qt_pump"
QUIT_NAME = "_sgtk_3de_quit_guard"
DEFAULT_TOOLS_PATH = "C:/pipeline/3de/python"


def _debug_log(msg):
    import tempfile, time
    try:
        with open(os.path.join(tempfile.gettempdir(), "tk-3de4_debug.log"), "a", encoding="utf-8") as f:
            f.write("%s [engine] %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass
    print("[tk-3de4] " + msg)


def _add_pyside_path(extra=None):
    """PySide6 on sys.path: an explicit path first, else the local install from the
    first-run bootstrap (%LOCALAPPDATA%\\NFA\\3de\\pyside6\\<version>)."""
    if extra:
        extra = os.path.expandvars(extra)
        if os.path.isdir(extra):
            if extra not in sys.path:
                sys.path.insert(0, extra)
            return extra
    pydir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python")
    if pydir not in sys.path:
        sys.path.insert(0, pydir)
    import nfa_3de_bootstrap as boot
    found = boot.find_pyside()
    boot.add_to_path(found)
    return found


class TDE4Engine(sgtk.platform.Engine):

    def __init__(self, *args, **kwargs):
        # PySide6 moet op sys.path staan vóór tk-core zijn Qt-shim opzet (in Engine.__init__)
        _add_pyside_path()
        self._qt_app = None
        self._pump_active = False
        super().__init__(*args, **kwargs)

    # ------------------------------------------------------------------ info
    @property
    def host_info(self):
        info = {"name": "3DEqualizer", "version": "unknown"}
        try:
            import tde4
            info["version"] = tde4.get3DEVersion()
        except Exception:
            pass
        return info

    @property
    def context_change_allowed(self):
        return True

    @property
    def has_ui(self):
        return True

    # ------------------------------------------------------------------ Qt-basis
    def _define_qt_base(self):
        """Laat tk-core Qt laden, maar log precies waarom het mislukt (tk-core slikt de fout)."""
        try:
            extra = self.get_setting("pyside_path")
        except Exception:
            extra = None
        _add_pyside_path(extra)
        base = super()._define_qt_base()
        if base.get("qt_gui") is None:
            import traceback
            _debug_log("tk-core _define_qt_base returned no QtGui. sys.path[:5]=%r" % (sys.path[:5],))
            try:
                import PySide6
                _debug_log("PySide6 imports on its own: %s (%s)" % (PySide6.__version__, PySide6.__file__))
            except Exception:
                _debug_log("import PySide6 failed:\n" + traceback.format_exc())
            try:
                from tank.util.qt_importer import QtImporter
                imp = QtImporter()
                _debug_log("QtImporter: binding=%r QtGui=%r" % (imp.binding_name, imp.QtGui))
            except Exception:
                _debug_log("QtImporter failed:\n" + traceback.format_exc())
        return base

    # ------------------------------------------------------------------ lifecycle
    def pre_app_init(self):
        try:
            sgtk.LogManager().initialize_base_file_handler("tk-3de4")
        except Exception:
            pass
        _add_pyside_path(self.get_setting("pyside_path"))
        self._init_qt_app()

    def post_app_init(self):
        self._start_qt_pump()
        self._install_quit_guard()
        try:
            import tde4
            _debug_log("tde4 project functions: %s" % [n for n in dir(tde4) if "roject" in n])
            _debug_log("tde4 camera functions: %s" % [n for n in dir(tde4) if "amera" in n])
        except Exception:
            pass
        self.logger.info("tk-3de4 started in %s, context: %s", self.host_info["version"], self.context)

    # ------------------------------------------------------------------ afsluiten
    def _install_quit_guard(self):
        """Vraagt bevestiging bij Exit: 'File' zit direct boven 'Exit' in het 3DE-menu.

        tde4.setQuit3DECallbackFunction roept onze functie aan als 3DE wil afsluiten.
        Een 3DE-eigen vraagvenster (postQuestionRequester) in plaats van Qt, omdat de
        Qt-pomp tijdens het afsluiten mogelijk al stilligt."""
        try:
            import tde4
            import __main__
        except ImportError:
            return

        def quit_guard(*args):
            try:
                import tde4
                dirty = False
                try:
                    dirty = not tde4.isProjectUpToDate()
                except Exception:
                    pass
                msg = "Are you sure you want to quit 3DEqualizer?"
                if dirty:
                    msg += "\n\nYour project has unsaved changes!"
                ret = tde4.postQuestionRequester("Quit", msg, "Quit", "Cancel")
                _debug_log("quit guard: answer %r" % (ret,))
                return ret == 1
            except Exception as exc:
                _debug_log("quit guard error: %s" % exc)
                return True

        setattr(__main__, QUIT_NAME, quit_guard)
        try:
            tde4.setQuit3DECallbackFunction(QUIT_NAME)
            _debug_log("quit guard installed")
        except Exception as exc:
            _debug_log("setQuit3DECallbackFunction failed: %s" % exc)

    def destroy_engine(self):
        self._stop_qt_pump()

    # ------------------------------------------------------------------ Qt
    def _init_qt_app(self):
        from sgtk.platform.qt import QtGui
        if QtGui is None:
            raise RuntimeError(
                "tk-core could not load PySide. sys.path has no PySide6 for Python 3.11 "
                "(pyside_path setting / NFA_3DE_PYSIDE_PATH / local install)."
            )
        QtWidgets = QtGui  # tk-core shim: QtGui bevat ook de widgets
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(["3DE4"])
        app.setQuitOnLastWindowClosed(False)
        self._qt_app = app
        try:
            self._initialize_dark_look_and_feel()
        except Exception:
            self.logger.debug("Dark look and feel not applied", exc_info=True)

    def _start_qt_pump(self):
        try:
            import tde4
        except ImportError:
            return
        import __main__
        app = self._qt_app

        def pump():
            try:
                app.processEvents()
            except Exception:
                pass

        setattr(__main__, PUMP_NAME, pump)
        interval = int(self.get_setting("qt_pump_interval") or 20)
        tde4.setTimerCallbackFunction(PUMP_NAME, interval)
        self._pump_active = True

    def _stop_qt_pump(self):
        if not self._pump_active:
            return
        try:
            import tde4
            tde4.removeTimerCallback()
        except Exception:
            self.logger.debug("removeTimerCallback failed", exc_info=True)
        self._pump_active = False

    def _get_dialog_parent(self):
        return None

    def _create_dialog(self, title, bundle, widget, parent):
        dialog = super()._create_dialog(title, bundle, widget, parent)
        from sgtk.platform.qt import QtCore
        # 3DE is geen Qt-venster: houd Toolkit-vensters boven 3DE
        dialog.setWindowFlags(dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self._center_when_shown(dialog)
        return dialog

    def _center_on_primary(self, widget):
        """Zet een venster midden op het hoofdscherm (primary screen)."""
        from sgtk.platform.qt import QtGui
        try:
            app = QtGui.QApplication.instance()
            screen = app.primaryScreen()
            area = screen.availableGeometry()
            frame = widget.frameGeometry()
            frame.moveCenter(area.center())
            top_left = frame.topLeft()
            # nooit buiten het scherm (bij vensters groter dan het scherm)
            x = max(area.left(), top_left.x())
            y = max(area.top(), top_left.y())
            widget.move(x, y)
        except Exception:
            self.logger.debug("Centering failed", exc_info=True)

    def _center_when_shown(self, widget):
        """Centreert zodra het venster zijn uiteindelijke grootte heeft (na show())."""
        from sgtk.platform.qt import QtCore
        for delay in (0, 50, 200):
            QtCore.QTimer.singleShot(delay, lambda w=widget: self._center_on_primary(w) if w.isVisible() else None)

    # ------------------------------------------------------------------ menu
    def _collect_commands(self):
        """Geeft [(groepnaam, [(naam, callback), ...]), ...] terug; favorieten eerst."""
        commands = dict(self.commands)
        groups = []
        favs = []
        for fav in self.get_setting("menu_favourites") or []:
            for name, cmd in commands.items():
                app = cmd["properties"].get("app")
                if name == fav["name"] and app and app.instance_name == fav["app_instance"]:
                    favs.append((name, cmd["callback"]))
        if favs:
            groups.append(("Favorites", favs))
        by_app = {}
        for name, cmd in sorted(commands.items()):
            if cmd["properties"].get("type") == "context_menu":
                continue
            app = cmd["properties"].get("app")
            by_app.setdefault(app.display_name if app else "Other", []).append((name, cmd["callback"]))
        groups += sorted(by_app.items())
        return groups

    def show_menu(self):
        """Opent het ShotGrid-paneel (File > ShotGrid...), in NFA Shot Manager-stijl."""
        old = getattr(self, "_panel", None)
        if old is not None:
            try:
                old.close()
                old.deleteLater()
            except Exception:
                pass
        tk_3de4 = self._ui_module()
        panel = tk_3de4.ShotGridPanel(self)
        panel.adjustSize()
        panel.show()
        self._center_on_primary(panel)
        panel.raise_()
        panel.activateWindow()
        self._panel = panel

    def _ui_module(self):
        """The tools package, preferably from the pipeline repo (tools_path setting,
        default C:/pipeline/3de/python), else the copy bundled with the engine.

        Imported directly, not via self.import_module: tk-core 0.21.7 loads the python/
        folder itself as a package there, which fails for this layout."""
        if getattr(self, "_tools_module", None) is not None:
            return self._tools_module
        tools = os.path.expandvars(self.get_setting("tools_path") or DEFAULT_TOOLS_PATH)
        bundled = os.path.join(self.disk_location, "python")
        use = tools if os.path.isfile(os.path.join(tools, "tk_3de4", "__init__.py")) else bundled
        if use not in sys.path:
            sys.path.insert(0, use)
        import tk_3de4
        self._tools_module = tk_3de4
        self.logger.info("Tools loaded from %s", os.path.dirname(tk_3de4.__file__))
        return tk_3de4

    def _jump_to_sg(self):
        from sgtk.platform.qt import QtCore, QtGui
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.context.shotgun_url))

    def _jump_to_fs(self):
        for path in self.context.filesystem_locations:
            if os.path.isdir(path):
                os.startfile(path) if sys.platform == "win32" else None

    # ------------------------------------------------------------------ logging
    def _emit_log_message(self, handler, record):
        msg = handler.format(record)
        print(msg)
