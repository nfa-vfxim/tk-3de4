# tk-3de4 — Changelog

ShotGrid Toolkit-engine voor 3DEqualizer 4 (R8.1) in de NFA VFXIM-pipeline.

## Versioning

Uses three-decimal versioning: `MAJOR.MINOR.PATCH`, same rules as the NFA Shot Manager:

- **PATCH** — a bug fix that doesn't change how the tool is used.
- **MINOR** — a new feature or visible behavior change that stays backward compatible.
- **MAJOR** — a breaking or structural change (config, folder layout, or a rebuild).

## v1.0.1 — First-start install no longer freezes 3DE

By Luuk Kamphuis.

- **Fix: 3DE froze during the first-start PySide6 install**, and the
  File → ShotGrid entry was missing afterwards until 3DE was restarted.
  v1.0.0 started pip from inside 3DE's startup script and showed requesters
  while 3DE was still starting up.
- The install now starts in **ShotGrid Desktop's launcher**, before 3DE
  opens, as a separate detached process (`nfa_3de_bootstrap.py --install`
  in 3DE's own python.exe). 3DE opens straight away and is usable.
- 3DE's startup script no longer blocks or shows anything. A light timer
  checks every 3 seconds whether the install is done and then starts the
  engine; File → ShotGrid... works from that moment, no restart needed.
- Clicking File → ShotGrid... while the install is still running says so.
  If the install failed, it says where the log is.
- If the launcher could not start the install, the startup script starts it
  itself (same detached process).

## v1.0.0 — Ready for the pipeline

By Luuk Kamphuis.

- **Split into a thin engine and pipeline tools.** The engine
  (`nfa-vfxim/tk-3de4`, released on GitHub) keeps what rarely changes: the
  launcher, Qt next to 3DE, the quit guard, File → ShotGrid and the
  Workfiles hook. The tools (panel, Shot Overview, Load Plate, Export to
  Nuke, thumbnails) are loaded from the pipeline repo,
  `C:/pipeline/3de/python/tk_3de4` (engine setting `tools_path`). Tool
  updates are a commit to the pipeline repo; no engine release and no config
  change. A copy of the tools is bundled with the engine as a fallback.
- **PySide6 installs itself.** On the first start on a computer, 3DE shows a
  short message and installs PySide6 6.5.3 (about 500 MB) in the background
  into `%LOCALAPPDATA%\NFA\3de\pyside6\6.5.3`, with 3DE's own Python and
  pip. It goes to a `.partial` folder first and is only renamed into place
  when pip succeeded, so a failed or interrupted install never looks
  complete. A lock file stops two 3DEs on one computer from installing at the
  same time. When it is done the engine starts by itself. Log:
  `%LOCALAPPDATA%\NFA\3de\pyside6\install_6.5.3.log`.
- Local disk rather than a network share: Qt loads hundreds of DLLs at every
  start.
- No manual `setx` or environment variables needed any more.
- HELP.html is found next to wherever the tools were loaded from.

## v0.8.1 — Thumbnail popup

By Luuk Kamphuis.

- While Nuke renders missing thumbnails, a small popup explains that this
  can take a while (Nuke alone needs 10–20 seconds to start), shows a
  progress bar and the shot being rendered, and has a **Continue without
  thumbnails** button. That stops the background Nuke; thumbnails that were
  already finished are kept, the rest show "no preview". Closing the popup
  does the same.
- The popup closes by itself when all thumbnails are done.

## v0.8.0 — 3DE renders missing thumbnails

By Luuk Kamphuis.

- Shots that the NFA Shot Manager has not made a thumbnail for yet get one
  from the Shot Overview itself. 3DE cannot read the EXR/ACES plates, so it
  starts a background **Nuke -t** that imports `nfa_shot_manager` and calls
  the Shot Manager's own functions (`thumbnail_source_for`,
  `thumbnail_needs_regen`, `_render_single_thumbnail`,
  `_record_thumbnail_version`). Same source choice, same colorspace, same
  file and `.ver` sidecar — Nuke will not render them again.
- Runs after every scan, only for shots without a `.jpg`. Rows update one by
  one as thumbnails arrive; the status line shows the progress. 3DE stays
  usable meanwhile; closing the overview stops the background Nuke.
- Nuke is the newest `C:\Program Files\Nuke*\Nuke*.exe`, started with a
  clean environment and `C:\pipeline\nuke` on `NUKE_PATH`.

## v0.7.0 — Shot Overview

By Luuk Kamphuis.

- **Shot Overview** button in the NFA ShotGrid panel: every shot of the
  project in one list with a thumbnail, on the same system as the NFA Shot
  Manager in Nuke.
  - Thumbnails are the Shot Manager's own
    (`<project>/.nfa_shot_manager/thumbnails/<sid>.jpg`), so nothing is
    rendered twice and both tools show the same picture.
  - Same row look (hover, blue selection border) and badge style.
- Badges per shot: **PLATE** / **2 PLATES** / NO PLATE, **UNDIST v2**,
  **TRACK v3** / NO TRACK, and who is on the Matchmove task (your own name
  alone when you are one of them, otherwise NAME +N).
- Sequence filter and **My shots only**.
- **Open Shot** (or double-click): switches 3DE to the shot's Matchmove task,
  creates its folders and opens the newest `.3de` if there is one (asks
  first when the open project has unsaved changes).
- The scan runs in the background; ShotGrid is the list of shots, the disk
  adds plates, undistorted plates and tracks. Shots that exist only on disk
  are listed too.

## v0.6.0 — My Tasks in the panel

By Luuk Kamphuis.

