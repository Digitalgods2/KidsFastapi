@echo off
echo ========================================
echo    KidsKlassiks FastAPI + HTMX Server
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo Installing/updating dependencies...
    pip install -r requirements.txt
    echo.
)

REM Check if .env file exists
if not exist ".env" (
    echo.
    echo ⚠️  WARNING: .env file not found!
    echo Please create a .env file with your configuration.
    echo See WINDOWS_SETUP.md for details.
    echo.
    pause
    exit /b 1
)

REM Start the FastAPI server
echo Starting KidsKlassiks server...
echo.
echo 🌟 Server will be available at: http://127.0.0.1:8000
echo 📚 API Documentation at: http://127.0.0.1:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped.
pause
