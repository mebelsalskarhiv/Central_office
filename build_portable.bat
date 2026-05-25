@echo off
REM Скрипт создания portable bundle для OrderManager Central Office

echo ========================================
echo OrderManager Central Office - Portable Bundle Creator
echo ========================================
echo.

set BUNDLE_DIR=OrderManager_Portable
set PYTHON_VERSION=3.12.9
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip

echo Step 1: Creating bundle directory...
if exist "%BUNDLE_DIR%" rmdir /s /q "%BUNDLE_DIR%"
mkdir "%BUNDLE_DIR%"

echo.
echo Step 2: Downloading Python embeddable package...
echo URL: %PYTHON_EMBED_URL%
curl -L -o python-embed.zip %PYTHON_EMBED_URL%
if errorlevel 1 (
    echo ERROR: Failed to download Python embeddable package
    pause
    exit /b 1
)

echo.
echo Step 3: Extracting Python...
powershell -Command "Expand-Archive -Path python-embed.zip -DestinationPath %BUNDLE_DIR% -Force"
del python-embed.zip

echo.
echo Step 4: Configuring Python paths...
cd "%BUNDLE_DIR%"
powershell -Command "(Get-Content python312._pth) -replace '#import site', 'import site' | Set-Content python312._pth"
cd ..

echo.
echo Step 5: Installing pip...
curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
"%BUNDLE_DIR%\python.exe" get-pip.py
del get-pip.py

echo.
echo Step 6: Installing dependencies...
"%BUNDLE_DIR%\python.exe" -m pip install PyQt6 PyQt6-WebEngine sqlalchemy pillow openpyxl webdavclient3 python-dateutil folium matplotlib

echo.
echo Step 7: Copying application files...
xcopy /E /I /Y src "%BUNDLE_DIR%\src"
xcopy /E /I /Y database "%BUNDLE_DIR%\database"
xcopy /E /I /Y gui "%BUNDLE_DIR%\gui"
xcopy /E /I /Y sync "%BUNDLE_DIR%\sync"
copy /Y central_office.ico "%BUNDLE_DIR%\"

echo.
echo Step 8: Creating data directories...
mkdir "%BUNDLE_DIR%\data"
mkdir "%BUNDLE_DIR%\data\images"
mkdir "%BUNDLE_DIR%\data\webdav"
mkdir "%BUNDLE_DIR%\data\backups"

echo.
echo Step 9: Building launcher with icon...
pyinstaller --clean launcher.spec
if exist "dist\OrderManager.exe" (
    copy /Y "dist\OrderManager.exe" "%BUNDLE_DIR%\"
    echo Launcher created successfully!
) else (
    echo WARNING: Launcher build failed, creating BAT file instead
    (
    echo @echo off
    echo cd /d "%%~dp0"
    echo start "" "%%~dp0python.exe" src\main.py
    ) > "%BUNDLE_DIR%\OrderManager.bat"
)

echo.
echo Step 10: Creating README...
(
echo OrderManager Central Office - Portable Bundle
echo =============================================
echo.
echo This is a portable version of OrderManager Central Office.
echo.
echo To run:
echo - Double-click OrderManager.exe
echo.
echo System Requirements:
echo - Windows 10 or later
echo - No Python installation required
echo.
echo The application stores its database in the 'data' folder.
echo.
echo First Run:
echo 1. Launch OrderManager.exe
echo 2. The database will be created automatically
echo 3. Configure WebDAV settings in the Settings tab
echo.
echo Data Folders:
echo - data/images - Product images
echo - data/webdav - WebDAV sync files
echo - data/backups - Database backups
echo.
echo Version: 1.0.0
echo Date: 2026-05-03
) > "%BUNDLE_DIR%\README.txt"

echo.
echo ========================================
echo PORTABLE BUNDLE CREATED SUCCESSFULLY!
echo ========================================
echo.
echo Location: %BUNDLE_DIR%\
echo Size:
dir "%BUNDLE_DIR%" | find "File(s)"
echo.
echo To run: %BUNDLE_DIR%\OrderManager.exe
echo.
pause