- When 3DE was started without a task (project context, "NO TASK"), the
  panel lists **your own tasks** in this project, with Matchmove/Tracking
  tasks first and highlighted. Click one to switch 3DE to that task: its
  folders are created, the Toolkit context changes, and the panel reopens
  with the shot, step and task filled in — no need to go through File Open.
- Omitted and Approved tasks are left out, the same as My Tasks in File Open.

## v0.5.1 — English, quit guard, fixes

By Luuk Kamphuis.

- **Everything in English**: buttons, dialogs, messages, logs and the help page.
- **Quit confirmation**: Exit asks "Are you sure you want to quit
  3DEqualizer?" (and warns about unsaved changes), because Exit sits right
  below File in 3DE's menu. Uses `tde4.setQuit3DECallbackFunction` and 3DE's
  own requester; Cancel keeps 3DE open (confirmed).
- **Fix: the ShotGrid window did not open** since v0.3.0. tk-core 0.21.7's
  `import_module` loads `python/` itself as a package and failed; the engine
  now imports `python/tk_3de4` directly.
- **My Tasks** in File Open now also lists tasks that are Waiting, Ready or
  On Hold; only Omitted and Approved are hidden (3DE only, other apps
  unchanged).
- The old PySide test menu (File → NFA) is disabled.

## v0.5.0 — Export to Nuke

By Luuk Kamphuis.

- **Export to Nuke** in the NFA ShotGrid panel: exports the LD_3DE4 lens
  distortion node of the current camera, after undistorting in 3DE, without
  going through File → Export and a file browser.
- Uses 3DE's own exporter (`export_nuke_LD_3DE4_Lens_Distortion_Node.py`,
  FOV mode "relative to Display Window"), so the node is identical to the
  manual export from the Matchmove wiki. Startframe = the camera's
  "First Frame is Frame" (1001).
- Saved to the shot's publish folder, named after the open work file so the
  LD node and the track share a version:
  `04_publish/shots/<seq>/<shot>/<Step>/nuke/<proj>_sc<seq>_<shot>_<Step>_LD_<name>_<camera>_v###.nk`.
- Asks before overwriting an existing export, puts the path on the
  clipboard, and offers to open the folder.
- Only available from a shot task, and only after the 3DE project has been
  saved (File Save).

## v0.4.1 — 25 fps default

By Luuk Kamphuis.

- Load Plate now always starts at **25 fps** (school standard) instead of
  reading a frame rate from ShotGrid. It can still be changed in the dialog.

## v0.4.0 — Load Plate

By Luuk Kamphuis.

- **Load Plate** in the NFA ShotGrid panel (only in a shot context). Finds
  the shot's plates on disk, the same way the NFA Shot Manager does:
  `02_source/<seq>/<shot>/<plate_id>/plates/[<format>/]`. The sequence
  folder is matched with or without its `sc` prefix.
- Loads the chosen plate as a 3DE sequence camera with the settings from
  the Matchmove wiki: **First Frame is Frame 1001**, the plate's FPS and **gamma 2.2**. All three
  can be changed in the dialog before loading.
- Reuses the empty default camera (`seq#1`) instead of adding a second one.
- Shows whether an undistorted version already exists, from the new agreed
  location: `02_source/<seq>/<shot>/<plate_id>/undistort/v###/`.
- A 3DE function that is missing is skipped and named in the dialog,
  instead of stopping the load. The engine now writes the available tde4
  camera functions to the debug log.

## v0.3.0 — Shot Manager-look, help en changelog

By Luuk Kamphuis.

- The ShotGrid panel (**File → ShotGrid...**) now uses the NFA Shot Manager's
  colours and button rules: one filled green button for the main action
  (File Open), a tinted one for anything that writes a file (File Save), grey
  for the rest, blue for navigation.
- Context card with the shot or project, pills for step and task, and the
  `.3de` file that is open right now.
- No more duplicate buttons: favourites only appear at the top.
- **?** button in the title bar opens `HELP.html` in the browser.
- Version and author in the footer, like the Shot Manager.
- Panel code moved to `python/tk_3de4/panel.py`.

## v0.2.0 — Workfiles

By Luuk Kamphuis.

- `tk-multi-workfiles2` in the project and shot_step environments.
- Scene-operation hook for 3DE: open, save, save as and new project
  (asks to save unsaved changes first).
- Templates `tde4_shot_work` / `tde4_shot_publish` (and asset variants) in
  `core/templates/tk-3de4.yml`:
  `03_workfiles/shots/<seq>/<shot>/<step>/3de/<proj>_sc<seq>_<shot>_<step>_work_<name>_v###.3de`.
- All Toolkit windows open centred on the primary screen and stay above 3DE.

## v0.1.0 — First working engine

By Luuk Kamphuis.

- Launch from ShotGrid Desktop: the launcher sets `PYTHON_CUSTOM_SCRIPTS_3DE4`,
  the Toolkit context and the PySide6 path, and 3DE starts the engine on
  startup (`3DE4.script.startup`).
- 3DE has no Qt of its own. PySide6 is loaded from outside and Qt events are
  pumped through `tde4.setTimerCallbackFunction` (every 20 ms), so Toolkit
  windows work next to 3DE without freezing it.
- **File → ShotGrid...** opens the ShotGrid panel; if the engine did not start
  at launch, the menu starts it.
- Needs the **full** PySide6 (6.5.3, incl. Addons): tk-core v0.21.7 also loads
  QtWebEngine and silently reports "no Qt" with PySide6-Essentials only.
- Debug log: `%TEMP%\tk-3de4_debug.log`.
