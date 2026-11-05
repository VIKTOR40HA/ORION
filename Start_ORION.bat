
@echo off
title ORION AI Launcher

cd /d "%USERPROFILE%\Desktop\Orion"

echo.
echo =====================================
echo       ORION AI - STARTING
echo =====================================
echo.

if not exist ".venv313\Scripts\python.exe" (
    echo ERROR: Python environment not found.
    echo Check the .venv313 folder.
    pause
    exit /b 1
)

start "" http://127.0.0.1:8000/chat-ui

".venv313\Scripts\python.exe" -m uvicorn app.main:app --app-dir python --host 127.0.0.1 --port 8000

echo.
echo ORION has stopped.
pause
