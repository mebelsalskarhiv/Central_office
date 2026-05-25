@echo off
echo ========================================
echo   OrderManager - Clean Temp Files
echo ========================================
echo.

cd /d "%~dp0"

echo Removing temporary build files...

if exist build (
    echo Removing build\...
    rmdir /s /q build
)

if exist dist (
    echo Removing dist\...
    rmdir /s /q dist
)

if exist __pycache__ (
    echo Removing __pycache__\...
    rmdir /s /q __pycache__
)

if exist *.spec (
    echo Removing *.spec...
    del /q *.spec
)

echo Removing __pycache__ in subdirectories...
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo Removing *.pyc files...
del /s /q *.pyc >nul 2>&1

echo.
echo ========================================
echo   Cleanup completed!
echo ========================================
echo.
pause
