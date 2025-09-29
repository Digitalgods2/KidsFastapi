@echo off
REM KidsKlassiks - Start Server (Fixed Version)

echo ========================================
echo Starting KidsKlassiks Server
echo ========================================
echo.

REM Activate virtual environment
if exist venv (
    call venv\Scripts\activate
) else (
    echo ERROR: Virtual environment not found!
    echo Please run: run_migration_fix.bat first
    pause
    exit /b 1
)

REM Check for required files
if not exist main_clean.py (
    echo ERROR: main_clean.py not found!
    echo Please run: run_migration_fix.bat first
    pause
    exit /b 1
)

REM Check for .env file
if not exist .env (
    echo WARNING: .env file not found!
    echo Creating from template...
    if exist .env.example (
        copy .env.example .env
        echo Please edit .env and add your OPENAI_API_KEY
        pause
    ) else (
        echo ERROR: No .env or .env.example found!
        pause
        exit /b 1
    )
)

echo Starting server...
echo Press Ctrl+C to stop
echo.
echo Server will be available at: http://localhost:8000
echo.

REM Start the server
python main_clean.py

pause
