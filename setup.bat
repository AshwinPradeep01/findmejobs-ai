@echo off
setlocal enabledelayedexpansion
title FindMeJobs.ai — Setup
echo.
echo  ============================================
echo   FindMeJobs.ai — One-Time Setup
echo  ============================================
echo.

REM Determine which Python command to use (prefer 3.12/3.11 if available, otherwise default python/py)
set "PYTHON_CMD="

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto :python_found
)

py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto :python_found
)

py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.13"
    goto :python_found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)

echo  [ERROR] Python is not installed or not found on PATH.
echo  Please install Python (recommended 3.11 or 3.12) from https://www.python.org/downloads/
echo  Make sure to check "Add Python to PATH" during installation.
pause
exit /b 1

:python_found
echo  Using Python interpreter: %PYTHON_CMD%
%PYTHON_CMD% --version

REM Clean up any pre-existing broken .venv if python executable is missing or corrupt
if exist ".venv" (
    if not exist ".venv\Scripts\python.exe" (
        echo  [INFO] Detected broken or incomplete .venv. Removing it...
        rmdir /s /q .venv
    )
)

echo.
echo  [1/4] Creating Python virtual environment...
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv --copies .venv
    if errorlevel 1 (
        echo  [WARN] Standard venv creation encountered an issue. Retrying with --without-pip...
        if exist ".venv" rmdir /s /q .venv
        %PYTHON_CMD% -m venv --without-pip --copies .venv
        if errorlevel 1 (
            echo  [ERROR] Failed to create virtual environment.
            echo  Note: Python 3.13 has known venvlauncher issues on some Windows systems.
            echo  Consider installing Python 3.11 or 3.12.
            pause
            exit /b 1
        )
        echo  [INFO] Bootstrapping pip into virtual environment...
        ".venv\Scripts\python.exe" -m ensurepip --upgrade
    )
) else (
    echo  [INFO] Existing valid virtual environment found.
)

REM Verify python.exe exists in .venv
if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] Virtual environment python executable not found at .venv\Scripts\python.exe
    pause
    exit /b 1
)

echo.
echo  [2/4] Verifying and upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet

echo.
echo  [3/4] Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies. Check requirements.txt
    pause
    exit /b 1
)

echo.
echo  [4/4] Installing Playwright Chromium browser...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo  [ERROR] Failed to install Playwright browser binaries.
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
