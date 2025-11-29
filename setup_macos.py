"""
py2app setup script for macOS Exit Node Toggle app.
Usage: python setup_macos.py py2app
"""

from setuptools import setup
import sys

# Ensure we're on macOS
if sys.platform != 'darwin':
    print("This setup script is for macOS only.")
    print("For Windows, use: pyinstaller --onefile --windowed main.py")
    sys.exit(1)

APP = ['main_macos.py']
DATA_FILES = ['config.json']

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'icon.icns',  # Optional: add your own icon
    'plist': {
        'CFBundleName': 'Exit Node Toggle',
        'CFBundleDisplayName': 'Exit Node Toggle',
        'CFBundleIdentifier': 'com.tailscale.exitnodetoggle',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSUIElement': True,  # Hide from Dock (menu bar app only)
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
        'NSHumanReadableCopyright': 'MIT License',
    },
    'packages': ['rumps'],
    'includes': ['json', 'subprocess', 'pathlib'],
}

setup(
    name='Exit Node Toggle',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

