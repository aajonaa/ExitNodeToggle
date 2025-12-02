#!/bin/bash
# Build script for Linux (PyInstaller)

echo "--- Building Exit Node Toggle for Linux ---"

# 1. Check for virtualenv
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

# 2. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# 3. Build
echo "Running PyInstaller..."
# --add-data format for Linux is source:dest
pyinstaller --onefile --windowed --hidden-import PyQt5 --name "ExitNodeToggle" --add-data "config.json:." main_linux.py

echo "--- Build Complete ---"
echo "Executable is located at: dist/ExitNodeToggle"
echo "Ensure config.json is in the same directory as the executable when running."
