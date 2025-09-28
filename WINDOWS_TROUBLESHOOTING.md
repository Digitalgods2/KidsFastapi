# Windows Troubleshooting Guide

## 🚨 Common Issues and Solutions

### Issue 1: ModuleNotFoundError: No module named 'itsdangerous'

**Problem:** Missing dependencies in the virtual environment.

**Solution:**
```cmd
# Activate virtual environment
venv\Scripts\activate

# Update pip first
python -m pip install --upgrade pip

# Install missing dependency
pip install itsdangerous==2.1.2

# Or reinstall all requirements
pip install -r requirements.txt --force-reinstall
```

### Issue 2: Import Errors for Other Modules

**Problem:** Incomplete dependency installation.

**Solution:**
```cmd
# Activate virtual environment
venv\Scripts\activate

# Install core FastAPI dependencies
pip install fastapi[all] uvicorn[standard]

# Install session middleware dependencies
pip install itsdangerous cryptography starlette

# Install database dependencies
pip install psycopg2-binary sqlalchemy

# Install AI service dependencies
pip install openai google-cloud-aiplatform aiohttp

# Install all requirements
pip install -r requirements.txt
```

### Issue 3: PostgreSQL Connection Issues

**Problem:** Database connection fails.

**Solution:**
```cmd
# Check if PostgreSQL service is running
services.msc
# Look for "postgresql-x64-xx" and start it

# Test connection
psql -U postgres -h localhost
```

**Check .env file:**
```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=kidsklassiks
DATABASE_USER=glen
DATABASE_PASSWORD=your_actual_password
```

### Issue 4: Port Already in Use

**Problem:** Port 8000 is already occupied.

**Solution:**
```cmd
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace 1234 with actual PID)
taskkill /PID 1234 /F

# Or use a different port
uvicorn main:app --port 8001
```

### Issue 5: Python Path Issues

**Problem:** Python not found or wrong version.

**Solution:**
```cmd
# Check Python version
python --version

# If not found, use full path
C:\Users\YourName\AppData\Local\Programs\Python\Python313\python.exe --version

# Add to PATH or use full path in commands
```

### Issue 6: Virtual Environment Issues

**Problem:** Virtual environment not working properly.

**Solution:**
```cmd
# Delete existing venv
rmdir /s venv

# Create new virtual environment
python -m venv venv

# Activate
venv\Scripts\activate

# Verify activation (should show (venv))
echo %VIRTUAL_ENV%

# Install dependencies
pip install -r requirements.txt
```

### Issue 7: Permission Errors

**Problem:** Access denied errors.

**Solution:**
```cmd
# Run Command Prompt as Administrator
# Right-click Command Prompt -> "Run as administrator"

# Or change directory permissions
# Right-click folder -> Properties -> Security -> Edit
```

### Issue 8: SSL Certificate Errors

**Problem:** SSL errors when installing packages.

**Solution:**
```cmd
# Upgrade pip and certificates
python -m pip install --upgrade pip
pip install --upgrade certifi

# Use trusted hosts if needed
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## 🔧 Complete Fresh Installation

If you're having multiple issues, try a complete fresh installation:

### Step 1: Clean Installation
```cmd
# Navigate to project directory
cd C:\Users\gosmo\OneDrive\Desktop\Kids3

# Remove virtual environment
rmdir /s venv

# Remove any cached files
del /s *.pyc
rmdir /s __pycache__
```

### Step 2: Create New Environment
```cmd
# Create virtual environment
python -m venv venv

# Activate
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip
```

### Step 3: Install Dependencies Step by Step
```cmd
# Install core FastAPI
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0

# Install session dependencies
pip install itsdangerous==2.1.2
pip install starlette==0.27.0

# Install template engine
pip install jinja2==3.1.2

# Install multipart for file uploads
pip install python-multipart==0.0.6

# Install environment variables
pip install python-dotenv==1.0.0

# Install database
pip install psycopg2-binary==2.9.9

# Install AI services
pip install openai==1.3.7

# Install async HTTP
pip install aiohttp==3.9.1

# Install all remaining
pip install -r requirements.txt
```

### Step 4: Test Installation
```cmd
# Test imports
python -c "import fastapi; print('FastAPI OK')"
python -c "import uvicorn; print('Uvicorn OK')"
python -c "import itsdangerous; print('itsdangerous OK')"
python -c "import psycopg2; print('PostgreSQL OK')"
python -c "import openai; print('OpenAI OK')"

# Start server
uvicorn main:app --reload
```

## 🔍 Debugging Commands

### Check Python Environment
```cmd
# Check Python version
python --version

# Check pip version
pip --version

# Check installed packages
pip list

# Check virtual environment
echo %VIRTUAL_ENV%

# Check current directory
cd
```

### Check Dependencies
```cmd
# Check specific package
pip show fastapi
pip show itsdangerous
pip show psycopg2-binary

# Check for conflicts
pip check
```

### Check System
```cmd
# Check PostgreSQL service
sc query postgresql-x64-15

# Check port usage
netstat -ano | findstr :8000

# Check Python path
where python
```

## 📞 Quick Fix Commands

Copy and paste these commands in order:

```cmd
# Quick fix for missing itsdangerous
venv\Scripts\activate
pip install itsdangerous==2.1.2 cryptography==41.0.8 starlette==0.27.0
uvicorn main:app --reload
```

If that doesn't work:

```cmd
# Nuclear option - reinstall everything
venv\Scripts\activate
pip uninstall -y -r requirements.txt
pip install -r requirements.txt --force-reinstall
uvicorn main:app --reload
```

## 🆘 Still Having Issues?

1. **Check the console output** for specific error messages
2. **Verify .env file** has correct database credentials
3. **Ensure PostgreSQL is running** and accessible
4. **Try running as Administrator** if permission issues persist
5. **Check antivirus software** isn't blocking Python or the application

Most issues are resolved by ensuring the virtual environment is properly activated and all dependencies are correctly installed.
