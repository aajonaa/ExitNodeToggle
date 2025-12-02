"""
Tailscale Exit Node Toggle App - Linux (GUI Version)
A Tkinter-based GUI application to toggle Tailscale exit node on/off on Linux.
Uses Native GTK3/AppIndicator for the System Tray.
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
import time
import signal
from multiprocessing import Process, Queue

# --- 1. Constants & Logging --------------------------------------------------

APP_NAME = "ExitNodeToggle"
LOG_DIR = Path.home() / ".local" / "state" / "exitnodetoggle"
LOG_FILE = LOG_DIR / "app.log"
TRAY_LOG_FILE = LOG_DIR / "tray.log"

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

def setup_logging(filename, name="App"):
    # Remove existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
            
    logging.basicConfig(
        filename=str(filename),
        level=logging.INFO,
        format=f"%(asctime)s [{name}] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Add console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    formatter = logging.Formatter(f"%(asctime)s [{name}] %(message)s")
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

setup_logging(LOG_FILE, "Main")

def log(msg, level=logging.INFO):
    logging.log(level, msg)


# --- 2. Configuration Class --------------------------------------------------

class Config:
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
            print(msg)
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
            log("Configuration Required: Please set your exit node IP.", logging.WARNING)


# --- 3. Startup Manager ------------------------------------------------------

class StartupManager:
    AUTOSTART_DIR = Path.home() / ".config" / "autostart"
    DESKTOP_FILE = AUTOSTART_DIR / f"{APP_NAME}.desktop"
    
    @staticmethod
    def get_exe_cmd() -> str:
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


# --- 4. Tailscale Controller -------------------------------------------------

class TailscaleController:
    def __init__(self, config: Config):
        self.config = config
    
    def _run(self, args):
        cmd = [self.config.tailscale_exe] + args
        # log(f"Running: {cmd}") # Too verbose
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


# --- 5. Icon Generation ------------------------------------------------------

def generate_icons(output_dir: Path):
    """Generate On/Off PNG icons using Pillow."""
    try:
        from PIL import Image, ImageDraw
        
        def make_icon(color_hex, path):
            size = 64
            color_hex = color_hex.lstrip('#')
            rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
            
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw simple circle
            draw.ellipse([2, 2, size-2, size-2], fill=(26, 26, 46), outline=(58, 58, 94), width=2)
            m = 16
            draw.ellipse([m, m, size-m, size-m], fill=rgb)
            
            image.save(path, "PNG")
            
        on_path = output_dir / "icon_on.png"
        off_path = output_dir / "icon_off.png"
        
        make_icon("00d9a5", on_path)
        make_icon("e94560", off_path)
        
        return str(on_path), str(off_path)
    except ImportError:
        log("Pillow not found. Icons cannot be generated.", logging.ERROR)
        return None, None


# --- 6. Tray Process (Native GTK) --------------------------------------------

def run_tray_process(msg_queue):
    """
    Runs the system tray icon in a separate process using pure GTK+AppIndicator.
    """
    setup_logging(TRAY_LOG_FILE, "Tray")
    logging.info("Tray process initialized.")

    # Import GTK
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib
        
        APP_INDICATOR = None
        try:
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3
            APP_INDICATOR = AppIndicator3
            logging.info("Using AppIndicator3")
        except:
            try:
                gi.require_version('AyatanaAppIndicator3', '0.1')
                from gi.repository import AyatanaAppIndicator3
                APP_INDICATOR = AyatanaAppIndicator3
                logging.info("Using AyatanaAppIndicator3")
            except:
                logging.error("No AppIndicator library found. Tray cannot start.")
                return
    except Exception as e:
        logging.critical(f"Failed to import GTK/Gi: {e}")
        return

    try:
        # Setup Logic
        config = Config()
        tailscale = TailscaleController(config)
        
        # Generate Icons
        icon_on, icon_off = generate_icons(LOG_DIR)
        if not icon_on:
            logging.error("Failed to generate icons. Exiting.")
            return
            
        logging.info(f"Icons: {icon_on}, {icon_off}")

        # Create Indicator
        # ID must be unique
        indicator = APP_INDICATOR.Indicator.new(
            "tailscale-exit-node-toggle",
            icon_off,
            APP_INDICATOR.IndicatorCategory.APPLICATION_STATUS
        )
        indicator.set_status(APP_INDICATOR.IndicatorStatus.ACTIVE)
        
        # Build Menu
        menu = Gtk.Menu()
        
        item_show = Gtk.MenuItem(label="Show Window")
        item_show.connect("activate", lambda _: msg_queue.put("show"))
        menu.append(item_show)
        
        item_toggle = Gtk.MenuItem(label="Toggle Exit Node")
        
        def on_toggle(_):
            logging.info("Toggle clicked.")
            # Run in thread
            threading.Thread(target=do_toggle, daemon=True).start()
            
        def do_toggle():
            # Optimistically toggle based on last known or check?
            # Let's just toggle based on check
            active, _ = tailscale.get_status()
            if active:
                tailscale.disable_exit_node()
            else:
                tailscale.enable_exit_node()
            # Poll loop will update icon
            # Force immediate check
            GLib.idle_add(update_icon)

        item_toggle.connect("activate", on_toggle)
        menu.append(item_toggle)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        item_quit = Gtk.MenuItem(label="Quit")
        def on_quit(_):
            logging.info("Quit clicked.")
            msg_queue.put("quit")
            Gtk.main_quit()
            
        item_quit.connect("activate", on_quit)
        menu.append(item_quit)
        
        menu.show_all()
        indicator.set_menu(menu)
        
        # Poll Status
        def update_icon():
            try:
                is_active, _ = tailscale.get_status()
                if is_active:
                    indicator.set_icon_full(icon_on, "Tailscale ON")
                else:
                    indicator.set_icon_full(icon_off, "Tailscale OFF")
            except Exception as e:
                logging.error(f"Poll error: {e}")
            return True # Keep running

        # Poll every 5 seconds
        GLib.timeout_add_seconds(5, update_icon)
        # Run once immediately
        GLib.idle_add(update_icon)
        
        # Handle Ctrl+C
        signal.signal(signal.SIGINT, lambda *args: Gtk.main_quit())

        logging.info("Entering GTK main loop...")
        Gtk.main()
        logging.info("GTK main loop exited.")

    except Exception as e:
        logging.critical(f"Tray crashed: {e}")
        import traceback
        logging.critical(traceback.format_exc())


# --- 7. Main App (Tkinter) ---------------------------------------------------

class App:
    def __init__(self, root: tk.Tk, msg_queue):
        self.root = root
        self.msg_queue = msg_queue
        self.config = Config()
        self.tailscale = TailscaleController(self.config)
        self.is_on = False
        
        self.setup_window()
        self.create_widgets()
        
        self.root.after(100, self.refresh_status)
        self.root.after(100, self.check_queue)
    
    def setup_window(self):
        self.root.title("Exit Node Toggle")
        self.root.geometry("320x280")
        self.root.configure(bg="#1a1a2e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Center
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 320) // 2
        y = (self.root.winfo_screenheight() - 280) // 2
        self.root.geometry(f"+{x}+{y}")

    def create_widgets(self):
        bg = "#1a1a2e"
        card = "#16213e"
        fg = "#eaeaea"
        
        tk.Label(self.root, text="🔒 Tailscale Exit Node", font=("Sans", 14, "bold"), 
                 bg=bg, fg=fg).pack(pady=15)
        
        self.status_lbl = tk.Label(self.root, text="Checking...", font=("Sans", 11), bg=card, fg=fg, width=30, pady=10)
        self.status_lbl.pack(pady=10)
        
        self.btn = tk.Button(self.root, text="Toggle", command=self.on_toggle, 
                             bg="#0f3460", fg=fg, font=("Sans", 11, "bold"), 
                             relief="flat", padx=20, pady=10)
        self.btn.pack(pady=10)
        
        self.chk_var = tk.BooleanVar(value=StartupManager.is_enabled())
        tk.Checkbutton(self.root, text="Start on Login", variable=self.chk_var, 
                       command=self.toggle_startup, bg=bg, fg=fg, selectcolor=card,
                       activebackground=bg, activeforeground=fg).pack()

        tk.Button(self.root, text="Quit App", command=self.quit_app, bg=bg, fg="#8892a0", 
                  relief="flat", bd=0, cursor="hand2").pack(side="bottom", pady=10)

    def refresh_status(self):
        is_active, _ = self.tailscale.get_status()
        self.is_on = is_active
        
        if is_active:
            self.status_lbl.config(text="✅ Connected via Exit Node", fg="#00d9a5")
            self.btn.config(text="Disable Exit Node", bg="#2d4a3e")
        else:
            self.status_lbl.config(text="⚪ Direct Connection", fg="#e94560")
            self.btn.config(text="Enable Exit Node", bg="#0f3460")
            
        self.root.after(5000, self.refresh_status)

    def on_toggle(self):
        self.btn.config(state="disabled", text="Working...")
        self.root.update()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        if self.is_on:
            self.tailscale.disable_exit_node()
        else:
            self.tailscale.enable_exit_node()
        self.root.after(0, lambda: self.btn.config(state="normal"))
        self.root.after(0, self.refresh_status)

    def toggle_startup(self):
        if self.chk_var.get():
            StartupManager.enable()
        else:
            StartupManager.disable()

    def on_close(self):
        # Minimize to tray
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()

    def quit_app(self):
        self.root.quit()

    def check_queue(self):
        try:
            while not self.msg_queue.empty():
                msg = self.msg_queue.get_nowait()
                if msg == "show":
                    self.show_window()
                elif msg == "quit":
                    self.quit_app()
        except:
            pass
        self.root.after(500, self.check_queue)


def main():
    msg_queue = Queue()
    
    # Check if we have tray capability
    has_tray = False
    try:
        import gi
        gi.require_version('AppIndicator3', '0.1')
        has_tray = True
    except:
        try:
            import gi
            gi.require_version('AyatanaAppIndicator3', '0.1')
            has_tray = True
        except:
            pass
    
    tray_process = None
    if has_tray:
        tray_process = Process(target=run_tray_process, args=(msg_queue,))
        tray_process.start()
    else:
        print("Tray support missing (AppIndicator3). Running window-only.")

    root = tk.Tk()
    app = App(root, msg_queue)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if tray_process and tray_process.is_alive():
            tray_process.terminate()

if __name__ == "__main__":
    main()