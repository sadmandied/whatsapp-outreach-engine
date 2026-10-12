@echo off
title WhatsApp Safe Outreach - Setup & Installation
cd /d "%~dp0"
echo ===================================================
echo     Installing Dependencies for WhatsApp Outreach
echo ===================================================
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Creating Desktop & App Shortcuts with Custom Icon...
powershell -NoProfile -ExecutionPolicy Bypass -File create_shortcut.ps1
echo.
echo ===================================================
echo [OK] Installation completed successfully!
echo.
echo - To launch the Modern Desktop GUI: double-click 'WhatsApp Outreach Engine.lnk'
echo   or 'run_gui.bat'
echo - To launch the Command-Line CLI:   double-click 'run_auto_outreach.bat'
echo ===================================================
pause
