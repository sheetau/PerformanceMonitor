@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo =====================================
echo Performance Monitor Service Builder
echo =====================================
echo.

REM Check administrator privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
) else (
    echo This script must be run as administrator.
    pause
    exit /b 1
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install Python.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python found:
python --version

echo.
echo Installing required packages...
echo.

REM Upgrade pip
python -m pip install --upgrade pip

REM Install required packages
set "packages=flask flask-cors psutil GPUtil pywin32 pyinstaller setuptools"

for %%p in (%packages%) do (
    echo Installing %%p...
    python -m pip install %%p
    if errorlevel 1 (
        echo Failed to install %%p.
        set "failed=1"
    )
)

if defined failed (
    echo.
    echo Some packages failed to install.
    echo Please install them manually and run again.
    pause
    exit /b 1
)

echo.
echo All packages installed successfully.
echo.

REM Clean build directories
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo Building with PyInstaller...
echo.

REM Change to the script's directory before building
cd /d "%~dp0"

REM Build with PyInstaller
pyinstaller --clean performance_monitor.spec

if errorlevel 1 (
    echo.
    echo Build failed.
    echo Please check error logs.
    pause
    exit /b 1
)

echo.
echo Build completed successfully!
echo.

REM Check build result
if exist "dist\PerformanceMonitor.exe" (
    echo Executable file: dist\PerformanceMonitor.exe
    echo.
    echo File size:
    dir "dist\PerformanceMonitor.exe" | find "PerformanceMonitor.exe"
    echo.
    echo Ready for distribution!
    echo.
    echo Usage:
    echo 1. Run PerformanceMonitor.exe
    echo 2. Click "Yes" on UAC prompt
    echo 3. Service will be automatically installed and started
    echo 4. Access data at http://127.0.0.1:5000/performance
    echo.
) else (
    echo Executable file not found. Build may have failed.
)

echo Cleaning up...
if exist "build" rmdir /s /q "build"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo Done!
pause