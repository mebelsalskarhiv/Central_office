@echo off
echo ========================================
echo   OrderManager - System Check
echo ========================================
echo.

cd /d "%~dp0"

set ERROR=0

echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not found!
    set ERROR=1
) else (
    python --version
    echo [OK] Python installed
)
echo.

echo [2/5] Checking pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [X] pip not found!
    set ERROR=1
) else (
    echo [OK] pip installed
)
echo.

echo [3/5] Checking requirements.txt...
if exist requirements.txt (
    echo [OK] requirements.txt found
) else (
    echo [X] requirements.txt not found!
    set ERROR=1
)
echo.

echo [4/5] Checking installed packages...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [X] PyQt6 not installed
    set ERROR=1
) else (
    echo [OK] PyQt6 installed
)

python -c "import sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo [X] SQLAlchemy not installed
    set ERROR=1
) else (
    echo [OK] SQLAlchemy installed
)
echo.

echo [5/5] Checking project structure...
if exist src\main.py (
    echo [OK] src\main.py found
) else (
    echo [X] src\main.py not found!
    set ERROR=1
)

if exist src\database\database.py (
    echo [OK] src\database\database.py found
) else (
    echo [X] src\database\database.py not found!
    set ERROR=1
)

if exist src\gui\main_window.py (
    echo [OK] src\gui\main_window.py found
) else (
    echo [X] src\gui\main_window.py not found!
    set ERROR=1
)
echo.

echo ========================================
if %ERROR%==1 (
    echo   Status: ERRORS FOUND
    echo ========================================
    echo.
    echo Run install.bat to install dependencies
) else (
    echo   Status: ALL CHECKS PASSED
    echo ========================================
    echo.
    echo System ready!
    echo Run run.bat to start application
)
echo.
pause
