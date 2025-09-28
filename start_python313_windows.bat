@echo off
echo 🚀 KidsKlassiks Python 3.13 Compatible Setup and Start Script
echo ============================================================

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

REM Check Python version
echo 🐍 Checking Python version...
python --version

REM Install legacy OpenAI version first
echo 📦 Installing legacy OpenAI version (0.28.1)...
pip install openai==0.28.1 --force-reinstall
if errorlevel 1 (
    echo ❌ Failed to install legacy OpenAI version
    pause
    exit /b 1
)

REM Install Python 3.13 compatible dependencies
echo 📦 Installing Python 3.13 compatible dependencies...
pip install -r requirements_python313.txt --upgrade
if errorlevel 1 (
    echo ⚠️ Some dependencies may have failed, but continuing...
    echo 📦 Installing core dependencies individually...
    
    REM Install core dependencies one by one
    pip install fastapi==0.104.1
    pip install "uvicorn[standard]==0.24.0"
    pip install starlette==0.27.0
    pip install jinja2==3.1.2
    pip install python-multipart==0.0.6
    pip install python-dotenv==1.0.0
    pip install itsdangerous==2.1.2
    pip install cryptography --upgrade
    pip install psycopg2-binary==2.9.9
    pip install aiohttp --upgrade
    pip install requests --upgrade
    pip install httpx --upgrade
    pip install anyio --upgrade
    pip install beautifulsoup4 --upgrade
    pip install pillow --upgrade
    pip install pandas --upgrade
    pip install numpy --upgrade
    
    echo ✅ Core dependencies installed
)

REM Check if .env file exists
if not exist ".env" (
    echo ⚠️ .env file not found. Creating from template...
    copy .env.example .env
    echo 📝 Please edit .env file with your API keys before continuing
    echo Press any key to continue after editing .env file...
    pause
)

REM Test OpenAI installation
echo 🧪 Testing OpenAI installation...
python -c "import openai; print('✅ OpenAI 0.28.1 imported successfully')"
if errorlevel 1 (
    echo ❌ OpenAI import failed
    pause
    exit /b 1
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
