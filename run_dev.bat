@echo off
echo ===================================================
echo   AutoSOL Trading Bot - Development Launcher
echo ===================================================

echo [1/2] Starting Backend Server (Flask)...
start "AutoSOL Backend" cmd /k "python app/main.py"

echo [2/2] Starting Frontend Server (Vite)...
cd frontend
start "AutoSOL Frontend" cmd /k "npm run dev"

echo.
echo ===================================================
echo   Services are starting in separate windows.
echo   Backend: http://127.0.0.1:5000
echo   Frontend: http://localhost:5173
echo ===================================================
pause
