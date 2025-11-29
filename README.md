# Tailscale Exit Node Toggle

A simple Windows GUI application to quickly toggle your Tailscale exit node on and off.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

## Features

- 🔒 One-click toggle for Tailscale exit node
- 🎨 Modern dark UI
- 📊 Real-time connection status
- 🖥️ System tray support - minimize to tray on close
- 🚀 Start with Windows option
- ⚡ Lightweight - minimal dependencies

## Prerequisites

- [Tailscale](https://tailscale.com/download) installed on Windows
- Python 3.10 or higher (for running from source)
- An exit node configured in your Tailscale network

## Quick Start

### Option 1: Run from Source

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

### Option 2: Build Standalone EXE

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

## Usage

### Main Window
- Click the button to toggle exit node ON/OFF
- Check "Start with Windows" to auto-launch on boot
- Click X to minimize to system tray

### System Tray
| Action | Result |
|--------|--------|
| **Left-click** | Toggle exit node ON/OFF |
| **Right-click** | Show menu |

### Tray Icon Colors
| Color | Status |
|-------|--------|
| ⚫ Grey | Exit node OFF (direct connection) |
| 🔴 Red | Exit node ON (routing via exit node) |

## Finding Your Exit Node IP

```bash
tailscale status
```

Look for the device you want to use as exit node and copy its IP (starts with `100.`).

## Troubleshooting

**"Tailscale not found"**
- Verify Tailscale is installed
- Check the path in `config.json` matches your installation

**"Operation failed"**
- Ensure Tailscale is running and logged in
- Check that your exit node is online

**EXE doesn't start**
- Make sure `config.json` is in the same folder as the EXE

## License

MIT License - feel free to modify and distribute.
