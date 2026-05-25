@echo off
echo ========================================
echo   OrderManager - Initialize Database
echo ========================================
echo.

cd /d "%~dp0"

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

echo Initializing database...
echo This will create all tables and default settings
echo.

python src\main.py --init-db

if errorlevel 1 (
    echo.
    echo [ERROR] Database initialization failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Database initialized successfully!
echo ========================================
echo.
echo Database file: data\central.db
echo.
pause
