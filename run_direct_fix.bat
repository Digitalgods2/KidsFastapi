@echo off
echo 🔧 KidsKlassiks Direct Fix
echo ========================

REM Activate virtual environment
call venv\Scripts\activate.bat

echo 🐍 Python version:
python --version

echo 📦 OpenAI version:
python -c "import openai; print('OpenAI version:', openai.__version__)"

echo 🔧 Running direct fix...
python direct_fix.py

echo.
echo 🚀 Testing server startup...
echo Starting server (will stop automatically after 15 seconds)...

REM Start server in background and test
start /b python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

REM Wait for server to start
timeout /t 5 /nobreak > nul

REM Test server
echo 🌐 Testing server response...
curl -s http://127.0.0.1:8000/health
if %errorlevel% == 0 (
    echo ✅ Server is working!
    echo 🌐 Open http://127.0.0.1:8000 in your browser
) else (
    echo ⚠️ Server may still be starting...
    echo 🌐 Try opening http://127.0.0.1:8000 in your browser
)

echo.
echo 🔄 Server is running in background
echo 🛑 Press Ctrl+C in the server window to stop
echo.
pause
