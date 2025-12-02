# Tailscale Exit Node Toggle

A simple cross-platform GUI application to quickly toggle your Tailscale exit node on and off.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey)

## Features

- 🔒 One-click toggle for Tailscale exit node
- 🎨 Modern dark UI (Windows/Linux) / Native menu bar (macOS)
- 📊 Real-time connection status
- 🖥️ System tray support
  - **Windows/Linux:** Left-click to toggle, Right-click for menu
  - **macOS:** Native menu bar integration
- 🚀 Start with system option
- ⚡ Lightweight - minimal dependencies

---

## Linux (Arch/KDE/GNOME)

### Prerequisites

- [Tailscale](https://tailscale.com/download/linux) installed (`sudo pacman -S tailscale`)
- Python 3.10 or higher
- **PyQt5** (Recommended for KDE/System Tray support)
  - Arch: `sudo pacman -S python-pyqt5`
  - Ubuntu/Debian: `sudo apt install python3-pyqt5`

### Quick Start

#### Option 1: Run from Source

1. **Clone and Setup**
   ```bash
   git clone https://github.com/yourusername/ExitNodeToggle.git
   cd ExitNodeToggle
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure**
   Create `config.json` (or copy `config.linux.json`) and set your specific exit node IP.
   For `tailscale_exe`, use `"tailscale"` if it's in your system's PATH, or its full path like `"/usr/bin/tailscale"`.
   ```json
   {
       "tailscale_exe": "/usr/bin/tailscale", 
       "exit_node_ip": "100.64.10.100"
   }
   ```

3. **Run**
   ```bash
   python main_linux.py
   ```

#### Option 2: Build Standalone Binary

1. **Run Build Script**
   ```bash
   ./build_linux.sh
   ```

2. **Install**
   The executable will be in `dist/ExitNodeToggle`. You can move this anywhere, but ensure `config.json` is in the same directory (or `~/.config/exitnodetoggle/config.json`).

### Linux Usage

- **Main Window:** Control panel with status indicator.
- **System Tray:**
  - **Left Click:** Immediately toggles Exit Node ON/OFF.
  - **Right Click:** Opens menu (Show Window, Toggle, Quit).

#### Dynamic Tray Icons

The system tray icons (On/Off) are dynamically generated at runtime using the `Pillow` library to ensure consistent styling and avoid external asset dependencies. These generated icons are stored temporarily in the application's log directory (`~/.local/state/exitnodetoggle/`).

#### Tray Icon Colors
| Color | Status |
|-------|--------|
| ⚫ Grey | Exit node OFF (direct connection) |
| 🔴 Red | Exit node ON (routing via exit node) |

---

## Windows

### Prerequisites

- [Tailscale](https://tailscale.com/download) installed on Windows
- Python 3.10 or higher (for running from source)
- An exit node configured in your Tailscale network

### Quick Start

#### Option 1: Run from Source

1. **Install dependencies**
   ```bash
   pip install pystray pillow
   ```

2. **Configure your exit node**
   
   Edit `config.json`:
   ```json
   {
       "tailscale_exe": "C:\\Program Files\\Tailscale\\tailscale.exe",
       "exit_node_ip": "100.64.10.100"
   }
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

#### Option 2: Build Standalone EXE

1. **Install dependencies**
   ```bash
   pip install pystray pillow pyinstaller
   ```

2. **Build the EXE**
   ```bash
   build.bat
   ```
   Or manually:
   ```bash
   pyinstaller --onefile --windowed --name "ExitNodeToggle" main.py
   ```

3. **Copy `config.json`** to the same folder as `ExitNodeToggle.exe`

4. **Run `ExitNodeToggle.exe`**

### Windows Usage

#### Main Window
- Click the button to toggle exit node ON/OFF
- Check "Start with Windows" to auto-launch on boot
- Click X to minimize to system tray

#### System Tray
| Action | Result |
|--------|--------|
| **Left-click** | Toggle exit node ON/OFF |
| **Right-click** | Show menu |

#### Tray Icon Colors
| Color | Status |
|-------|--------|
| ⚫ Grey | Exit node OFF (direct connection) |
| 🔴 Red | Exit node ON (routing via exit node) |

---

## macOS

### Prerequisites

- [Tailscale](https://tailscale.com/download) installed on macOS
- Python 3.10 or higher (for running from source)
- An exit node configured in your Tailscale network

### Quick Start

#### Option 1: Run from Source

1. **Install dependencies**
   ```bash
   pip install rumps
   ```

2. **Configure your exit node**
   
   Copy and edit `config.macos.json` to `config.json` (the CLI path `tailscale` usually works best on macOS):
   ```json
   {
       "tailscale_exe": "tailscale",
       "exit_node_ip": "100.64.10.100"
   }
   ```

3. **Run the application**
   ```bash
   python main_macos.py
   ```

#### Option 2: Build Standalone App & DMG

1. **Run the build script**
   ```bash
   chmod +x build_macos.sh
   ./build_macos.sh
   ```

   This will:
   - Create a virtual environment
   - Install dependencies (rumps, py2app)
   - Build `Exit Node Toggle.app`
   - Optionally create a DMG installer
   - Bake in the working Tailscale CLI path (prefers `tailscale` on PATH) and default exit node IP

2. **The app will be in** `dist/Exit Node Toggle.app`

3. **Configuration inside the app bundle**  
   - Tailscale binary: auto-detected during build (CLI preferred).  
   - Exit node IP: defaults to `100.64.10.100` (override by setting `EXIT_NODE_IP` before running the build script).  
   - File: `dist/Exit Node Toggle.app/Contents/Resources/config.json`

### macOS Usage

The app sits in your **menu bar** (top right of screen).

#### Menu Bar Icon
| Icon | Status |
|------|--------|
| 🔓 | Exit node OFF (direct connection) |
| 🔒 | Exit node ON (routing via exit node) |

#### Menu Options
- **Status** - Shows current connection state
- **Toggle Exit Node** - Switch on/off
- **Node: xxx.xxx.xxx.xxx** - Shows configured exit node
- **Start at Login** - Enable/disable auto-start
- **Quit** - Exit the application

### DMG Installation

1. Open the DMG file
2. Drag `Exit Node Toggle.app` to Applications
3. Open from Applications
4. Configure your exit node:
   - Right-click the app → Show Package Contents
   - Navigate to `Contents/Resources/config.json`
   - Edit with your exit node IP

---

## Finding Your Exit Node IP

```bash
tailscale status
```

Look for the device you want to use as exit node and copy its IP (starts with `100.`).

---

## Troubleshooting

For any issues, please check the application logs located at `~/.local/state/exitnodetoggle/app.log` (on Linux/macOS) or `%LOCALAPPDATA%\exitnodetoggle\app.log` (on Windows). These logs provide detailed information that can help diagnose problems.

### Linux (Arch/KDE)

**"Tray icon not responding"**
- Ensure you have `PyQt5` installed. The app uses native Qt system tray integration for best results on KDE.
- If using GNOME, ensure you have AppIndicator support enabled (though Qt fallback usually works).

**"Tray icon not showing after packaging (makepkg)"**
- **Problem:** The packaged application might not display the system tray icon, even though `main_linux.py` works when run directly. This was due to a mismatch in the tray capability check (`main_linux.py` was checking for `gi` (AppIndicator/GTK) while the tray implementation uses `PyQt5`) and PyInstaller not always correctly detecting and bundling `PyQt5` when dynamically imported.
- **Solution:** Ensure your `PKGBUILD` and `build_linux.sh` explicitly include `PyQt5` using `--hidden-import PyQt5` in the PyInstaller command. The application logic has been updated to check for `PyQt5` directly.

**"Cannot enable exit node after packaging (makepkg)"**
- **Problem:** After building with `makepkg`, the application could disable the exit node but failed to enable it. This happened because the `exit_node_ip` was missing from the configuration. The `PKGBUILD` was not bundling `config.json` into the executable, leading the app to start with an invalid configuration.
- **Solution:** Ensure your `PKGBUILD` explicitly bundles `config.json` using `--add-data "config.json:."` in the PyInstaller command. The application will now find the `exit_node_ip` from the bundled `config.json`.
- **Note:** For persistent configuration, it is recommended to create a `config.json` file in `~/.config/exitnodetoggle/` with your desired `exit_node_ip`. This user-specific file will take precedence over the bundled configuration.

**"Permission Denied"**
- Ensure your user can run `tailscale` commands (add user to `tailscale` group if applicable, or use `sudo` via `tailscale_exe` wrapper if strictly required, though typically `tailscale set` works for users in the operator group).

### Windows

**"Tailscale not found"**
- Verify Tailscale is installed
- Check the path in `config.json` matches your installation

**"Operation failed"**
- Ensure Tailscale is running and logged in
- Check that your exit node is online

**EXE doesn't start**
- Make sure `config.json` is in the same folder as the EXE

### macOS

**"Tailscale not found"**
- Verify Tailscale is installed in Applications
- Try setting `tailscale_exe` to just `"tailscale"` if you have the CLI version

**App doesn't appear in menu bar**
- Check for notification requesting permissions
- Go to System Settings → Privacy & Security → Accessibility and allow the app

**DMG build fails**
- Ensure you have Xcode Command Line Tools: `xcode-select --install`

---

## Project Structure

```
ExitNodeToggle/
├── main.py              # Windows version (tkinter + pystray)
├── main_macos.py        # macOS version (rumps menu bar)
├── main_linux.py        # Linux version (tkinter + PyQt5 Tray)
├── config.json          # Your configuration
├── config.macos.json    # macOS config template
├── config.linux.json    # Linux config template
├── requirements.txt     # Python dependencies
├── build.bat            # Windows build script
├── build_macos.sh       # macOS build script
├── build_linux.sh       # Linux build script
├── setup_macos.py       # py2app configuration
└── README.md            # This file
```

---

## License

MIT License - feel free to modify and distribute.
