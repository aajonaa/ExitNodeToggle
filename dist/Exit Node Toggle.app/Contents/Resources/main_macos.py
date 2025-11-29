"""
Tailscale Exit Node Toggle App - macOS Version
A menu bar application to toggle Tailscale exit node on/off.
Sits in the macOS top bar for quick access.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# macOS menu bar support
try:
    import rumps
    MENUBAR_SUPPORT = True
except ImportError:
    MENUBAR_SUPPORT = False
    print("rumps not installed. Install with: pip install rumps")
    sys.exit(1)


# App name for Launch Agent
APP_NAME = "com.tailscale.exitnodetoggle"
LOG_FILE = Path.home() / "Library" / "Logs" / "ExitNodeToggle" / "exit_node_toggle.log"

LAUNCHAGENT_PLIST = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{APP_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{{app_path}}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""


def log(message: str) -> None:
    """Append a timestamped log line for easier troubleshooting."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"[{timestamp}] {message}\n")
    except Exception:
        # Logging should never crash the app
        pass


class Config:
    """Load and manage configuration."""
    
    def __init__(self):
        # Try multiple config locations. Prefer user-level config so the
        # bundled app and the dev script share the same settings.
        if getattr(sys, 'frozen', False):
            # Running as bundled app
            bundle_dir = Path(sys.executable).parent.parent / "Resources"
            config_paths = [
                Path.home() / "Library" / "Application Support" / "ExitNodeToggle" / "config.json",
                Path.home() / ".config" / "exitnodetoggle" / "config.json",
                bundle_dir / "config.json",
                Path(sys.executable).parent / "config.json",
            ]
        else:
            # Running as script
            config_paths = [
                Path.home() / "Library" / "Application Support" / "ExitNodeToggle" / "config.json",
                Path.home() / ".config" / "exitnodetoggle" / "config.json",
                Path(__file__).parent / "config.json",
                Path.home() / ".config" / "exitnodetoggle" / "config.json",
            ]
        
        config_path = None
        for p in config_paths:
            if p.exists():
                config_path = p
                break
        
        if not config_path:
            rumps.alert(
                title="Configuration Required",
                message="config.json not found. Please create it with your settings.\n\n"
                        f"Expected locations:\n" + "\n".join(str(p) for p in config_paths)
            )
            sys.exit(1)
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            log(f"Loaded config from {config_path}")
        
        # macOS default Tailscale path
        default_tailscale = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
        if not Path(default_tailscale).exists():
            # Try CLI version
            default_tailscale = "tailscale"
        
        self.tailscale_exe = data.get("tailscale_exe", default_tailscale)
        self.exit_node_ip = data.get("exit_node_ip", "")
        
        if self.exit_node_ip == "YOUR_EXIT_NODE_IP_HERE" or not self.exit_node_ip:
            log("exit_node_ip not configured")
            rumps.alert(
                title="Configuration Required",
                message="Please set your exit node IP in config.json"
            )


class StartupManager:
    """Manage macOS startup via Launch Agents."""
    
    @staticmethod
    def get_launchagent_path() -> Path:
        """Get the path to the Launch Agent plist."""
        return Path.home() / "Library" / "LaunchAgents" / f"{APP_NAME}.plist"
    
    @staticmethod
    def get_app_path() -> str:
        """Get the path to the current application."""
        if getattr(sys, 'frozen', False):
            # Running as bundled app - get the .app bundle path
            app_path = Path(sys.executable).parent.parent.parent
            return str(app_path)
        else:
            # Running as script
            return f"/usr/bin/python3 {os.path.abspath(__file__)}"
    
    @staticmethod
    def is_enabled() -> bool:
        """Check if startup is enabled."""
        return StartupManager.get_launchagent_path().exists()
    
    @staticmethod
    def enable() -> bool:
        """Enable startup with macOS login."""
        try:
            plist_path = StartupManager.get_launchagent_path()
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            
            app_path = StartupManager.get_app_path()
            plist_content = LAUNCHAGENT_PLIST.replace("{app_path}", app_path)
            
            with open(plist_path, "w") as f:
                f.write(plist_content)
            
            # Load the Launch Agent
            subprocess.run(["launchctl", "load", str(plist_path)], check=False)
            return True
        except Exception as e:
            rumps.alert("Error", f"Failed to enable startup: {e}")
            return False
    
    @staticmethod
    def disable() -> bool:
        """Disable startup with macOS login."""
        try:
            plist_path = StartupManager.get_launchagent_path()
            if plist_path.exists():
                # Unload the Launch Agent
                subprocess.run(["launchctl", "unload", str(plist_path)], check=False)
                plist_path.unlink()
            return True
        except Exception as e:
            rumps.alert("Error", f"Failed to disable startup: {e}")
            return False


