"""
Tailscale Exit Node Toggle App - Linux (GUI Version)
A Tkinter-based GUI application to toggle Tailscale exit node on/off on Linux.
Includes optional system tray support and handles backend compatibility.
"""

import subprocess
import tkinter as tk
from tkinter import messagebox
import json
from pathlib import Path
import threading
import sys
import os
import logging
import shutil

# --- Dependency Checks -------------------------------------------------------

# System tray support (pystray + PIL)
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    print("Warning: pystray and/or pillow not found. Tray support disabled.")

# AppIndicator support (Critical for interactive tray on Gnome/KDE/Arch)
HAS_APP_INDICATOR = False
try:
    import gi
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
    HAS_APP_INDICATOR = True
except (ImportError, ValueError):
    pass


# --- Logging & Constants -----------------------------------------------------

APP_NAME = "ExitNodeToggle"
LOG_DIR = Path.home() / ".local" / "state" / "exitnodetoggle"
LOG_FILE = LOG_DIR / "app.log"

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Console handler
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

def log(msg, level=logging.INFO):
    logging.log(level, msg)


# --- Configuration -----------------------------------------------------------

class Config:
    """Load and manage configuration for Linux."""

    def __init__(self) -> None:
        base_dir = Path(__file__).parent.absolute()
        xdg_config = Path.home() / ".config" / "exitnodetoggle" / "config.json"
        
        candidate_paths = [
            xdg_config,
            base_dir / "config.linux.json",
            base_dir / "config.json",
        ]

        self.config_path: Path | None = None
        for p in candidate_paths:
            if p.exists():
                self.config_path = p
                break

        if self.config_path is None:
            msg = "No configuration file found. Please create config.json."
            log(msg, logging.CRITICAL)
            messagebox.showerror("Configuration Error", msg)
            sys.exit(1)

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            log(f"Loaded config from {self.config_path}")
        except Exception as e:
            log(f"Failed to parse config: {e}", logging.CRITICAL)
            sys.exit(1)

        self.tailscale_exe: str = data.get("tailscale_exe", "tailscale")
        self.exit_node_ip: str = data.get("exit_node_ip", "")
        
        self.valid = True
        if not self.exit_node_ip or self.exit_node_ip == "YOUR_EXIT_NODE_IP_HERE":
            self.valid = False
            messagebox.showwarning(
                "Configuration Required",
                "Please set your exit node IP in config.json"
            )


# --- Startup Manager (Linux XDG Autostart) -----------------------------------

class StartupManager:
    """Manage Linux startup via ~/.config/autostart/."""
    
    AUTOSTART_DIR = Path.home() / ".config" / "autostart"
    DESKTOP_FILE = AUTOSTART_DIR / f"{APP_NAME}.desktop"
    
    @staticmethod
    def get_exe_cmd() -> str:
        """Get the command to run the app."""
        python_exe = sys.executable
        script_path = str(Path(__file__).absolute())
        return f'{python_exe} "{script_path}"'
    
    @staticmethod
    def is_enabled() -> bool:
        return StartupManager.DESKTOP_FILE.exists()
    
    @staticmethod
    def enable() -> bool:
        try:
            StartupManager.AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            
            cmd = StartupManager.get_exe_cmd()
            content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Toggle Tailscale Exit Node
Exec={cmd}
Terminal=false
Icon=network-vpn
Categories=Network;Utility;
"""
            with open(StartupManager.DESKTOP_FILE, "w") as f:
                f.write(content)
            return True
        except Exception as e:
            log(f"Failed to enable startup: {e}", logging.ERROR)
            return False
    
    @staticmethod
    def disable() -> bool:
        try:
            if StartupManager.DESKTOP_FILE.exists():
                StartupManager.DESKTOP_FILE.unlink()
            return True
        except Exception as e:
            log(f"Failed to disable startup: {e}", logging.ERROR)
            return False


# --- Tailscale Controller ----------------------------------------------------

class TailscaleController:
    """Handles Tailscale exit node operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def _run(self, args):
        cmd = [self.config.tailscale_exe] + args
        log(f"Running: {cmd}")
        return subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=10
        )

    def get_status(self) -> tuple[bool, str | None]:
        try:
            res = self._run(["status", "--json"])
            if res.returncode != 0:
                return False, None
            
            data = json.loads(res.stdout)
            exit_node_status = data.get("ExitNodeStatus")
            if not exit_node_status:
                return False, None
            
            return True, exit_node_status.get("ID", "Unknown")
            
        except Exception as e:
            log(f"Status check error: {e}", logging.ERROR)
            return False, None
    
    def enable_exit_node(self) -> bool:
        if not self.config.valid:
            return False
        try:
            res = self._run(["set", f"--exit-node={self.config.exit_node_ip}"])
            return res.returncode == 0
        except Exception as e:
            log(f"Enable error: {e}", logging.ERROR)
            return False
    
    def disable_exit_node(self) -> bool:
        try:
            res = self._run(["set", "--exit-node="])
            return res.returncode == 0
        except Exception as e:
            log(f"Disable error: {e}", logging.ERROR)
            return False


