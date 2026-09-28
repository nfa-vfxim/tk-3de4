# tk-3de4

ShotGrid Toolkit engine for **3DEqualizer 4 R8** in the NFA VFXIM pipeline.
By Luuk Kamphuis.

## What is where

| Part | Lives in | Updated by |
|---|---|---|
| Engine (launcher, Qt next to 3DE, quit guard, File → ShotGrid, Workfiles hook) | this repo, released on GitHub | a new release + `engine_locations.yml` in the config |
| Tools (panel, Shot Overview, Load Plate, Export to Nuke, thumbnails) | pipeline repo, `C:/pipeline/3de/python/tk_3de4` | a commit to the pipeline repo |
| PySide6 6.5.3 | `%LOCALAPPDATA%\NFA\3de\pyside6\6.5.3` on each computer | installed automatically on first start |

`python/tk_3de4` in this repo is a fallback copy of the tools, used only when
`C:/pipeline/3de/python/tk_3de4` is missing (engine setting `tools_path`).

## Requirements

- 3DEqualizer 4 R8.x (Python 3.11).
- tk-core 0.21.7 or newer. tk-core's PySide6 patcher also imports QtWebEngine,
  so the **full** PySide6 is required, not PySide6-Essentials.
- Internet access (PyPI) on the first start, for the PySide6 install.

## Config

- `env/includes/engine_locations.yml`: `engines.tk-3de4.location` (github_release).
- `env/includes/settings/tk-3de4.yml`, included from `project.yml` and `shot_step.yml`.
- `core/templates/tk-3de4.yml` (work/publish templates, `.3de`).
- `tk-multi-workfiles2.yml`: `settings.tk-multi-workfiles2.3de(.shot_step)`.
- ShotGrid Software entity "3DEqualizer": Engine `tk-3de4`.

See CHANGELOG.md for the history and HELP.html for the artist-facing help.
