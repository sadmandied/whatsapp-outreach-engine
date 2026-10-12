@echo off
title Create Desktop Shortcut - WhatsApp Outreach
cd /d "%~dp0"
echo ===================================================
echo   Creating WhatsApp Outreach App Shortcut
echo ===================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File create_shortcut.ps1
echo.
echo ===================================================
echo [OK] Done! You can now launch WhatsApp Outreach from
echo      your Desktop or project folder using the icon.
echo ===================================================
pause
