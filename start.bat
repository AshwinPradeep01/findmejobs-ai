@echo off
title FindMeJobs.ai — Running
echo.
echo  ============================================
echo   FindMeJobs.ai — Starting Server
echo  ============================================
echo.

REM Check virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo  Please run setup.bat first.
    pause
    exit /b 1
)

echo  Activating virtual environment...
call .venv\Scripts\activate.bat

echo  Starting server on http://127.0.0.1:8000 ...
echo.
echo  Opening browser in 3 seconds...
echo  Press Ctrl+C to stop the server.
echo.

REM Open browser after a short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"

REM Start the server (blocks until Ctrl+C)
python -m uvicorn app:app --host 127.0.0.1 --port 8000
