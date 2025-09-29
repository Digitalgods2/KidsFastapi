@echo off
echo 🔄 Restarting KidsKlassiks Server with Fixes
echo ==========================================

REM Activate virtual environment
call venv\Scripts\activate.bat

echo 🛑 Stopping any existing server processes...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak > nul

echo 🚀 Starting server with all fixes applied...
echo 📍 Server will be available at: http://127.0.0.1:8000
echo.

REM Start the server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo 🛑 Server stopped
pause
