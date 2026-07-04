@echo off
title FindMeJobs.ai — Setup
echo.
echo  ============================================
echo   FindMeJobs.ai — One-Time Setup
echo  ============================================
echo.

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not on PATH.
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo  [1/4] Creating Python virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo  [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat

echo  [3/4] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies. Check requirements.txt
    pause
    exit /b 1
)

echo  [4/4] Installing Playwright Chromium browser...
playwright install chromium
if errorlevel 1 (
    echo  [ERROR] Failed to install Playwright browsers.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Setup complete!
echo  ============================================
echo.
echo  To start the app, run:  start.bat
echo.
pause
