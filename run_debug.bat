@echo off
echo ========================================
echo   OrderManager - Run in Debug Mode
echo ========================================
echo.

cd /d "%~dp0"

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Run install.bat first
    pause
    exit /b 1
)

echo Starting OrderManager in debug mode...
echo.
python src\main.py --debug

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error!
    pause
    exit /b 1
)
