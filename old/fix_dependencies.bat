@echo off
echo ========================================
echo    KidsKlassiks Dependency Fix Tool
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

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install core dependencies one by one
echo Installing core FastAPI dependencies...
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0

echo Installing session middleware...
pip install itsdangerous==2.1.2
pip install cryptography==41.0.8
pip install starlette==0.27.0

echo Installing template engine...
pip install jinja2==3.1.2

echo Installing file upload support...
pip install python-multipart==0.0.6

echo Installing environment variables...
pip install python-dotenv==1.0.0

echo Installing database support...
pip install psycopg2-binary==2.9.9
pip install sqlalchemy==2.0.23

echo Installing AI services...
pip install openai==1.3.7
pip install aiohttp==3.9.1

echo Installing remaining dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo Testing installation...
echo ========================================

REM Test critical imports
python -c "import fastapi; print('✅ FastAPI OK')" 2>nul || echo "❌ FastAPI failed"
python -c "import uvicorn; print('✅ Uvicorn OK')" 2>nul || echo "❌ Uvicorn failed"
python -c "import itsdangerous; print('✅ itsdangerous OK')" 2>nul || echo "❌ itsdangerous failed"
python -c "import starlette; print('✅ Starlette OK')" 2>nul || echo "❌ Starlette failed"
python -c "import jinja2; print('✅ Jinja2 OK')" 2>nul || echo "❌ Jinja2 failed"
python -c "import psycopg2; print('✅ PostgreSQL OK')" 2>nul || echo "❌ PostgreSQL failed"
python -c "import openai; print('✅ OpenAI OK')" 2>nul || echo "❌ OpenAI failed"

echo.
echo ========================================
echo Dependency installation complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure PostgreSQL is running
echo 2. Configure your .env file
echo 3. Run start_windows.bat to start the server
echo.
pause
