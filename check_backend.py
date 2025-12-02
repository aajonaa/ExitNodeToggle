import os
import sys

try:
    import pystray
    print("Pystray imported")
except ImportError:
    print("Pystray not found")
    sys.exit(1)

try:
    import gi
    print("PyGObject (gi) imported successfully")
    try:
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        print("Gtk 3.0 imported successfully")
    except ValueError as e:
         print(f"Gtk 3.0 not found: {e}")
    except Exception as e:
        print(f"Gtk 3.0 import failed: {e}")
        
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3
        print("AppIndicator3 imported successfully")
    except ValueError as e:
        print(f"AppIndicator3 not found: {e}")
    except Exception as e:
        print(f"AppIndicator3 import failed: {e}")

except ImportError:
    print("PyGObject (gi) not found")

# check pystray backend selection logic (simplified)
from pystray import Icon
try:
    i = Icon('test', title='test')
    # Force internal instantiation if lazy
    # Accessing _impl might be creating it
    print(f"Backend implementation: {i._impl.__class__.__module__}")
except Exception as e:
    print(f"Could not determine backend: {e}")
