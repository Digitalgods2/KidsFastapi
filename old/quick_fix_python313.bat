@echo off
echo 🔧 Quick Fix for Python 3.13 Compatibility Issues
echo ==================================================

REM Activate virtual environment
call venv\Scripts\activate.bat

echo 📦 Installing compatible cryptography version...
pip install cryptography --upgrade --force-reinstall

echo 📦 Installing compatible anyio version...
pip install anyio --upgrade --force-reinstall

echo 📦 Installing other core dependencies...
pip install fastapi uvicorn starlette jinja2 python-multipart python-dotenv itsdangerous
pip install psycopg2-binary aiohttp requests httpx
pip install beautifulsoup4 pillow pandas numpy

echo 🧪 Testing OpenAI installation...
python -c "import openai; print('✅ OpenAI version:', openai.__version__)"

echo 🧪 Testing FastAPI installation...
python -c "import fastapi; print('✅ FastAPI version:', fastapi.__version__)"

echo 🧪 Testing cryptography installation...
python -c "import cryptography; print('✅ Cryptography version:', cryptography.__version__)"

echo ✅ Quick fix complete! Try starting the server now.
echo 🚀 Run: uvicorn main:app --host 127.0.0.1 --port 8000 --reload

pause
