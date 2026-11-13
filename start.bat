@echo off
cd /d "%~dp0"
set "PATH=C:\Program Files\nodejs;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

echo ========================================================
echo   TechPay Programmatic SEO Directory - Launcher
echo ========================================================
echo.

echo [1/2] Ensuring SQLite database ^& SEO pages are populated...
call node database.js
call python pipeline.py

echo.
echo [2/2] Starting Express Server on http://localhost:3000 ...
echo Public Directory: http://localhost:3000
echo Admin Dashboard:  http://localhost:3000/admin/login (Password: admin123)
echo.
call node server.js
pause
