@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10 first.
    pause
    exit /b 1
)

echo Starting Image-to-SVG converter ...
python run.py
if errorlevel 1 (
    echo.
    echo [ERROR] Start failed. Make sure a "libs" folder exists and Python is 3.10.
    pause
    exit /b 1
)
