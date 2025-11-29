"""
Tailscale Exit Node Toggle App - macOS Version
A menu bar application to toggle Tailscale exit node on/off.
Sits in the macOS top bar for quick access.
"""

import subprocess
import json
from pathlib import Path
import os
import sys

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


class Config:
    """Load and manage configuration."""
    
    def __init__(self):
        # Try multiple config locations
        if getattr(sys, 'frozen', False):
            # Running as bundled app
            bundle_dir = Path(sys.executable).parent.parent / "Resources"
            config_paths = [
                bundle_dir / "config.json",
                Path(sys.executable).parent / "config.json",
                Path.home() / ".config" / "exitnodetoggle" / "config.json",
            ]
        else:
            # Running as script
            config_paths = [
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
        
        with open(config_path, "r") as f:
            data = json.load(f)
        
        # macOS default Tailscale path
        default_tailscale = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
        if not Path(default_tailscale).exists():
            # Try CLI version
            default_tailscale = "tailscale"
        
        self.tailscale_exe = data.get("tailscale_exe", default_tailscale)
        self.exit_node_ip = data.get("exit_node_ip", "")
        
        if self.exit_node_ip == "YOUR_EXIT_NODE_IP_HERE" or not self.exit_node_ip:
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
    
    def get_status(self) -> tuple:
        """
        Check if an exit node is currently active.
        
        Returns:
            tuple: (is_active: bool, current_exit_node: str | None)
        """
        try:
            result = subprocess.run(
                [self.config.tailscale_exe, "status", "--json"],
                capture_output=True,
                text=True
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
            rumps.alert(
                "Error",
                f"Tailscale not found at:\n{self.config.tailscale_exe}\n\n"
                "Make sure Tailscale is installed."
            )
            return False, None
        except json.JSONDecodeError:
            return False, None
        except Exception as e:
            rumps.alert("Error", f"Failed to get status: {e}")
            return False, None
    
    def enable_exit_node(self) -> bool:
        """Enable the exit node."""
        try:
            result = subprocess.run(
                [self.config.tailscale_exe, "set", f"--exit-node={self.config.exit_node_ip}"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            rumps.alert("Error", f"Failed to enable exit node: {e}")
            return False
    
    def disable_exit_node(self) -> bool:
        """Disable the exit node."""
        try:
            result = subprocess.run(
                [self.config.tailscale_exe, "set", "--exit-node="],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
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

