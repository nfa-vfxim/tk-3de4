# ShotGrid-paneel voor 3DE, in de stijl van de NFA Shot Manager (Nuke).
# Kleuren/knopstijlen komen 1-op-1 uit nfa_shot_manager.py zodat de tools als één familie voelen.
import os
import re

from sgtk.platform.qt import QtCore, QtGui

TOOL_VERSION = "1.0.0"
TOOL_AUTHOR = "Luuk Kamphuis"
HELP_FILENAME = "HELP.html"
MATCHMOVE_STEPS = ("matchmove", "tracking", "track", "mm", "camtrack")

# ---------------------------------------------------------------- stijl (uit NFA Shot Manager)
STYLE = """
QWidget#NFA3DEPanel { background-color: #1c1c1e; }
QFrame#titleBar { background-color: #2a2a2c; border-radius: 9px; }
QFrame#contextCard { background-color: #222224; border-radius: 9px; }
QLabel { color: #e4e4e6; }
QLabel#status { color: #6c6c70; font-size: 10px; padding: 2px; }
QLabel#section { color: #6c6c70; font-size: 9px; font-weight: 600; letter-spacing: 1.2px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical { background: #48484a; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #5a5a5e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""

HOVER_LIFT = 0.16


def _shade(colour, amount):
    colour = colour.lstrip("#")
    rgb = [int(colour[i:i + 2], 16) for i in (0, 2, 4)]
    if amount >= 0:
        rgb = [int(c + (255 - c) * amount) for c in rgb]
    else:
        rgb = [int(c * (1 + amount)) for c in rgb]
    return "#%02x%02x%02x" % tuple(max(0, min(255, c)) for c in rgb)


def _btn_style(bg, hover_bg, pressed_bg=None, text="white"):
    pressed_bg = pressed_bg or _shade(bg, -0.10)
    return """
        QPushButton {{
            background-color: {bg}; color: {text}; border: none;
            border-radius: 7px; font-size: 11px; font-weight: 600;
            padding: 7px 12px;
        }}
        QPushButton:hover {{ background-color: {hover}; color: #ffffff; }}
        QPushButton:pressed {{ background-color: {pressed}; }}
        QPushButton:disabled {{ background-color: #2a2a2c; color: #5c5c60; }}
    """.format(bg=bg, text=text, hover=hover_bg, pressed=pressed_bg)


def _tinted(fill, pressed, text):
    return """
        QPushButton {{
            background-color: {fill}; color: {text}; border: none;
            border-radius: 7px; font-size: 11px; font-weight: 600;
            padding: 7px 12px;
        }}
        QPushButton:hover {{ background-color: {hover}; color: {htext}; }}
        QPushButton:pressed {{ background-color: {pressed}; color: #ffffff; }}
        QPushButton:disabled {{ background-color: #262628; color: #57575b; }}
    """.format(fill=fill, text=text, hover=_shade(fill, HOVER_LIFT),
               htext=_shade(text, 0.22), pressed=pressed)


BTN_PRIMARY = _btn_style("#39704f", _shade("#39704f", HOVER_LIFT), text="#f0f6f2")
BTN_SAVE = _tinted("#332828", "#4a3634", "#d99a91")
BTN_REFRESH = _tinted("#252f3a", "#354354", "#8fb6dd")
BTN_QUIET = _tinted("#2a2a2c", "#39393d", "#9c9ca3")
BTN_ICON = BTN_QUIET.replace("padding: 7px 12px;", "padding: 4px 0; font-size: 13px;")


def _pill(text, bg, fg):
    # Upper case like the Shot Manager, but versions keep their small v (TRACK v3).
    lbl = QtGui.QLabel(re.sub(r"\bV(\d+)\b", r"v\1", text.upper()))
    lbl.setStyleSheet(
        "background:%s; color:%s; border-radius:6px; padding:2px 7px; "
        "font-size:9px; font-weight:600; letter-spacing:0.6px;" % (bg, fg)
    )
    return lbl


def _classify(name):
    """Welke stijl een favoriet krijgt: open = primair, save = schrijft een bestand."""
    low = name.lower()
    if "open" in low:
        return BTN_PRIMARY
    if "save" in low or "publish" in low or "snapshot" in low:
        return BTN_SAVE
    return BTN_QUIET


class ShotGridPanel(QtGui.QWidget):
    """Niet-modaal ShotGrid-paneel dat boven 3DE blijft staan."""

    def __init__(self, engine, parent=None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self._engine = engine
        self.setObjectName("NFA3DEPanel")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setWindowTitle("ShotGrid – 3DEqualizer")
        self.setStyleSheet(STYLE)
        self.setMinimumWidth(320)
        self._build()

    # ------------------------------------------------------------ opbouw
    def _build(self):
        eng = self._engine
        ctx = eng.context
        root = QtGui.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)

        # titelbalk
        tb = QtGui.QFrame()
        tb.setObjectName("titleBar")
        tb_row = QtGui.QHBoxLayout(tb)
        tb_row.setContentsMargins(14, 10, 10, 10)
        tbl = QtGui.QVBoxLayout()
        tbl.setSpacing(1)
        t = QtGui.QLabel("NFA ShotGrid")
        t.setStyleSheet("font-size:15px; font-weight:600; color:#f2f2f7;")
        s = QtGui.QLabel("3DEQUALIZER · VFXIM PIPELINE")
        s.setStyleSheet("font-size:9px; font-weight:600; color:#7fa8cc; letter-spacing:1.2px;")
        tbl.addWidget(t)
        tbl.addWidget(s)
        tb_row.addLayout(tbl, 1)
        help_btn = QtGui.QPushButton("?")
        help_btn.setFixedSize(30, 28)
        help_btn.setStyleSheet(BTN_ICON)
        help_btn.setCursor(QtCore.Qt.PointingHandCursor)
        help_btn.setToolTip("Open the help page")
        help_btn.clicked.connect(self._open_help)
        tb_row.addWidget(help_btn, 0, QtCore.Qt.AlignVCenter)
        root.addWidget(tb)

        # contextkaart
        card = QtGui.QFrame()
        card.setObjectName("contextCard")
        cl = QtGui.QVBoxLayout(card)
        cl.setContentsMargins(14, 11, 14, 11)
        cl.setSpacing(5)

        if ctx.entity:
            head = ctx.entity.get("name") or str(ctx.entity.get("id"))
        elif ctx.project:
            head = ctx.project.get("name")
        else:
            head = "No context"
        title = QtGui.QLabel(head)
        title.setStyleSheet("font-size:13px; font-weight:600; color:#e8e8ea;")
        cl.addWidget(title)

        sub_parts = []
        if ctx.project and ctx.entity:
            sub_parts.append(ctx.project.get("name"))
        if ctx.entity:
            sub_parts.append(ctx.entity.get("type"))
        if sub_parts:
            sub = QtGui.QLabel(" · ".join(p for p in sub_parts if p))
            sub.setStyleSheet("color:#8e8e93; font-size:11px;")
            cl.addWidget(sub)

        pills = QtGui.QHBoxLayout()
        pills.setSpacing(5)
        if ctx.step:
            pills.addWidget(_pill(ctx.step.get("name", ""), "#26333c", "#8fc2e0"))
        if ctx.task:
            pills.addWidget(_pill(ctx.task.get("name", ""), "#302a3c", "#b8a8dd"))
        if not ctx.task:
            pills.addWidget(_pill("no task", "#2a2a2c", "#8e8e93"))
        pills.addStretch(1)
        cl.addLayout(pills)

        self._file_lbl = QtGui.QLabel()
        self._file_lbl.setStyleSheet("color:#8e8e93; font-size:10px;")
        self._file_lbl.setWordWrap(True)
        cl.addWidget(self._file_lbl)
        self._update_file_label()
        root.addWidget(card)

        root.addWidget(self._button("Shot Overview", self._open_overview, BTN_REFRESH, close=False,
                                    tip="All shots of this project with thumbnails and matchmove status"))

        # Started without a task (project context): offer the user's own tasks,
        # matchmove first, so one click puts 3DE in the right shot and step.
        if not ctx.task:
            tasks = self._my_tasks()
            if tasks:
                sec = QtGui.QLabel("MY TASKS")
                sec.setObjectName("section")
                root.addWidget(sec)
                for task in tasks[:8]:
                    ent = (task.get("entity") or {}).get("name") or "?"
                    step = (task.get("step") or {}).get("name") or ""
                    label = "%s · %s" % (ent, task.get("content") or "")
                    if step and step.lower() != (task.get("content") or "").lower():
                        label += "  (%s)" % step
                    style = BTN_PRIMARY if self._is_matchmove(task) else BTN_QUIET
                    root.addWidget(self._button(label, lambda t=task: self._switch_to_task(t), style,
                                                close=False, tip="Switch 3DE to this task"))

        # acties
        groups = eng._collect_commands()
        favs = []
        rest = []
        for group, items in groups:
            if group == "Favorites":
                favs = items
            else:
                rest.append((group, items))
        fav_names = set(n for n, _ in favs)

        if favs:
            row = QtGui.QHBoxLayout()
            row.setSpacing(6)
            for name, cb in favs:
                row.addWidget(self._button(name.replace("...", "").strip(), cb, _classify(name)))
            root.addLayout(row)

        # plates (02_source) — alleen zinvol met een shot
        if ctx.entity and ctx.entity.get("type") == "Shot":
            sec = QtGui.QLabel("PLATES")
            sec.setObjectName("section")
            root.addSpacing(4)
            root.addWidget(sec)
            prow = QtGui.QHBoxLayout()
            prow.setSpacing(6)
            prow.addWidget(self._button("Load Plate", self._open_plate_dialog, BTN_QUIET, close=False,
                                        tip="Load a plate of this shot from 02_source as a camera"))
            prow.addWidget(self._button("Export to Nuke", self._export_to_nuke, BTN_SAVE, close=False,
                                        tip="Export the LD_3DE4 node of the current camera to this shot's publish folder"))
            root.addLayout(prow)

        # overige apps (zonder dubbelingen met de favorieten)
        body = QtGui.QVBoxLayout()
        body.setSpacing(6)
        for group, items in rest:
            items = [(n, cb) for n, cb in items if n not in fav_names]
            if not items:
                continue
            sec = QtGui.QLabel(group.upper())
            sec.setObjectName("section")
            body.addSpacing(4)
            body.addWidget(sec)
            for name, cb in items:
                body.addWidget(self._button(name, cb, BTN_QUIET))
        root.addLayout(body)

        # navigatie
        sep = QtGui.QFrame()
        sep.setFrameShape(QtGui.QFrame.HLine)
        sep.setStyleSheet("color:#2e2e30; max-height:1px;")
        root.addSpacing(2)
        root.addWidget(sep)
        nav = QtGui.QHBoxLayout()
        nav.setSpacing(6)
        nav.addWidget(self._button("ShotGrid", eng._jump_to_sg, BTN_REFRESH, close=False,
                                   tip="Open this context in ShotGrid"))
        nav.addWidget(self._button("Explorer", eng._jump_to_fs, BTN_REFRESH, close=False,
                                   tip="Open the folder of this context"))
        root.addLayout(nav)

        # voetregel
        foot = QtGui.QLabel("v%s · %s" % (TOOL_VERSION, TOOL_AUTHOR))
        foot.setStyleSheet("color:#555; font-size:9px;")
        foot.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        foot.setToolTip("tk-3de4 %s · %s" % (TOOL_VERSION, eng.host_info.get("version", "")))
        root.addWidget(foot)

    def _button(self, text, cb, style, close=True, tip=None):
        btn = QtGui.QPushButton(text)
        btn.setStyleSheet(style)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        if tip:
            btn.setToolTip(tip)

        def run():
            if close:
                self.close()
            try:
                cb()
            except Exception:
                self._engine.logger.exception("Error in '%s'", text)

        btn.clicked.connect(run)
        return btn

    def _open_plate_dialog(self):
        dlg = PlateDialog(self._engine, self)
        self._plate_dialog = dlg
        dlg.show()
        self._engine._center_on_primary(dlg)
        dlg.raise_()
        dlg.activateWindow()

    # ------------------------------------------------------------ my tasks
    def _is_matchmove(self, task):
        step = ((task.get("step") or {}).get("name") or "").lower()
        name = (task.get("content") or "").lower()
        return step in MATCHMOVE_STEPS or name in MATCHMOVE_STEPS

    def _current_user(self):
        user = self._engine.context.user
        if not user:
            try:
                import sgtk
                user = sgtk.util.get_current_user(self._engine.sgtk)
            except Exception:
                user = None
        return user

    def _my_tasks(self):
        """Tasks in this project assigned to the current user, matchmove first."""
        eng = self._engine
        user = self._current_user()
        if not user or not eng.context.project:
            return []
        try:
            tasks = eng.shotgun.find(
                "Task",
                [["project", "is", eng.context.project],
                 ["task_assignees", "is", {"type": "HumanUser", "id": user["id"]}],
                 ["sg_status_list", "not_in", ["omt", "apr"]]],
                ["content", "step", "entity", "sg_status_list"])
        except Exception:
            eng.logger.exception("Could not fetch my tasks")
            return []
        tasks = [t for t in tasks if t.get("entity")]
        tasks.sort(key=lambda t: (not self._is_matchmove(t),
                                  (t["entity"].get("name") or ""), t.get("content") or ""))
        return tasks

    def _switch_to_task(self, task):
        """Change 3DE's Toolkit context to *task* (creates its folders first)."""
        import sgtk
        eng = self._engine
        try:
            eng.sgtk.create_filesystem_structure("Task", task["id"], engine=eng.instance_name)
            ctx = eng.sgtk.context_from_entity("Task", task["id"])
            self.close()
            sgtk.platform.change_context(ctx)
        except Exception as exc:
            eng.logger.exception("Switching context failed")
            QtGui.QMessageBox.warning(None, "Switch task", "Could not switch to this task:\n%s" % exc)
            return
        # Reopen the panel on the new engine, now in the task's context.
        new = sgtk.platform.current_engine()
        if new is not None and hasattr(new, "show_menu"):
            QtCore.QTimer.singleShot(100, new.show_menu)

    def _open_overview(self):
        from .overview import ShotOverview
        win = ShotOverview(self._engine, self)
        self._overview = win
        win.show()
        self._engine._center_on_primary(win)
        win.raise_()
        win.activateWindow()

    def _export_to_nuke(self):
        """LD_3DE4-node van de huidige camera, met dezelfde versie als het werkbestand."""
        from . import nuke_export as nx
        try:
            cam = nx.current_camera()
            path = nx.export_path(self._engine, cam["name"])
        except Exception as exc:
            QtGui.QMessageBox.warning(self, "Export to Nuke", str(exc))
            return
        if os.path.exists(path):
            res = QtGui.QMessageBox.question(
                self, "Export to Nuke",
                "This version has already been exported:\n%s\n\nOverwrite?" % os.path.basename(path),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if res != QtGui.QMessageBox.Yes:
                return
        try:
            nx.export_ld_node(cam["cam"], cam["offset"], path)
        except Exception as exc:
            self._engine.logger.exception("LD export failed")
            QtGui.QMessageBox.warning(self, "Export to Nuke", "Export failed:\n%s" % exc)
            return
        self._engine.logger.info("LD node exported: %s", path)
        QtGui.QApplication.clipboard().setText(path.replace("\\", "/"))
        box = QtGui.QMessageBox(self)
        box.setWindowTitle("Export to Nuke")
        box.setText("Exported the LD node of camera '%s' (start frame %d).\n\n%s\n\n"
                    "The path is on your clipboard. In Nuke: File > Insert Comp Nodes."
                    % (cam["name"], cam["offset"], path))
        folder = box.addButton("Open folder", QtGui.QMessageBox.ActionRole)
        box.addButton(QtGui.QMessageBox.Ok)
        box.exec()
        if box.clickedButton() is folder and hasattr(os, "startfile"):
            os.startfile(os.path.dirname(path))

    def _open_help(self):
        """HELP.html in de standaardbrowser (zelfde keuze als de NFA Shot Manager)."""
        # HELP.html sits next to the python folder the tools were loaded from:
        # C:/pipeline/3de/HELP.html, or the engine's own copy for the bundled fallback.
        here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(here, HELP_FILENAME)
        if not os.path.isfile(path):
            path = os.path.join(self._engine.disk_location, HELP_FILENAME)
        if not os.path.isfile(path):
            QtGui.QMessageBox.warning(self, "Help", "Help page not found:\n%s" % path)
            return
        if not QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path)):
            QtGui.QMessageBox.information(self, "Help", "Could not open a browser.\n\nThe help page is here:\n%s" % path)

    def _update_file_label(self):
        path = ""
        try:
            import tde4
            path = tde4.getProjectPath() or ""
        except Exception:
            pass
        if path:
            self._file_lbl.setText("Open: %s" % os.path.basename(path))
            self._file_lbl.setToolTip(path)
        else:
            self._file_lbl.setText("Project not saved yet")


# ====================================================================== plates
class PlateDialog(QtGui.QWidget):
    """Kies een plate van het huidige shot en laad hem als 3DE-camera."""

    def __init__(self, engine, parent=None):
        super().__init__(None, QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        from . import plates as plates_mod
        self._mod = plates_mod
        self._engine = engine
        self._panel = parent
        self.setObjectName("NFA3DEPanel")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setWindowTitle("Load Plate – 3DEqualizer")
        self.setStyleSheet(STYLE + LIST_STYLE)
        self.setMinimumWidth(460)
        self._plates = []
        self._build()
        self._scan()

    def _build(self):
        root = QtGui.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)

        tb = QtGui.QFrame()
        tb.setObjectName("titleBar")
        tbl = QtGui.QVBoxLayout(tb)
        tbl.setContentsMargins(14, 10, 14, 10)
        tbl.setSpacing(1)
        t = QtGui.QLabel("Load Plate")
        t.setStyleSheet("font-size:15px; font-weight:600; color:#f2f2f7;")
        ent = self._engine.context.entity or {}
        s = QtGui.QLabel(("%s · 02_SOURCE" % ent.get("name", "")).upper())
        s.setStyleSheet("font-size:9px; font-weight:600; color:#7fa8cc; letter-spacing:1.2px;")
        tbl.addWidget(t)
        tbl.addWidget(s)
        root.addWidget(tb)

        self._list = QtGui.QListWidget()
        self._list.setMinimumHeight(150)
        self._list.itemDoubleClicked.connect(lambda *_: self._load())
        root.addWidget(self._list)

        form = QtGui.QHBoxLayout()
        form.setSpacing(8)
        self._fps = QtGui.QDoubleSpinBox()
        self._fps.setRange(1, 120)
        self._fps.setDecimals(3)
        self._fps.setValue(self._default_fps())
        self._first = QtGui.QSpinBox()
        self._first.setRange(0, 999999)
        self._first.setValue(1001)
        self._gamma = QtGui.QDoubleSpinBox()
        self._gamma.setRange(0.1, 5.0)
        self._gamma.setSingleStep(0.1)
        self._gamma.setValue(2.2)
        for label, w, tip in (("FPS", self._fps, "Frame rate of the plate"),
                              ("First frame", self._first, "First Frame is Frame (wiki: 1001)"),
                              ("Gamma", self._gamma, "8 Bit Color Conversion gamma (wiki: 2.2 for linear plates)")):
            lbl = QtGui.QLabel(label)
            lbl.setStyleSheet("color:#8e8e93; font-size:11px;")
            w.setToolTip(tip)
            form.addWidget(lbl)
            form.addWidget(w)
        form.addStretch(1)
        root.addLayout(form)

        self._status = QtGui.QLabel("")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        row = QtGui.QHBoxLayout()
        row.setSpacing(6)
        refresh = QtGui.QPushButton("Refresh")
        refresh.setStyleSheet(BTN_REFRESH)
        refresh.clicked.connect(self._scan)
        folder = QtGui.QPushButton("Explorer")
        folder.setStyleSheet(BTN_QUIET)
        folder.clicked.connect(self._reveal)
        self._load_btn = QtGui.QPushButton("Load in 3DE")
        self._load_btn.setStyleSheet(BTN_PRIMARY)
        self._load_btn.clicked.connect(self._load)
        for b in (refresh, folder, self._load_btn):
            b.setCursor(QtCore.Qt.PointingHandCursor)
        row.addWidget(refresh)
        row.addWidget(folder)
        row.addStretch(1)
        row.addWidget(self._load_btn)
        root.addLayout(row)

    # ------------------------------------------------------------ data
    def _default_fps(self):
        """Altijd 25 fps als standaard (schoolnorm); aan te passen in het venster."""
        return 25.0

    def _project_root(self):
        roots = getattr(self._engine.sgtk, "roots", {}) or {}
        return roots.get("primary") or (list(roots.values())[0] if roots else None)

    def _seq_name(self):
        ent = self._engine.context.entity or {}
        try:
            sh = self._engine.shotgun.find_one("Shot", [["id", "is", ent.get("id")]], ["sg_sequence"])
            return ((sh or {}).get("sg_sequence") or {}).get("name")
        except Exception:
            return None

    def _scan(self):
        self._list.clear()
        ent = self._engine.context.entity or {}
        root = self._project_root()
        seq = self._seq_name()
        try:
            self._plates = self._mod.find_plates(root, ent.get("name"), seq)
        except Exception as exc:
            self._plates = []
            self._engine.logger.exception("Plate search failed")
            self._status.setText("Search failed: %s" % exc)
            return
        for p in self._plates:
            und = p.get("undistort")
            und_txt = ("  ·  undistort v%d" % und["version"]) if und and und.get("version") else (
                "  ·  undistort" if und else "")
            text = "%s   %s   %d–%d  (%d frames)%s" % (
                p["plate_id"], p["ext"].upper(), p["first"], p["last"], p["count"], und_txt)
            item = QtGui.QListWidgetItem(text)
            item.setToolTip(p["path"])
            self._list.addItem(item)
        if self._plates:
            self._list.setCurrentRow(0)
            self._status.setText("%d plate(s) found in 02_source." % len(self._plates))
        else:
            self._status.setText("No plates found for %s in %s/02_source (sequence: %s)."
                                 % (ent.get("name"), root, seq or "?"))
        self._load_btn.setEnabled(bool(self._plates))

    def _current(self):
        row = self._list.currentRow()
        return self._plates[row] if 0 <= row < len(self._plates) else None

    def _reveal(self):
        p = self._current()
        path = p["plate_dir"] if p else None
        if path and os.path.isdir(path):
            os.startfile(path) if hasattr(os, "startfile") else None

    def _load(self):
        p = self._current()
        if not p:
            return
        ent = self._engine.context.entity or {}
        name = "%s_%s" % (ent.get("name", ""), p["plate_id"])
        try:
            cam, skipped = self._mod.load_into_3de(
                p, fps=self._fps.value(), first_frame=self._first.value(),
                gamma=self._gamma.value(), name=name,
                log=lambda m: self._engine.logger.info(m))
        except Exception as exc:
            self._engine.logger.exception("Loading the plate failed")
            QtGui.QMessageBox.warning(self, "Load Plate", "Loading failed:\n%s" % exc)
            return
        msg = "Loaded as camera '%s' (%d–%d, first frame %d)." % (
            name, p["first"], p["last"], self._first.value())
        if skipped:
            msg += "\nNot set (function missing in this 3DE): %s" % ", ".join(skipped)
        self._status.setText(msg)
        if not skipped:
            self.close()


LIST_STYLE = """
QListWidget {
    background-color: #222224; color: #e4e4e6; border: none; border-radius: 9px;
    outline: none; padding: 4px; font-size: 11px;
}
QListWidget::item { padding: 7px 8px; border-radius: 6px; }
QListWidget::item:hover { background-color: #2a2a2c; }
QListWidget::item:selected { background-color: #2c3440; color: #ffffff; }
QDoubleSpinBox, QSpinBox {
    background-color: #2a2a2c; color: #e4e4e6; border: none;
    border-radius: 7px; padding: 4px 6px;
}
"""
