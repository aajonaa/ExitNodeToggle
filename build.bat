@echo off
echo ========================================
echo  Building Exit Node Toggle EXE
echo ========================================
echo.

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building executable...
echo.

pyinstaller --onefile --windowed --name "ExitNodeToggle" --add-data "config.json;." main.py

echo.
echo ========================================
echo  Build complete!
echo  EXE location: dist\ExitNodeToggle.exe
echo ========================================
echo.
echo NOTE: Copy config.json to the same folder as the EXE
echo.
pause

