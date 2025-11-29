# Tailscale Exit Node Toggle

A simple cross-platform GUI application to quickly toggle your Tailscale exit node on and off.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS-lightgrey)

## Features

- 🔒 One-click toggle for Tailscale exit node
- 🎨 Modern dark UI (Windows) / Native menu bar (macOS)
- 📊 Real-time connection status
- 🖥️ System tray (Windows) / Menu bar (macOS) support
- 🚀 Start with system option
- ⚡ Lightweight - minimal dependencies

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
   
   Copy and edit `config.macos.json` to `config.json`:
   ```json
   {
       "tailscale_exe": "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
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

2. **The app will be in** `dist/Exit Node Toggle.app`

3. **Configure your exit node IP** in:
   ```
   dist/Exit Node Toggle.app/Contents/Resources/config.json
   ```

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
├── config.json          # Your configuration
├── config.macos.json    # macOS config template
├── requirements.txt     # Python dependencies
├── build.bat            # Windows build script
├── build_macos.sh       # macOS build script
├── setup_macos.py       # py2app configuration
└── README.md            # This file
```

---

## License

MIT License - feel free to modify and distribute.
