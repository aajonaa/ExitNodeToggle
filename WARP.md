# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common commands

### Dependency installation
- Install all platform-specific dependencies (Windows + macOS) into the current environment:
  - `pip install -r requirements.txt`
- For Windows-only development from source (minimal):
  - `pip install pystray pillow`
- For Windows packaging:
  - `pip install pyinstaller`
- For macOS-only development from source (minimal):
  - `pip install rumps`
- For macOS packaging with the provided script (uses a venv and installs what it needs):
  - The script itself runs `pip install rumps py2app` inside `venv/`.

### Run app from source
- **Windows GUI (tkinter + system tray):**
  - `python main.py`
- **macOS menu bar app (rumps):**
  - `python main_macos.py`

Both entrypoints expect a `config.json` with at least:
```json
{
  "tailscale_exe": "path-or-command-for-tailscale",
  "exit_node_ip": "100.64.10.100"
}
```
On macOS, `config.macos.json` can be copied/edited to `config.json` as a starting point.

### Build distributables

#### Windows (PyInstaller)
- Preferred: use the helper script (also installs PyInstaller if missing):
  - `build.bat`
- Equivalent manual build:
  - `pyinstaller --onefile --windowed --name "ExitNodeToggle" --add-data "config.json;." main.py`
- Output EXE: `dist/ExitNodeToggle.exe`
- Ensure a `config.json` sits next to the EXE at runtime.

#### macOS (`.app` and optional DMG)
- Use the build script (creates venv, installs rumps/py2app, builds the `.app`, and optionally a DMG):
  - `chmod +x build_macos.sh`
  - `./build_macos.sh`
- Resulting app bundle: `dist/Exit Node Toggle.app`
- The script ensures a `config.json` is present and copies it into:
  - `dist/Exit Node Toggle.app/Contents/Resources/config.json`
- Optional DMG: the script can build `ExitNodeToggle-1.0.0.dmg` interactively.

Alternative direct py2app invocation (if you want to bypass the shell script):
- `python setup_macos.py py2app`

### Tests and linting
- There are currently **no automated tests** or explicit linting/type-checking tools configured in this repo.
- If you add tests (e.g., `pytest`) or linters/formatters (e.g., `ruff`, `flake8`, `black`), update this section with the canonical commands.

## High-level architecture

### Platform entrypoints
- `main.py` — Windows-only GUI application using **tkinter** for the window and **pystray + Pillow** for the system tray icon.
- `main_macos.py` — macOS-only menu bar application using **rumps**.
- The two entrypoints share the same conceptual responsibilities:
  - Load configuration (`Config` classes) to determine the Tailscale CLI path and target exit node IP.
  - Use a `TailscaleToggle` abstraction to query and update exit-node state via the Tailscale CLI.
  - Provide a lightweight, always-available UI surface (window + tray on Windows, menu bar icon on macOS).

### Shared Tailscale integration
- Both platforms shell out to the **Tailscale CLI** to manage exit nodes:
  - Status: `tailscale status --json` (invoked via `subprocess.run`).
  - Enable exit node: `tailscale set --exit-node=<exit_node_ip>`.
  - Disable exit node: `tailscale set --exit-node=` (empty value clears the exit node).
- The JSON `ExitNodeStatus` field is used to infer whether an exit node is active and to identify the current node.
- Configuration is required for the exit node IP; both `Config` implementations show blocking UI alerts if it is missing or left as the placeholder.

### Windows implementation details (`main.py`)
- Key classes:
  - `Config` — Reads `config.json` from the same directory as `main.py`/the bundled EXE. Provides `tailscale_exe` and `exit_node_ip`. Warns via `tkinter.messagebox` if configuration is incomplete.
  - `StartupManager` — Manages **"Start with Windows"** via the `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` registry key using `winreg`.
    - When running from a bundled EXE (PyInstaller), it points directly to `sys.executable`.
    - When running as a script, it uses `pythonw.exe` and the script path so it can start without a console window.
  - `TailscaleToggle` — Wraps all Tailscale CLI interaction on Windows and uses `subprocess.CREATE_NO_WINDOW` so no console windows flash.
  - `App` — tk-based GUI that wires together configuration, Tailscale operations, and startup behavior.
