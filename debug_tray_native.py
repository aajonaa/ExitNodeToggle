import sys
import os
import logging
import signal
import time

# Configure basic logging to stdout
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("TrayDebug")

print("--- Starting Tray Debug Script ---")

try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    print("GTK 3.0 imported.")
except Exception as e:
    print(f"Failed to import GTK: {e}")
    sys.exit(1)

APP_INDICATOR_ID = None
try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
    APP_INDICATOR_ID = "AppIndicator3"
    print("AppIndicator3 imported.")
except Exception as e:
    print(f"AppIndicator3 failed: {e}")
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import AyatanaAppIndicator3 as AppIndicator3
        APP_INDICATOR_ID = "AyatanaAppIndicator3"
        print("AyatanaAppIndicator3 imported.")
    except Exception as e:
        print(f"AyatanaAppIndicator3 failed: {e}")
        print("No AppIndicator library found.")
        sys.exit(1)

# Create a dummy icon
icon_path = os.path.abspath("icon.iconset/icon_32x32.png")
if not os.path.exists(icon_path):
    print(f"Icon not found at {icon_path}, making a dummy one if PIL exists")
    try:
        from PIL import Image
        img = Image.new('RGB', (32, 32), color = 'red')
        img.save('debug_icon.png')
        icon_path = os.path.abspath('debug_icon.png')
        print(f"Created debug_icon.png at {icon_path}")
    except:
        print("PIL not found, cannot create dummy icon.")

print(f"Using icon: {icon_path}")

def quit_app(_):
    print("Quit clicked")
    Gtk.main_quit()

indicator = AppIndicator3.Indicator.new(
    "test-tray-id",
    icon_path,
    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
)
indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

menu = Gtk.Menu()
item = Gtk.MenuItem(label="Test Item")
item.connect("activate", quit_app)
menu.append(item)
menu.show_all()

indicator.set_menu(menu)

print("Entering GTK main loop. Look for the icon in your tray.")
# Handle Ctrl+C
signal.signal(signal.SIGINT, lambda *args: Gtk.main_quit())

Gtk.main()
print("Exited GTK main loop.")
