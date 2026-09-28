# Shot overview for 3DE, built on the same system as the NFA Shot Manager (Nuke):
# same folder scan, same thumbnails (<root>/.nfa_shot_manager/thumbnails/<sid>.jpg),
# same row look and badges — plus what matters for matchmove: plate, undistort, track.
import os
import re

from sgtk.platform.qt import QtCore, QtGui

from . import plates as plates_mod
from . import thumbnails as thumbs_mod
from .panel import (STYLE, LIST_STYLE, BTN_PRIMARY, BTN_QUIET, BTN_REFRESH, _pill, TOOL_VERSION,
                    TOOL_AUTHOR, MATCHMOVE_STEPS)

MANAGER_DIR = ".nfa_shot_manager"
THUMB_DIR = "thumbnails"
WORKFILES = "03_workfiles"
THUMB_W, THUMB_H = 136, 77
SHOT_NAME_RE = re.compile(r"^[A-Za-z]*\d+$")
VERSION_RE = re.compile(r"v(\d+)", re.IGNORECASE)

ROW_IDLE = "QFrame#ShotRow { border: 1px solid transparent; border-radius: 8px; }"
ROW_HOVER = "QFrame#ShotRow { border: 1px solid transparent; border-radius: 8px; background-color: #2a2a2c; }"
ROW_SELECTED = "QFrame#ShotRow { border: 1px solid #5a8fc4; border-radius: 8px; background-color: #2c3440; }"


def shot_id(seq, shot):
    """Same id as the Shot Manager: sequence without its letter prefix + '_' + shot."""
    return "%s_%s" % (plates_mod.SEQ_PREFIX_RE.sub("", seq or ""), shot)


def badge_version(v):
    return "v%d" % int(v)


def abbreviate(name):
    parts = (name or "").split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0].upper()
    return ("%s %s." % (parts[0], parts[-1][0])).upper()


# ------------------------------------------------------------------ scan (no Qt, worker thread)
def _scan_track(shot_dir):
    best = None
    for dept, dept_path in plates_mod._listdirs(shot_dir):
        tde = plates_mod._child(dept_path, "3de")
        if not tde:
            continue
        for name in plates_mod._listfiles(tde):
            if not name.lower().endswith(".3de"):
                continue
            m = VERSION_RE.search(name)
            v = int(m.group(1)) if m else 0
            if best is None or v > best["version"]:
                best = {"version": v, "dept": dept, "filename": name, "path": os.path.join(tde, name)}
    return best


def scan_project(root):
    """{sid: {seq, shot, plates:[...], undistort:{...}|None, track:{...}|None, workfiles_dir}}"""
    shots = {}

    def ensure(seq, shot):
        sid = shot_id(seq, shot)
        if sid not in shots:
            shots[sid] = {"sid": sid, "seq": seq, "shot": shot, "plates": [], "undistort": None,
                          "track": None, "workfiles_dir": None}
        return shots[sid]

    src = plates_mod._child(root, plates_mod.SOURCE_DIRNAME)
    for seq, seq_path in plates_mod._listdirs(src) if src else []:
        for shot, shot_path in plates_mod._listdirs(seq_path):
            if not SHOT_NAME_RE.match(shot) or not plates_mod.normalize_seq(seq):
                continue
            sd = ensure(seq, shot)
            for plate_id, plate_dir in plates_mod._listdirs(shot_path):
                leaf = plates_mod._child(plate_dir, plates_mod.PLATES_LEAF)
                if not leaf:
                    continue
                info = plates_mod._scan_leaf(leaf)
                if info:
                    info["plate_id"] = plate_id
                    sd["plates"].append(info)
                und = plates_mod._scan_undistort(plate_dir)
                if und and (sd["undistort"] is None or und.get("version", 0) > sd["undistort"].get("version", 0)):
                    sd["undistort"] = und

    wf = plates_mod._child(root, WORKFILES)
    shots_root = plates_mod._child(wf, "shots") if wf else None
    for seq, seq_path in plates_mod._listdirs(shots_root) if shots_root else []:
        for shot, shot_path in plates_mod._listdirs(seq_path):
            if not SHOT_NAME_RE.match(shot) or not plates_mod.normalize_seq(seq):
                continue
            sd = ensure(seq, shot)
            sd["workfiles_dir"] = shot_path
            sd["track"] = _scan_track(shot_path)
    return shots


