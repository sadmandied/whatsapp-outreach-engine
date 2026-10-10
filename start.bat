@echo off
cd /d "%~dp0"
echo ========================================================
echo  Starting Secure Customer Notification & Outreach Service
echo  URL: http://localhost:4000
echo ========================================================
start http://localhost:4000
node src/server.js
pause