# --- UI & App ----------------------------------------------------------------

def create_tray_icon(color_hex: str) -> "Image.Image":
    """Create a simple colored circle icon."""
    size = 64
    # Hex to RGB
    color_hex = color_hex.lstrip('#')
    rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
    
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Outer circle
    draw.ellipse([2, 2, size-2, size-2], fill=(26, 26, 46), outline=(58, 58, 94), width=2)
    # Inner circle
    m = 16
    draw.ellipse([m, m, size-m, size-m], fill=rgb)
    return image


class App:
    """Main application GUI (Tkinter)."""
    
    # Theme Colors
    COLOR_BG = "#1a1a2e"
    COLOR_CARD = "#16213e"
    COLOR_ACCENT = "#0f3460"
    COLOR_ON = "#00d9a5"
    COLOR_OFF = "#e94560"
    COLOR_TEXT = "#eaeaea"
    COLOR_TEXT_DIM = "#8892a0"
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = Config()
        self.tailscale = TailscaleController(self.config)
        self.is_on = False
        self.tray_icon = None
        
        # Settings
        self.startup_enabled = tk.BooleanVar(value=StartupManager.is_enabled())
        
        # Default minimize behavior:
        # Only default to True if we are confident the tray works (AppIndicator present)
        self.minimize_to_tray = tk.BooleanVar(value=HAS_APP_INDICATOR and HAS_PYSTRAY)
        
        self.setup_window()
        self.create_widgets()
        self.setup_tray()
        
        # Initial status check
        self.root.after(100, self.refresh_status)
    
    def setup_window(self):
        self.root.title("Exit Node Toggle")
        self.root.geometry("320x320") # Increased height for extra controls
        self.root.resizable(False, False)
        self.root.configure(bg=self.COLOR_BG)
        
        # Handle closing -> minimize to tray OR quit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)
        
        # Center
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 320) // 2
        y = (sh - 320) // 2
        self.root.geometry(f"+{x}+{y}")

    def setup_tray(self):
        if not HAS_PYSTRAY:
            return
        
        menu = pystray.Menu(
            pystray.MenuItem("Show Window", self.show_window, default=True),
            pystray.MenuItem("Toggle Exit Node", self.tray_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit_app)
        )
        
        icon_img = create_tray_icon(self.COLOR_OFF)
        self.tray_icon = pystray.Icon("ExitNodeToggle", icon_img, "Exit Node: OFF", menu)
        
        # Run tray in background thread
        t = threading.Thread(target=self.tray_icon.run, daemon=True)
        t.start()

    def update_tray_icon(self):
        if not self.tray_icon:
            return
        
        color = self.COLOR_ON if self.is_on else self.COLOR_OFF
        self.tray_icon.icon = create_tray_icon(color)
        self.tray_icon.title = "Exit Node: ON" if self.is_on else "Exit Node: OFF"

    def on_close_window(self):
        """Minimize to tray if enabled, otherwise quit."""
        if self.minimize_to_tray.get() and self.tray_icon:
            self.root.withdraw()
            # Show notification hint once
            if not getattr(self, '_minimized_once', False):
                log("Minimized to system tray.")
                self._minimized_once = True
        else:
            self.quit_app()

    def show_window(self, icon=None, item=None):
        """Bring window back."""
        self.root.after(0, self._restore_window)
    
    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()

    def tray_toggle(self, icon=None, item=None):
        """Toggle from tray."""
        self.root.after(0, self.toggle_node)

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

    def create_widgets(self):
        # Styles
        font_title = ("Sans", 14, "bold")
        font_main = ("Sans", 10)
        font_btn = ("Sans", 11, "bold")
        font_small = ("Sans", 9)
        
        container = tk.Frame(self.root, bg=self.COLOR_BG)
        container.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        tk.Label(container, text="🔒 Tailscale Exit Node", font=font_title, 
                 bg=self.COLOR_BG, fg=self.COLOR_TEXT).pack(pady=(0, 15))
        
        # Status Card
        status_frame = tk.Frame(container, bg=self.COLOR_CARD, padx=15, pady=10)
        status_frame.pack(fill="x", pady=(0, 15))
        
        self.status_dot = tk.Label(status_frame, text="●", font=("Sans", 16), 
                                   bg=self.COLOR_CARD, fg=self.COLOR_OFF)
        self.status_dot.pack(side="left")
        
        self.status_label = tk.Label(status_frame, text="Checking...", font=font_main,
                                     bg=self.COLOR_CARD, fg=self.COLOR_TEXT)
        self.status_label.pack(side="left", padx=(8, 0))
        
        # Button
        self.btn_text = tk.StringVar(value="Loading...")
        self.toggle_btn = tk.Button(
            container, textvariable=self.btn_text, command=self.toggle_node,
            font=font_btn, bg=self.COLOR_ACCENT, fg=self.COLOR_TEXT,
            activebackground=self.COLOR_CARD, activeforeground=self.COLOR_TEXT,
            relief="flat", cursor="hand2", height=2, width=25,
            borderwidth=0
        )
        self.toggle_btn.pack()
        
        # Info
        tk.Label(container, text=f"Node: {self.config.exit_node_ip}", font=("Sans", 8),
                 bg=self.COLOR_BG, fg=self.COLOR_TEXT_DIM).pack(pady=(10, 0))
        
        # Separator
        tk.Frame(container, height=1, bg=self.COLOR_CARD).pack(fill="x", pady=10)

        # Options Label
        tk.Label(container, text="Options", font=("Sans", 8, "bold"),
                 bg=self.COLOR_BG, fg=self.COLOR_TEXT_DIM).pack(anchor="w")

        # Startup Checkbox
        chk_startup = tk.Checkbutton(
            container, text="Start on Login", variable=self.startup_enabled,
            command=self.toggle_startup, font=font_small,
            bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD,
            activebackground=self.COLOR_BG, activeforeground=self.COLOR_TEXT
        )
        chk_startup.pack(anchor="w")

        # Minimize to Tray Checkbox
        chk_tray = tk.Checkbutton(
            container, text="Close to Tray", variable=self.minimize_to_tray,
            font=font_small,
            bg=self.COLOR_BG, fg=self.COLOR_TEXT, selectcolor=self.COLOR_CARD,
            activebackground=self.COLOR_BG, activeforeground=self.COLOR_TEXT
        )
        chk_tray.pack(anchor="w")

        # Warnings/Tips
        if not HAS_APP_INDICATOR:
            tip_frame = tk.Frame(container, bg=self.COLOR_BG, pady=5)
            tip_frame.pack(fill="x")
            tk.Label(tip_frame, text="⚠ Tray interaction requires:", 
                     font=("Sans", 7), bg=self.COLOR_BG, fg="#e94560").pack(anchor="w")
            e = tk.Entry(tip_frame, font=("Sans", 7), bg=self.COLOR_CARD, fg=self.COLOR_TEXT, borderwidth=0)
            e.insert(0, "sudo pacman -S libappindicator-gtk3")
            e.config(state="readonly")
            e.pack(fill="x")

        # Quit Button (Explicit)
        tk.Button(
            container, text="Quit Application", command=self.quit_app,
            font=("Sans", 8), bg=self.COLOR_BG, fg=self.COLOR_TEXT_DIM,
            activebackground=self.COLOR_BG, activeforeground=self.COLOR_OFF,
            relief="flat", cursor="hand2", borderwidth=0
        ).pack(pady=(10, 0), anchor="e")

    def refresh_status(self):
        is_active, _ = self.tailscale.get_status()
        if is_active != self.is_on:
            self.is_on = is_active
            self.update_ui()
        
        # Poll every 5 seconds
        self.root.after(5000, self.refresh_status)

    def update_ui(self):
        if self.is_on:
            self.status_dot.config(fg=self.COLOR_ON)
            self.status_label.config(text="Connected via Exit Node")
            self.btn_text.set("⏹  Disable Exit Node")
            self.toggle_btn.config(bg="#2d4a3e")
        else:
            self.status_dot.config(fg=self.COLOR_OFF)
            self.status_label.config(text="Direct Connection")
            self.btn_text.set("▶  Enable Exit Node")
            self.toggle_btn.config(bg=self.COLOR_ACCENT)
        
        self.update_tray_icon()

    def toggle_node(self):
        self.toggle_btn.config(state="disabled")
        self.btn_text.set("Working...")
        self.root.update()
        
        # Run in thread to keep UI responsive
        threading.Thread(target=self._toggle_worker, daemon=True).start()
    
    def _toggle_worker(self):
        if self.is_on:
            success = self.tailscale.disable_exit_node()
        else:
            success = self.tailscale.enable_exit_node()
        
        # Schedule UI update on main thread
        self.root.after(0, lambda: self._toggle_complete(success))

    def _toggle_complete(self, success):
        if success:
            self.is_on = not self.is_on
            self.update_ui()
        else:
            messagebox.showerror("Error", "Operation failed. Check logs/tailscale.")
            self.refresh_status()
        self.toggle_btn.config(state="normal")

    def toggle_startup(self):
        if self.startup_enabled.get():
            if not StartupManager.enable():
                self.startup_enabled.set(False)
        else:
            if not StartupManager.disable():
                self.startup_enabled.set(True)


def main():
    root = tk.Tk()
    app = App(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.quit_app()


if __name__ == "__main__":
    main()