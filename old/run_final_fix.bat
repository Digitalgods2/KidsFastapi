@echo off
echo 🔧 KidsKlassiks Final Comprehensive Fix
echo ======================================

REM Activate virtual environment
call venv\Scripts\activate.bat

echo 🐍 Python version:
python --version

echo 📦 OpenAI version:
python -c "import openai; print('OpenAI version:', openai.__version__)"

echo 🔧 Running final comprehensive fix...
python final_fix.py

echo.
echo 🚀 Testing working server startup...
echo Starting working server (will test for 10 seconds)...

REM Kill any existing python processes
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak > nul

REM Start working server in background
start /b python -m uvicorn main_working:app --host 127.0.0.1 --port 8000 --reload

REM Wait for server to start
timeout /t 8 /nobreak > nul

REM Test server
echo 🌐 Testing working server response...
curl -s http://127.0.0.1:8000/health
if %errorlevel% == 0 (
    echo ✅ Working server is running perfectly!
    echo 🌐 Open http://127.0.0.1:8000 in your browser
    echo 📚 Try http://127.0.0.1:8000/books/library for book management
) else (
    echo ⚠️ Working server may still be starting...
    echo 🌐 Try opening http://127.0.0.1:8000 in your browser
)

echo.
echo 🔄 Working server is running in background
echo 🛑 Press Ctrl+C in the server window to stop
echo.

echo 📝 If working server is good, you can also try the fixed main server:
echo    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
echo.
pause
