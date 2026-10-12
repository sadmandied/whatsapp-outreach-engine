@echo off
title WhatsApp Outreach - Build Standalone EXE
cd /d "%~dp0"
echo ===================================================
echo   Building Standalone Windows Executable (.exe)
echo ===================================================
echo.
echo Installing PyInstaller...
python -m pip install pyinstaller
echo.
echo Compiling app_gui.py into dist\WhatsApp-Outreach...
pyinstaller --noconfirm --onedir --windowed --name "WhatsApp-Outreach" --icon "assets\icon.ico" --add-data "assets;assets" --collect-all customtkinter --collect-all playwright app_gui.py
echo.
echo ===================================================
echo [OK] Build complete!
echo Your standalone application is in:
echo   dist\WhatsApp-Outreach\WhatsApp-Outreach.exe
echo ===================================================
pause
