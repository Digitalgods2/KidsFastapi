@echo off
echo 🔧 KidsKlassiks Comprehensive OpenAI Fix
echo =======================================

REM Activate virtual environment
call venv\Scripts\activate.bat

echo 🐍 Python version:
python --version

echo 📦 OpenAI version:
python -c "import openai; print('OpenAI version:', openai.__version__)"

echo 🔧 Running comprehensive fix...
python comprehensive_fix.py

echo.
echo 🚀 Testing simple server startup...
echo Starting simple server (will test for 10 seconds)...

REM Start simple server in background
start /b python -m uvicorn main_simple:app --host 127.0.0.1 --port 8000 --reload

REM Wait for server to start
timeout /t 8 /nobreak > nul

REM Test server
echo 🌐 Testing simple server response...
curl -s http://127.0.0.1:8000/health
if %errorlevel% == 0 (
    echo ✅ Simple server is working!
    echo 🌐 Open http://127.0.0.1:8000 in your browser
) else (
    echo ⚠️ Simple server may still be starting...
    echo 🌐 Try opening http://127.0.0.1:8000 in your browser
)

echo.
echo 🔄 Simple server is running in background
echo 🛑 Press Ctrl+C in the server window to stop
echo.

echo 📝 If simple server works, you can also try the fixed main server:
echo    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
echo.
pause