class TailscaleToggle:
    """Handles Tailscale exit node operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self._tried_start = False
    
    def _ensure_gui_running(self):
        """Try to start the Tailscale GUI once if not already running."""
        if self._tried_start:
            return
        self._tried_start = True
        try:
            log("Attempting to start Tailscale GUI")
            subprocess.run(["open", "-g", "-a", "Tailscale"], check=False)
            time.sleep(2)
        except Exception as e:
            log(f"Failed to start Tailscale GUI: {e}")
    
    def _run_tailscale(self, args):
        """Run a tailscale CLI command with logging and a single retry if GUI is down."""
        cmd = [self.config.tailscale_exe] + args
        env = os.environ.copy()
        env.setdefault("PATH", "/usr/local/bin:/opt/homebrew/bin:/Applications/Tailscale.app/Contents/MacOS:/usr/bin:/bin:/usr/sbin:/sbin")
        
        log(f"Running command: {' '.join(cmd)} with PATH={env['PATH']}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        log(f"Return code: {result.returncode}")
        if result.stdout:
            log(f"stdout: {result.stdout.strip()}")
        if result.stderr:
            log(f"stderr: {result.stderr.strip()}")
        
        gui_failure = "failed to start" in (result.stdout or "").lower() or "failed to start" in (result.stderr or "").lower()
        if gui_failure and not self._tried_start:
            self._ensure_gui_running()
            return self._run_tailscale(args)
        
        return result
    
    def get_status(self) -> tuple:
        """
        Check if an exit node is currently active.
        
        Returns:
            tuple: (is_active: bool, current_exit_node: str | None)
        """
        try:
            result = self._run_tailscale(["status", "--json"])
            
            if result.returncode != 0:
                log(f"tailscale status failed ({result.returncode}): {result.stderr.strip()}")
                return False, None
            
            data = json.loads(result.stdout)
            exit_node_status = data.get("ExitNodeStatus")
            
            if exit_node_status is None:
                return False, None
            
            # Get the current exit node IP if available
            current_node = exit_node_status.get("ID", "Unknown")
            return True, current_node
            
        except FileNotFoundError:
            log(f"Tailscale binary not found at {self.config.tailscale_exe}")
            rumps.alert(
                "Error",
                f"Tailscale not found at:\n{self.config.tailscale_exe}\n\n"
                "Make sure Tailscale is installed."
            )
            return False, None
        except json.JSONDecodeError:
            log("Failed to parse tailscale status output")
            return False, None
        except Exception as e:
            log(f"Exception in get_status: {e}")
            rumps.alert("Error", f"Failed to get status: {e}")
            return False, None
    
    def enable_exit_node(self) -> bool:
        """Enable the exit node."""
        try:
            result = self._run_tailscale(["set", f"--exit-node={self.config.exit_node_ip}"])
            if result.returncode != 0:
                log(f"tailscale set exit-node failed ({result.returncode}): {result.stderr.strip()}")
            return result.returncode == 0
        except Exception as e:
            log(f"Exception enabling exit node: {e}")
            rumps.alert("Error", f"Failed to enable exit node: {e}")
            return False
    
    def disable_exit_node(self) -> bool:
        """Disable the exit node."""
        try:
            result = self._run_tailscale(["set", "--exit-node="])
            if result.returncode != 0:
                log(f"tailscale clear exit-node failed ({result.returncode}): {result.stderr.strip()}")
            return result.returncode == 0
        except Exception as e:
            log(f"Exception disabling exit node: {e}")
            rumps.alert("Error", f"Failed to disable exit node: {e}")
            return False


class ExitNodeToggleApp(rumps.App):
    """macOS Menu Bar Application."""
    
    # Icons (using emoji for simplicity, can be replaced with actual icons)
    ICON_OFF = "🔓"  # Direct connection
    ICON_ON = "🔒"   # Exit node active
    
    def __init__(self):
        super().__init__(
            name="Exit Node Toggle",
            title=self.ICON_OFF,
            quit_button=None  # We'll add our own quit button
        )
        
        self.config = Config()
        self.tailscale = TailscaleToggle(self.config)
        self.is_on = False
        self.startup_enabled = StartupManager.is_enabled()
        
        self.setup_menu()
        self.refresh_status()
        
        # Start status refresh timer (every 30 seconds)
        self.timer = rumps.Timer(self.timer_refresh, 30)
        self.timer.start()
    
    def setup_menu(self):
        """Setup the menu bar menu."""
        self.status_item = rumps.MenuItem("Status: Checking...")
        self.status_item.set_callback(None)  # Non-clickable
        
        self.toggle_item = rumps.MenuItem("Toggle Exit Node", callback=self.toggle_clicked)
        
        self.node_info = rumps.MenuItem(f"Node: {self.config.exit_node_ip}")
        self.node_info.set_callback(None)  # Non-clickable
        
        self.startup_item = rumps.MenuItem(
            "Start at Login",
            callback=self.toggle_startup
        )
        self.startup_item.state = self.startup_enabled
        
        self.menu = [
            self.status_item,
            None,  # Separator
            self.toggle_item,
            None,  # Separator
            self.node_info,
            self.startup_item,
            None,  # Separator
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
    
    def timer_refresh(self, sender):
        """Timer callback to refresh status."""
        self.refresh_status()
    
    def refresh_status(self):
        """Refresh the current exit node status."""
        self.is_on, _ = self.tailscale.get_status()
        self.update_ui()
    
    def update_ui(self):
        """Update UI elements based on current state."""
        if self.is_on:
            self.title = self.ICON_ON
            self.status_item.title = "Status: ✅ Connected via Exit Node"
            self.toggle_item.title = "⏹ Disable Exit Node"
        else:
            self.title = self.ICON_OFF
            self.status_item.title = "Status: ⚪ Direct Connection"
            self.toggle_item.title = "▶ Enable Exit Node"
    
    @rumps.clicked("Toggle Exit Node")
    def toggle_clicked(self, sender):
        """Handle toggle menu item click."""
        self.toggle_node()
    
    def toggle_node(self):
        """Toggle the exit node on/off."""
        # Show working state
        original_title = self.toggle_item.title
        self.toggle_item.title = "⏳ Working..."
        
        try:
            if self.is_on:
                success = self.tailscale.disable_exit_node()
            else:
                success = self.tailscale.enable_exit_node()
            
            if success:
                self.is_on = not self.is_on
                self.update_ui()
                
                # Show notification
                status = "enabled" if self.is_on else "disabled"
                rumps.notification(
                    title="Exit Node Toggle",
                    subtitle="",
                    message=f"Exit node {status}",
                    sound=False
                )
            else:
                rumps.alert("Error", "Operation failed. Check Tailscale status.")
                self.refresh_status()
        except Exception as e:
            rumps.alert("Error", str(e))
            self.toggle_item.title = original_title
    
    def toggle_startup(self, sender):
        """Toggle startup at login."""
        if self.startup_enabled:
            if StartupManager.disable():
                self.startup_enabled = False
                sender.state = False
        else:
            if StartupManager.enable():
                self.startup_enabled = True
                sender.state = True
    
    def quit_app(self, sender):
        """Quit the application."""
        rumps.quit_application()


def main():
    if not MENUBAR_SUPPORT:
        print("Error: rumps library is required for macOS menu bar support.")
        print("Install it with: pip install rumps")
        sys.exit(1)
    
    app = ExitNodeToggleApp()
    app.run()


if __name__ == "__main__":
    main()

