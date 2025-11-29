#!/bin/bash
# Build script for macOS Exit Node Toggle app
# Creates a .app bundle and optionally a DMG installer

set -e

echo "🔧 Exit Node Toggle - macOS Build Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script must be run on macOS${NC}"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install rumps py2app

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.dmg

# Check for config.json
if [ ! -f "config.json" ]; then
    echo -e "${YELLOW}⚠️  config.json not found. Creating default...${NC}"
    cat > config.json << 'EOF'
{
    "tailscale_exe": "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
    "exit_node_ip": "YOUR_EXIT_NODE_IP_HERE"
}
EOF
fi

# Build the app
echo "🔨 Building application..."
python3 setup_macos.py py2app

# Check if build was successful
if [ -d "dist/Exit Node Toggle.app" ]; then
    echo -e "${GREEN}✓ App bundle created successfully!${NC}"
    echo "  Location: dist/Exit Node Toggle.app"
else
    echo -e "${RED}Error: Build failed${NC}"
    exit 1
fi

# Copy config.json into the app bundle Resources
echo "📋 Copying configuration..."
cp config.json "dist/Exit Node Toggle.app/Contents/Resources/"

# Create DMG (optional)
echo ""
read -p "Would you like to create a DMG installer? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📀 Creating DMG installer..."
    
    DMG_NAME="ExitNodeToggle-1.0.0.dmg"
    VOLUME_NAME="Exit Node Toggle"
    
    # Create a temporary directory for DMG contents
    DMG_TEMP="dmg_temp"
    rm -rf "$DMG_TEMP"
    mkdir -p "$DMG_TEMP"
    
    # Copy the app
    cp -R "dist/Exit Node Toggle.app" "$DMG_TEMP/"
    
    # Create a symlink to Applications
    ln -s /Applications "$DMG_TEMP/Applications"
    
    # Create README for DMG
    cat > "$DMG_TEMP/README.txt" << 'EOF'
Exit Node Toggle
================

Installation:
1. Drag "Exit Node Toggle.app" to the Applications folder
2. Open the app from Applications
3. Edit config.json in the app bundle to set your exit node IP

Configuration:
- Right-click the app > Show Package Contents
- Navigate to Contents/Resources/config.json
- Set your Tailscale exit node IP

Usage:
- The app will appear in your menu bar (top right)
- Click the icon to see options
- Use "Toggle Exit Node" to switch on/off

Note: Make sure Tailscale is installed and you're logged in.
EOF
    
    # Create the DMG
    hdiutil create -volname "$VOLUME_NAME" \
                   -srcfolder "$DMG_TEMP" \
                   -ov \
                   -format UDZO \
                   "$DMG_NAME"
    
    # Clean up
    rm -rf "$DMG_TEMP"
    
    if [ -f "$DMG_NAME" ]; then
        echo -e "${GREEN}✓ DMG created successfully!${NC}"
        echo "  Location: $DMG_NAME"
    else
        echo -e "${RED}Error: DMG creation failed${NC}"
    fi
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Build complete!${NC}"
echo ""
echo "To run the app:"
echo "  open \"dist/Exit Node Toggle.app\""
echo ""
echo "Remember to configure your exit node IP in:"
echo "  dist/Exit Node Toggle.app/Contents/Resources/config.json"

