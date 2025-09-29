@echo off
echo 🔧 KidsKlassiks Import Issues Fix
echo =================================

REM Activate virtual environment
call venv\Scripts\activate.bat

echo 🧪 Testing imports to identify issues...
python test_imports.py

echo.
echo 🔧 Attempting to fix import issues...

echo 📝 Backing up original main.py...
copy main.py main_original.py

echo 📝 Using minimal main.py to avoid import conflicts...
copy main_minimal.py main.py

echo 🧪 Testing minimal application startup...
echo Starting server for 10 seconds to test...
timeout /t 3 /nobreak > nul
start /b python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

echo Waiting 10 seconds for server to start...
timeout /t 10 /nobreak > nul

echo 🌐 Testing server response...
curl -s http://127.0.0.1:8000/health > nul
if %errorlevel% == 0 (
    echo ✅ Server is responding successfully!
    echo 🌐 Application available at: http://127.0.0.1:8000
) else (
    echo ❌ Server is not responding
)

echo.
echo 🔄 Server is running in background
echo 🌐 Open http://127.0.0.1:8000 in your browser
echo 🛑 Press Ctrl+C in the server window to stop
echo.
pause
