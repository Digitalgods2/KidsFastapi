@echo off
echo 🚀 KidsKlassiks Legacy OpenAI Setup and Start Script
echo ====================================================

REM Check if virtual environment exists
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install legacy OpenAI version and dependencies
echo 📦 Installing legacy OpenAI version (0.28.1) and dependencies...
pip install openai==0.28.1 --force-reinstall
if errorlevel 1 (
    echo ❌ Failed to install legacy OpenAI version
    pause
    exit /b 1
)

echo 📦 Installing other dependencies...
pip install -r requirements_legacy.txt
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️ .env file not found. Creating from template...
    copy .env.example .env
    echo 📝 Please edit .env file with your API keys before continuing
    echo Press any key to continue after editing .env file...
    pause
)

REM Start the server
echo 🌟 Starting KidsKlassiks server with legacy OpenAI API...
echo 🌐 Server will be available at: http://127.0.0.1:8000
echo 🔄 Press Ctrl+C to stop the server
echo.

uvicorn main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo 🔄 Server stopped
pause
