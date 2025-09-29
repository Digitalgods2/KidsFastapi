@echo off
REM KidsKlassiks Complete Migration Fix
REM This will fix all issues and migrate to the new OpenAI API

echo ========================================
echo KidsKlassiks Complete Migration Fix
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

echo Step 1: Running comprehensive migration fix...
echo.
python comprehensive_migration_fix.py
if errorlevel 1 (
    echo ERROR: Migration fix failed
    pause
    exit /b 1
)

echo.
echo Step 2: Installing dependencies...
echo.

REM Check if virtual environment exists
if exist venv (
    echo Virtual environment found
) else (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install dependencies
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements_clean.txt

echo.
echo ========================================
echo Migration Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure your .env file has your OPENAI_API_KEY
echo 2. Run: start_server.bat
echo    Or manually: python main_clean.py
echo 3. Open: http://localhost:8000
echo.
echo Press any key to exit...
pause >nul