class ScanThread(QtCore.QThread):
    done = QtCore.Signal(object, object)

    def __init__(self, root, sg, project, parent=None):
        super().__init__(parent)
        self._root, self._sg, self._project = root, sg, project

    def run(self):
        shots, sg_shots = {}, []
        try:
            shots = scan_project(self._root)
        except Exception:
            pass
        try:
            sg_shots = self._sg.find(
                "Shot", [["project", "is", self._project]], ["code", "sg_sequence", "image"])
            tasks = self._sg.find(
                "Task", [["project", "is", self._project], ["entity", "type_is", "Shot"]],
                ["content", "step", "entity", "task_assignees", "sg_status_list"])
            by_shot = {}
            for t in tasks:
                by_shot.setdefault(t["entity"]["id"], []).append(t)
            for s in sg_shots:
                s["tasks"] = by_shot.get(s["id"], [])
        except Exception:
            pass
        self.done.emit(shots, sg_shots)


# ------------------------------------------------------------------ row widget
class ShotRow(QtGui.QFrame):
    clicked = QtCore.Signal(object)
    activated = QtCore.Signal(object)

    def __init__(self, data, thumb_path, me, parent=None):
        super().__init__(parent)
        self.data = data
        self._selected = False
        self.setObjectName("ShotRow")
        self.setStyleSheet(ROW_IDLE)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        lay = QtGui.QHBoxLayout(self)
        lay.setContentsMargins(6, 5, 8, 5)
        lay.setSpacing(10)

        self._thumb = QtGui.QLabel()
        self._thumb.setFixedSize(THUMB_W, THUMB_H)
        self._thumb.setAlignment(QtCore.Qt.AlignCenter)
        self.set_thumbnail(thumb_path)
        lay.addWidget(self._thumb)

        info = QtGui.QVBoxLayout()
        info.setSpacing(5)
        title = QtGui.QLabel("%s · %s" % (data["seq_label"], data["shot"]))
        title.setStyleSheet("font-size:12px; font-weight:600; color:#e8e8ea;")
        info.addWidget(title)

        badges = QtGui.QHBoxLayout()
        badges.setSpacing(5)
        n = len(data.get("plates") or [])
        if n:
            badges.addWidget(_pill("PLATE" if n == 1 else "%d PLATES" % n, "#26333c", "#8fc2e0"))
        else:
            badges.addWidget(_pill("NO PLATE", "#2a2a2c", "#8e8e93"))
        und = data.get("undistort")
        if und:
            label = "UNDIST %s" % badge_version(und["version"]) if und.get("version") else "UNDIST"
            badges.addWidget(_pill(label, "#24343a", "#93cdd4"))
        track = data.get("track")
        if track:
            p = _pill("TRACK %s" % badge_version(track["version"]) if track["version"] else "TRACK",
                      "#2b3431", "#93d0bb")
            p.setToolTip("%s · %s" % (track["dept"], track["filename"]))
            badges.addWidget(p)
        else:
            badges.addWidget(_pill("NO TRACK", "#2a2a2c", "#8e8e93"))
        mm = data.get("mm_task")
        if mm:
            names = [a.get("name", "") for a in mm.get("task_assignees") or []]
            if names:
                mine = [x for x in names if me and x.strip().lower() == me.strip().lower()]
                label = abbreviate(mine[0]) if mine else abbreviate(names[0]) + (
                    " +%d" % (len(names) - 1) if len(names) > 1 else "")
                p = _pill(label, "#2b2e3a", "#a9b4d8")
                p.setToolTip(", ".join(names) + "  (%s)" % (mm.get("content") or "Matchmove"))
                badges.addWidget(p)
        badges.addStretch(1)
        info.addLayout(badges)
        info.addStretch(1)
        lay.addLayout(info, 1)

    def set_thumbnail(self, path):
        pix = QtGui.QPixmap(path) if path and os.path.isfile(path) else QtGui.QPixmap()
        if pix.isNull():
            self._thumb.setText("no preview")
            self._thumb.setStyleSheet("background:#2a2a2c; border:none; border-radius:6px; "
                                      "color:#5c5c60; font-size:9px;")
        else:
            self._thumb.setPixmap(pix.scaled(THUMB_W, THUMB_H, QtCore.Qt.KeepAspectRatio,
                                             QtCore.Qt.SmoothTransformation))
            self._thumb.setStyleSheet("")

    def set_selected(self, on):
        self._selected = on
        self.setStyleSheet(ROW_SELECTED if on else ROW_IDLE)

    def enterEvent(self, e):
        if not self._selected:
            self.setStyleSheet(ROW_HOVER)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._selected:
            self.setStyleSheet(ROW_IDLE)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self.clicked.emit(self)
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.activated.emit(self)
        super().mouseDoubleClickEvent(e)


