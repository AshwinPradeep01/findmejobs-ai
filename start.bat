@echo off
title FindMeJobs.ai — Running
echo.
echo  ============================================
echo   FindMeJobs.ai — Starting Server
echo  ============================================
echo.

REM Check virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo  [ERROR] Virtual environment not found.
    echo  Please run setup.bat first.
    pause
    exit /b 1
)

echo  Starting server on http://127.0.0.1:8000 ...
echo.
echo  Opening browser in 3 seconds...
echo  Press Ctrl+C to stop the server.
echo.

REM Open browser after a short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"

REM Start the server using the venv python interpreter
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000

