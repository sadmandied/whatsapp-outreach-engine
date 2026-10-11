@echo off
title WhatsApp Safe Outreach - Desktop GUI
cd /d "%~dp0"
echo Launching Modern Desktop GUI...
python app_gui.py
if errorlevel 1 (
    echo.
    echo [!] An error occurred. Press any key to view...
    pause
)
