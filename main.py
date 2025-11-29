"""
Tailscale Exit Node Toggle App
A simple GUI application to toggle Tailscale exit node on/off.
"""

import subprocess
import tkinter as tk
from tkinter import messagebox
import json
from pathlib import Path
import threading
import sys
import os
import winreg

# System tray support
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_SUPPORT = True
except ImportError:
    TRAY_SUPPORT = False


# App name for registry
APP_NAME = "TailscaleExitNodeToggle"


class Config:
    """Load and manage configuration."""
    
    def __init__(self):
        config_path = Path(__file__).parent / "config.json"
        
        if not config_path.exists():
            raise FileNotFoundError(
                "config.json not found. Please create it with your settings."
            )
        
        with open(config_path, "r") as f:
            data = json.load(f)
        
        self.tailscale_exe = data.get("tailscale_exe", r"C:\Program Files\Tailscale\tailscale.exe")
        self.exit_node_ip = data.get("exit_node_ip", "")
        
        if self.exit_node_ip == "YOUR_EXIT_NODE_IP_HERE" or not self.exit_node_ip:
            messagebox.showwarning(
                "Configuration Required",
                "Please set your exit node IP in config.json"
            )


class StartupManager:
    """Manage Windows startup registration."""
    
    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    @staticmethod
    def get_exe_path() -> str:
        """Get the path to the current executable."""
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            return sys.executable
        else:
            # Running as script
            return f'pythonw.exe "{os.path.abspath(__file__)}"'
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if startup is enabled."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, StartupManager.REG_PATH, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, APP_NAME)
                return True
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False
    
    @staticmethod
    def enable():
        """Enable startup with Windows."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, StartupManager.REG_PATH, 0, winreg.KEY_SET_VALUE)
            exe_path = StartupManager.get_exe_path()
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable startup: {e}")
            return False
    
    @staticmethod
    def disable():
        """Disable startup with Windows."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, StartupManager.REG_PATH, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass  # Already disabled
            winreg.CloseKey(key)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable startup: {e}")
            return False


