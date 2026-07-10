@echo off
echo =========================================================
echo Starting Pay-In Automation Dashboard (Version 1)...
echo =========================================================

echo Starting Backend API Server (Port 8000)...
start "Pay-In Backend API" cmd /k "uvicorn backend.app.main:app --port 8000"

echo Starting Frontend Dev Server (Port 5173)...
start "Pay-In Frontend Client" cmd /k "cd frontend && npm run dev"

echo =========================================================
echo Both servers have been launched in separate windows.
echo =========================================================
pause