# ------------------------------------------------------------------ window
class ShotOverview(QtGui.QWidget):
    """Every shot of the project with thumbnail and matchmove status; open one in one click."""

    def __init__(self, engine, panel=None):
        super().__init__(None, QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self._engine = engine
        self._panel = panel
        self._rows = []
        self._selected = None
        self._thread = None
        self._thumb_proc = None
        self._thumb_buf = ""
        self.setObjectName("NFA3DEPanel")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setWindowTitle("Shot Overview – 3DEqualizer")
        self.setStyleSheet(STYLE + LIST_STYLE + COMBO_STYLE)
        self.resize(520, 640)
        self._build()
        self._refresh()

    def _root(self):
        roots = getattr(self._engine.sgtk, "roots", {}) or {}
        return roots.get("primary") or (list(roots.values())[0] if roots else None)

    def _build(self):
        root = QtGui.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)
        tb = QtGui.QFrame()
        tb.setObjectName("titleBar")
        tbl = QtGui.QVBoxLayout(tb)
        tbl.setContentsMargins(14, 10, 14, 10)
        tbl.setSpacing(1)
        t = QtGui.QLabel("Shot Overview")
        t.setStyleSheet("font-size:15px; font-weight:600; color:#f2f2f7;")
        s = QtGui.QLabel(("%s · MATCHMOVE" % (self._engine.context.project or {}).get("name", "")).upper())
        s.setStyleSheet("font-size:9px; font-weight:600; color:#7fa8cc; letter-spacing:1.2px;")
        tbl.addWidget(t)
        tbl.addWidget(s)
        root.addWidget(tb)

        row = QtGui.QHBoxLayout()
        row.setSpacing(6)
        self._seq_cb = QtGui.QComboBox()
        self._seq_cb.currentIndexChanged.connect(lambda *_: self._populate())
        self._mine = QtGui.QCheckBox("My shots only")
        self._mine.toggled.connect(lambda *_: self._populate())
        self._refresh_btn = QtGui.QPushButton("Refresh")
        self._refresh_btn.setStyleSheet(BTN_REFRESH)
        self._refresh_btn.clicked.connect(self._refresh)
        row.addWidget(self._seq_cb, 1)
        row.addWidget(self._mine)
        row.addWidget(self._refresh_btn)
        root.addLayout(row)

        self._scroll = QtGui.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._list_host = QtGui.QWidget()
        self._list_host.setObjectName("listHost")
        self._list_host.setStyleSheet("QWidget#listHost { background-color: #222224; border-radius: 9px; }")
        self._list_lay = QtGui.QVBoxLayout(self._list_host)
        self._list_lay.setContentsMargins(4, 4, 4, 4)
        self._list_lay.setSpacing(2)
        self._list_lay.addStretch(1)
        self._scroll.setWidget(self._list_host)
        root.addWidget(self._scroll, 1)

        self._status = QtGui.QLabel("")
        self._status.setObjectName("status")
        root.addWidget(self._status)

        actions = QtGui.QHBoxLayout()
        actions.setSpacing(6)
        self._folder_btn = QtGui.QPushButton("Explorer")
        self._folder_btn.setStyleSheet(BTN_QUIET)
        self._folder_btn.clicked.connect(self._reveal)
        self._open_btn = QtGui.QPushButton("Open Shot")
        self._open_btn.setStyleSheet(BTN_PRIMARY)
        self._open_btn.setToolTip("Switch 3DE to this shot's matchmove task and open the newest track")
        self._open_btn.clicked.connect(self._open_selected)
        for b in (self._folder_btn, self._open_btn, self._refresh_btn):
            b.setCursor(QtCore.Qt.PointingHandCursor)
        actions.addWidget(self._folder_btn)
        actions.addStretch(1)
        actions.addWidget(self._open_btn)
        root.addLayout(actions)
        foot = QtGui.QLabel("v%s · %s" % (TOOL_VERSION, TOOL_AUTHOR))
        foot.setStyleSheet("color:#555; font-size:9px;")
        foot.setAlignment(QtCore.Qt.AlignRight)
        root.addWidget(foot)
        self._open_btn.setEnabled(False)

    # ------------------------------------------------------------ data
    def _refresh(self):
        if self._thread is not None:
            return
        self._status.setText("Scanning project…")
        self._refresh_btn.setEnabled(False)
        self._thread = ScanThread(self._root(), self._engine.shotgun, self._engine.context.project, self)
        self._thread.done.connect(self._on_scanned)
        self._thread.start()

    def _on_scanned(self, disk, sg_shots):
        self._thread = None
        self._refresh_btn.setEnabled(True)
        me = self._me()
        merged = {}
        # ShotGrid is the list of shots; the disk scan adds what exists per shot.
        for s in sg_shots:
            seq = (s.get("sg_sequence") or {}).get("name") or ""
            sid = shot_id(seq, s["code"])
            d = dict(disk.get(sid) or {"plates": [], "undistort": None, "track": None, "workfiles_dir": None})
            d.update({"sid": sid, "seq": seq, "shot": s["code"], "sg": s,
                      "seq_label": seq or "—"})
            d["mm_task"] = self._mm_task(s.get("tasks") or [])
            d["mine"] = bool(d["mm_task"] and me and any(
                (a.get("name") or "").lower() == me.lower() for a in d["mm_task"].get("task_assignees") or []))
            merged[sid] = d
        for sid, d in disk.items():   # on disk but not (yet) in ShotGrid
            if sid not in merged:
                d = dict(d)
                d.update({"seq_label": d["seq"], "sg": None, "mm_task": None, "mine": False})
                merged[sid] = d
        self._shots = sorted(merged.values(), key=lambda d: (plates_mod.normalize_seq(d["seq"]), d["shot"]))
        seqs = sorted({d["seq_label"] for d in self._shots})
        current = self._seq_cb.currentText()
        self._seq_cb.blockSignals(True)
        self._seq_cb.clear()
        self._seq_cb.addItem("All sequences")
        self._seq_cb.addItems(seqs)
        idx = self._seq_cb.findText(current)
        self._seq_cb.setCurrentIndex(idx if idx >= 0 else 0)
        self._seq_cb.blockSignals(False)
        self._populate()
        self._render_missing_thumbnails()

    # ------------------------------------------------------------ thumbnails
    def _thumb_dir(self):
        return os.path.join(self._root() or "", MANAGER_DIR, THUMB_DIR)

    def _render_missing_thumbnails(self):
        """Shots without a Shot Manager thumbnail get one, rendered in a background Nuke."""
        if self._thumb_proc is not None:
            return
        tdir = self._thumb_dir()
        missing = [d["sid"] for d in getattr(self, "_shots", [])
                   if (d.get("plates") or d.get("workfiles_dir"))
                   and not os.path.isfile(os.path.join(tdir, "%s.jpg" % d["sid"]))]
        if not missing:
            return
        nuke = thumbs_mod.find_nuke()
        if not nuke:
            self._set_thumb_status("Nuke not found; %d shot(s) stay without a thumbnail." % len(missing))
            return
        cmd = thumbs_mod.command(nuke, self._root(), missing)
        proc = QtCore.QProcess(self)
        env = QtCore.QProcessEnvironment()
        for k, v in thumbs_mod.nuke_environment().items():
            env.insert(k, v)
        proc.setProcessEnvironment(env)
        proc.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_thumb_output)
        proc.finished.connect(self._on_thumb_finished)
        self._thumb_total = len(missing)
        self._thumb_done = 0
        self._thumb_proc = proc
        self._thumb_buf = ""
        self._set_thumb_status("Rendering %d thumbnail(s) in Nuke…" % len(missing))
        self._engine.logger.info("Thumbnails: %s", " ".join(cmd))
        proc.start(cmd[0], cmd[1:])
        self._thumb_popup = ThumbnailProgress(len(missing), self)
        self._thumb_popup.cancelled.connect(self._cancel_thumbnails)
        self._thumb_popup.show()
        self._engine._center_on_primary(self._thumb_popup)
        self._thumb_popup.raise_()

    def _set_thumb_status(self, text):
        self._thumb_status = text
        self._show_status()

    def _show_status(self):
        parts = [p for p in (getattr(self, "_base_status", ""), getattr(self, "_thumb_status", "")) if p]
        self._status.setText("  ·  ".join(parts))

    def _on_thumb_output(self):
        self._thumb_buf += bytes(self._thumb_proc.readAllStandardOutput()).decode("utf-8", "replace")
        lines = self._thumb_buf.split("\n")
        self._thumb_buf = lines.pop()
        tdir = self._thumb_dir()
        for line in lines:
            m = thumbs_mod.LINE_RE.match(line.strip())
            if not m:
                continue
            sid, state = m.group(1), m.group(2)
            self._thumb_done += 1
            if state == "ok":
                for row in self._rows:
                    if row.data["sid"] == sid:
                        row.set_thumbnail(os.path.join(tdir, "%s.jpg" % sid))
            elif state == "fail":
                self._engine.logger.warning("Thumbnail %s failed: %s", sid, m.group(3))
            self._set_thumb_status("Rendering thumbnails %d/%d…" % (self._thumb_done, self._thumb_total))
            if getattr(self, "_thumb_popup", None) is not None:
                self._thumb_popup.set_progress(self._thumb_done, sid)

    def _cancel_thumbnails(self):
        """Stop the background Nuke; the overview carries on without the missing thumbnails."""
        self._thumb_cancelled = True
        if self._thumb_proc is not None:
            self._thumb_proc.kill()

    def _close_thumb_popup(self):
        popup = getattr(self, "_thumb_popup", None)
        self._thumb_popup = None
        if popup is not None:
            popup.done = True
            popup.close()
            popup.deleteLater()

    def _on_thumb_finished(self, code, *_):
        self._thumb_proc = None
        self._close_thumb_popup()
        if getattr(self, "_thumb_cancelled", False):
            self._thumb_cancelled = False
            self._set_thumb_status("Thumbnails cancelled (%d/%d done)" % (self._thumb_done, self._thumb_total))
            return
        if code == 0:
            self._set_thumb_status("Thumbnails up to date")
        else:
            self._set_thumb_status("Thumbnail render stopped (Nuke exit code %s)" % code)

    def closeEvent(self, event):
        # A half-written thumbnail is impossible (the Shot Manager writes via a temp file),
        # so closing simply stops the background Nuke.
        if self._thumb_proc is not None:
            self._thumb_cancelled = True
            self._thumb_proc.kill()
        self._close_thumb_popup()
        super().closeEvent(event)

    def _me(self):
        user = self._engine.context.user
        if not user:
            try:
                import sgtk
                user = sgtk.util.get_current_user(self._engine.sgtk)
            except Exception:
                user = None
        return (user or {}).get("name")

    @staticmethod
    def _mm_task(tasks):
        for t in tasks:
            step = ((t.get("step") or {}).get("name") or "").lower()
            if step in MATCHMOVE_STEPS or (t.get("content") or "").lower() in MATCHMOVE_STEPS:
                return t
        return None

    def _populate(self):
        while self._list_lay.count() > 1:
            w = self._list_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        self._rows = []
        self._select(None)
        seq = self._seq_cb.currentText()
        tdir = os.path.join(self._root() or "", MANAGER_DIR, THUMB_DIR)
        me = self._me()
        shown = 0
        for d in getattr(self, "_shots", []):
            if seq and seq != "All sequences" and d["seq_label"] != seq:
                continue
            if self._mine.isChecked() and not d["mine"]:
                continue
            row = ShotRow(d, os.path.join(tdir, "%s.jpg" % d["sid"]), me)
            row.clicked.connect(self._select)
            row.activated.connect(lambda r: (self._select(r), self._open_selected()))
            self._list_lay.insertWidget(self._list_lay.count() - 1, row)
            self._rows.append(row)
            shown += 1
            ctx_ent = self._engine.context.entity or {}
            if d.get("sg") and ctx_ent.get("id") == d["sg"]["id"]:
                self._select(row)
        tracked = sum(1 for d in getattr(self, "_shots", []) if d.get("track"))
        self._base_status = "%d shots shown · %d tracked" % (shown, tracked)
        self._show_status()

    def _select(self, row):
        if self._selected is not None and self._selected in self._rows:
            self._selected.set_selected(False)
        self._selected = row
        if row is not None:
            row.set_selected(True)
        self._open_btn.setEnabled(bool(row and row.data.get("mm_task")))
        if row is not None and not row.data.get("mm_task"):
            self._status.setText("%s has no Matchmove task in ShotGrid." % row.data["shot"])

    # ------------------------------------------------------------ actions
    def _reveal(self):
        d = self._selected.data if self._selected else None
        path = (d or {}).get("workfiles_dir") or self._root()
        if path and os.path.isdir(path) and hasattr(os, "startfile"):
            os.startfile(path)

    def _open_selected(self):
        """Switch to the shot's matchmove task, then open the newest .3de if there is one."""
        import sgtk
        d = self._selected.data if self._selected else None
        if not d or not d.get("mm_task"):
            return
        eng = self._engine
        track = d.get("track")
        if track:
            try:
                import tde4
                if not tde4.isProjectUpToDate():
                    res = QtGui.QMessageBox.question(
                        self, "Open Shot", "The current 3DE project has unsaved changes.\\nOpen anyway?",
                        QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                    if res != QtGui.QMessageBox.Yes:
                        return
            except Exception:
                pass
        try:
            task_id = d["mm_task"]["id"]
            eng.sgtk.create_filesystem_structure("Task", task_id, engine=eng.instance_name)
            ctx = eng.sgtk.context_from_entity("Task", task_id)
            self.close()
            if self._panel is not None:
                self._panel.close()
            sgtk.platform.change_context(ctx)
        except Exception as exc:
            eng.logger.exception("Open Shot failed")
            QtGui.QMessageBox.warning(None, "Open Shot", "Could not switch to this shot:\\n%s" % exc)
            return
        if track:
            try:
                import tde4
                tde4.loadProject(track["path"])
            except Exception as exc:
                QtGui.QMessageBox.warning(None, "Open Shot", "Could not open %s:\\n%s" % (track["filename"], exc))
        new = sgtk.platform.current_engine()
        if new is not None and hasattr(new, "show_menu"):
            QtCore.QTimer.singleShot(100, new.show_menu)


class ThumbnailProgress(QtGui.QWidget):
    """Small popup while Nuke renders thumbnails: explains the wait, shows progress,
    and lets you carry on without thumbnails."""

    cancelled = QtCore.Signal()

    def __init__(self, total, parent=None):
        super().__init__(None, QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self._total = total
        self.setObjectName("NFA3DEPanel")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setWindowTitle("Rendering thumbnails")
        self.setStyleSheet(STYLE + PROGRESS_STYLE)
        self.setFixedWidth(380)
        root = QtGui.QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(9)
        title = QtGui.QLabel("Rendering thumbnails")
        title.setStyleSheet("font-size:14px; font-weight:600; color:#f2f2f7;")
        root.addWidget(title)
        text = QtGui.QLabel(
            "%d shot(s) have no thumbnail yet. A Nuke is rendering them in the background, "
            "the same way the NFA Shot Manager does.\n\n"
            "This can take a while: starting Nuke alone takes 10–20 seconds. "
            "You can keep working in 3DE meanwhile." % total)
        text.setWordWrap(True)
        text.setStyleSheet("color:#c7c7cc; font-size:11px;")
        root.addWidget(text)
        self._bar = QtGui.QProgressBar()
        self._bar.setRange(0, 0)          # busy until the first thumbnail arrives
        root.addWidget(self._bar)
        self._detail = QtGui.QLabel("Starting Nuke…")
        self._detail.setObjectName("status")
        root.addWidget(self._detail)
        row = QtGui.QHBoxLayout()
        row.addStretch(1)
        btn = QtGui.QPushButton("Continue without thumbnails")
        btn.setStyleSheet(BTN_QUIET)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setToolTip("Stop Nuke; shots without a thumbnail show 'no preview'")
        btn.clicked.connect(self._cancel)
        row.addWidget(btn)
        root.addLayout(row)

    def set_progress(self, done, sid):
        self._bar.setRange(0, self._total)
        self._bar.setValue(done)
        self._detail.setText("%d / %d · %s" % (done, self._total, sid))

    def _cancel(self):
        self._detail.setText("Stopping Nuke…")
        self.cancelled.emit()

    def closeEvent(self, event):
        # Closing the popup with the window's X means the same as the button.
        if self.isVisible() and not getattr(self, "done", False):
            self.cancelled.emit()
        super().closeEvent(event)


PROGRESS_STYLE = """
QProgressBar {
    background-color: #2a2a2c; border: none; border-radius: 6px; height: 14px;
    color: #9c9ca3; font-size: 9px; text-align: center;
}
QProgressBar::chunk { background-color: #39704f; border-radius: 6px; }
"""


COMBO_STYLE = """
QComboBox {
    background-color: #2a2a2c; color: #e4e4e6; border: none;
    border-radius: 7px; padding: 6px 10px; font-size: 12px; min-height: 20px;
}
QComboBox:hover { background-color: #313135; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background-color: #2a2a2c; color: #e4e4e6; border: 1px solid #3a3a3d;
    border-radius: 8px; selection-background-color: #3f4b5c; outline: none; padding: 4px;
}
QCheckBox { spacing: 7px; color: #8e8e93; font-size: 11px; }
QCheckBox::indicator { width: 13px; height: 13px; border-radius: 4px;
    border: 1px solid #48484a; background-color: #2a2a2c; }
QCheckBox::indicator:checked { background-color: #5a8fc4; border-color: #5a8fc4; }
"""
