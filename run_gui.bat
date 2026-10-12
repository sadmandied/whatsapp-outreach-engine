@echo off
title WhatsApp Safe Outreach - Desktop GUI
cd /d "%~dp0"

:: Auto-generate desktop & project shortcut with custom icon if missing
if not exist "WhatsApp Outreach Engine.lnk" (
    powershell -NoProfile -ExecutionPolicy Bypass -File create_shortcut.ps1 >nul 2>&1
)

echo Launching Modern Desktop GUI...
python app_gui.py
if errorlevel 1 (
    echo.
    echo [!] An error occurred. Press any key to view...
    pause
)