class TailscaleToggle:
    """Handles Tailscale exit node operations."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def get_status(self) -> tuple[bool, str | None]:
        """
        Check if an exit node is currently active.
        
        Returns:
            tuple: (is_active: bool, current_exit_node: str | None)
        """
        try:
            result = subprocess.run(
                [self.config.tailscale_exe, "status", "--json"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                return False, None
            
            data = json.loads(result.stdout)
            exit_node_status = data.get("ExitNodeStatus")
            
            if exit_node_status is None:
                return False, None
            
            # Get the current exit node IP if available
            current_node = exit_node_status.get("ID", "Unknown")
            return True, current_node
            
        except FileNotFoundError:
            messagebox.showerror(
                "Error",
                f"Tailscale not found at:\n{self.config.tailscale_exe}"
            )
            return False, None
        except json.JSONDecodeError:
            return False, None
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get status: {e}")
            return False, None
    
    def enable_exit_node(self) -> bool:
        """Enable the exit node."""
        try:
            result = subprocess.run(
                [self.config.tailscale_exe, "set", f"--exit-node={self.config.exit_node_ip}"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable exit node: {e}")
            return False
    
    def disable_exit_node(self) -> bool:
        """Disable the exit node."""
        try:
            result = subprocess.run(
                [self.config.tailscale_exe, "set", "--exit-node="],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable exit node: {e}")
            return False


def create_tray_icon(color: str) -> Image.Image:
    """Create a simple colored circle icon for the system tray."""
    size = 64
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw outer circle (border)
    draw.ellipse([2, 2, size-2, size-2], fill='#1a1a2e', outline='#3a3a5e', width=2)
    
    # Draw inner status circle
    inner_margin = 16
    draw.ellipse(
        [inner_margin, inner_margin, size-inner_margin, size-inner_margin],
        fill=color
    )
    
    return image


class App:
    """Main application GUI."""
    
    # Colors
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
        self.tailscale = TailscaleToggle(self.config)
        self.is_on = False
        self.tray_icon = None
        self.startup_enabled = tk.BooleanVar(value=StartupManager.is_enabled())
        
        self.setup_window()
        self.create_widgets()
        self.setup_tray()
        self.refresh_status()
    
    def setup_window(self):
        """Configure the main window."""
        self.root.title("Exit Node Toggle")
        self.root.geometry("320x240")
        self.root.resizable(False, False)
        self.root.configure(bg=self.COLOR_BG)
        
        # Handle window close - minimize to tray instead
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 320) // 2
        y = (self.root.winfo_screenheight() - 240) // 2
        self.root.geometry(f"320x240+{x}+{y}")
    
    def setup_tray(self):
        """Setup system tray icon."""
        if not TRAY_SUPPORT:
            print("System tray not available. Install: pip install pystray pillow")
            # Fall back to normal close behavior
            self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
            return
        
        # Create tray menu
        menu = pystray.Menu(
            pystray.MenuItem("Toggle Exit Node", self.tray_toggle, default=True),
            pystray.MenuItem("Show Window", self.show_window),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows",
                self.toggle_startup,
                checked=lambda item: self.startup_enabled.get()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.quit_app)
        )
        
        # Create initial icon (grey = OFF)
        icon_image = create_tray_icon("#808080")
        self.tray_icon = pystray.Icon(
            "exit_node_toggle",
            icon_image,
            "Exit Node Toggle",
            menu
        )
        
        # Run tray icon in background thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def update_tray_icon(self):
        """Update tray icon color based on status."""
        if not TRAY_SUPPORT or not self.tray_icon:
            return
        
        # Grey when OFF, Red when ON
        color = "#e94560" if self.is_on else "#808080"
        self.tray_icon.icon = create_tray_icon(color)
        
        status = "ON" if self.is_on else "OFF"
        self.tray_icon.title = f"Exit Node: {status}"
    
    def hide_to_tray(self):
        """Hide window to system tray."""
        if TRAY_SUPPORT and self.tray_icon:
            self.root.withdraw()
        else:
            self.quit_app()
    
    def show_window(self, icon=None, item=None):
        """Show the main window."""
        self.root.after(0, self._show_window)
    
    def _show_window(self):
        """Show window (called from main thread)."""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def tray_toggle(self, icon=None, item=None):
        """Toggle from tray menu."""
        self.root.after(0, self.toggle_node)
    
    def toggle_startup(self, icon=None, item=None):
        """Toggle startup with Windows."""
        if self.startup_enabled.get():
            if StartupManager.disable():
                self.startup_enabled.set(False)
        else:
            if StartupManager.enable():
                self.startup_enabled.set(True)
        
        # Update checkbox in GUI
        self.root.after(0, lambda: self.startup_check.config(
            text="✓ Start with Windows" if self.startup_enabled.get() else "Start with Windows"
        ))
    
    def toggle_startup_from_gui(self):
        """Toggle startup from GUI checkbox."""
        # Value already toggled by checkbutton, so we need to apply it
        if self.startup_enabled.get():
            if not StartupManager.enable():
                self.startup_enabled.set(False)
        else:
            if not StartupManager.disable():
                self.startup_enabled.set(True)
    
    def quit_app(self, icon=None, item=None):
        """Properly quit the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()
        self.root.destroy()
    
    def create_widgets(self):
        """Create and layout all widgets."""
        # Main container
        container = tk.Frame(self.root, bg=self.COLOR_BG)
        container.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Title
        title = tk.Label(
            container,
            text="🔒 Tailscale Exit Node",
            font=("Segoe UI", 14, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT
        )
        title.pack(pady=(0, 15))
        
        # Status indicator
        self.status_frame = tk.Frame(container, bg=self.COLOR_CARD, padx=15, pady=10)
        self.status_frame.pack(fill="x", pady=(0, 15))
        
        self.status_dot = tk.Label(
            self.status_frame,
            text="●",
            font=("Segoe UI", 16),
            bg=self.COLOR_CARD,
            fg=self.COLOR_OFF
        )
        self.status_dot.pack(side="left")
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Checking...",
            font=("Segoe UI", 10),
            bg=self.COLOR_CARD,
            fg=self.COLOR_TEXT
        )
        self.status_label.pack(side="left", padx=(8, 0))
        
        # Toggle button
        self.btn_text = tk.StringVar(value="Loading...")
        self.toggle_btn = tk.Button(
            container,
            textvariable=self.btn_text,
            command=self.toggle_node,
            font=("Segoe UI", 11, "bold"),
            bg=self.COLOR_ACCENT,
            fg=self.COLOR_TEXT,
            activebackground=self.COLOR_CARD,
            activeforeground=self.COLOR_TEXT,
            relief="flat",
            cursor="hand2",
            height=2,
            width=25
        )
        self.toggle_btn.pack()
        
        # Exit node info
        self.info_label = tk.Label(
            container,
            text=f"Node: {self.config.exit_node_ip}",
            font=("Segoe UI", 8),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT_DIM
        )
        self.info_label.pack(pady=(10, 0))
        
        # Startup checkbox
        self.startup_check = tk.Checkbutton(
            container,
            text="Start with Windows",
            variable=self.startup_enabled,
            command=self.toggle_startup_from_gui,
            font=("Segoe UI", 9),
            bg=self.COLOR_BG,
            fg=self.COLOR_TEXT_DIM,
            activebackground=self.COLOR_BG,
            activeforeground=self.COLOR_TEXT,
            selectcolor=self.COLOR_CARD,
            cursor="hand2"
        )
        self.startup_check.pack(pady=(8, 0))
    
    def refresh_status(self):
        """Refresh the current exit node status."""
        self.is_on, _ = self.tailscale.get_status()
        self.update_ui()
    
    def update_ui(self):
        """Update UI elements based on current state."""
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
        
        # Update tray icon
        self.update_tray_icon()
    
    def toggle_node(self):
        """Toggle the exit node on/off."""
        self.toggle_btn.config(state="disabled")
        self.btn_text.set("Working...")
        self.root.update()
        
        try:
            if self.is_on:
                success = self.tailscale.disable_exit_node()
            else:
                success = self.tailscale.enable_exit_node()
            
            if success:
                self.is_on = not self.is_on
                self.update_ui()
            else:
                messagebox.showerror("Error", "Operation failed. Check Tailscale status.")
                self.refresh_status()
        finally:
            self.toggle_btn.config(state="normal")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
