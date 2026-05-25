@echo off
echo ========================================
echo   OrderManager - Build EXE
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

echo Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not installed. Installing...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller!
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller ready
echo.

echo Building application...
echo This may take several minutes...
echo.

pyinstaller --clean --name=OrderManager --onefile --windowed --add-data="src;src" --hidden-import=PyQt6 --hidden-import=sqlalchemy --hidden-import=sqlalchemy.ext.declarative --hidden-import=sqlalchemy.orm src\main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build completed successfully!
echo ========================================
echo.
echo EXE file location: dist\OrderManager.exe
echo.
echo To distribute, copy:
echo   - dist\OrderManager.exe
echo   - ordermanager.db (if exists)
echo.
pause