- System tray integration:
  - Uses `pystray.Icon` running in a **background thread**.
  - Tray menu exposes: toggle exit node, show main window, toggle startup, and exit.
  - Tray icon is a dynamically drawn colored circle via Pillow, with **grey** for OFF and **red** for ON.
  - If `pystray`/Pillow are missing, the app falls back to a normal window close behavior instead of minimizing to tray.
- The main window is a small, fixed-size dark-themed UI with:
  - Status indicator (dot + label),
  - Primary toggle button,
  - Exit-node IP label,
  - "Start with Windows" checkbox kept in sync with `StartupManager` and the tray menu.

### macOS implementation details (`main_macos.py`)
- macOS-specific stack:
  - **rumps** for menu bar integration (the app quits immediately if rumps is not importable).
  - `ExitNodeToggleApp` subclasses `rumps.App` and manages the menu, status updates, start-at-login behavior, and notifications.
- `Config` on macOS is more flexible about where `config.json` lives:
  - It searches, in order, user-level locations like
    - `~/Library/Application Support/ExitNodeToggle/config.json`,
    - `~/.config/exitnodetoggle/config.json`,
    - the app bundle `Resources/config.json` when bundled,
    - or the script directory when running from source.
  - Defaults for `tailscale_exe`:
    - `/Applications/Tailscale.app/Contents/MacOS/Tailscale` if present, otherwise falls back to just `tailscale` (CLI on PATH).
- `StartupManager` for macOS uses **LaunchAgents**:
  - Writes `~/Library/LaunchAgents/com.tailscale.exitnodetoggle.plist` with a `ProgramArguments` entry pointing to the app or script.
  - Uses `launchctl load/unload` to enable/disable "Start at Login" from the menu.
- `TailscaleToggle` on macOS:
  - Centralizes all CLI calls through `_run_tailscale`, which:
    - Crafts a PATH that includes common Tailscale install locations (Homebrew, system, app bundle).
    - Logs commands, exit codes, stdout, and stderr to `~/Library/Logs/ExitNodeToggle/exit_node_toggle.log` via a small `log()` helper.
    - On certain "failed to start" errors, attempts to start the Tailscale GUI once (`open -g -a Tailscale`) and retries.
- Menu bar UX:
  - App icon is an emoji lock: `🔓` when using direct connection, `🔒` when routing via exit node.
  - Menu items include: a read-only status item, a "Toggle Exit Node" action, a read-only node info line, a "Start at Login" toggle, and "Quit".
  - A 30-second `rumps.Timer` refreshes status periodically.

### Packaging and distribution
- **Windows**:
  - `ExitNodeToggle.spec` defines a PyInstaller build using `main.py` and bundling `config.json` as data.
  - `build.bat` is the canonical entrypoint; it checks for PyInstaller, builds a one-file, windowed EXE, and reminds the user to place `config.json` next to the binary.
- **macOS**:
  - `setup_macos.py` is the py2app configuration, using `main_macos.py` as the app entry and including `config.json` as a data file.
  - `build_macos.sh` orchestrates the entire macOS build pipeline:
    - Creates/uses `venv/`.
    - Installs `rumps` and `py2app`.
    - Ensures a `config.json` exists (autogenerating one if necessary) with a sensible `tailscale_exe` based on the detected CLI or app.
    - Runs `python3 setup_macos.py py2app`.
    - Copies and normalizes `config.json` into the app bundle resources and (optionally) builds a DMG with a simple README and Applications symlink.

### Configuration files
- `config.json` (runtime configuration):
  - On Windows: expected to live alongside `main.py` / the EXE.
  - On macOS: may live in several user-level locations or inside the app bundle; `Config` encapsulates the search logic.
- `config.macos.json` (template):
  - macOS-specific example that typically uses a bare `tailscale` CLI as `tailscale_exe`.
- When modifying configuration behavior, prefer updating the respective `Config` classes so both the from-source and bundled flows stay consistent.
