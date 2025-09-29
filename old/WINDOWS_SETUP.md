# KidsKlassiks - Windows 11 Setup Guide

## 🚀 Quick Start for Windows 11

This guide will help you set up and run the KidsKlassiks FastAPI + HTMX application on Windows 11.

## 📋 Prerequisites

### 1. Python 3.11+
Download and install Python from [python.org](https://www.python.org/downloads/)
- ✅ Make sure to check "Add Python to PATH" during installation
- ✅ Verify installation: `python --version`

### 2. PostgreSQL Database
Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/downloads/windows/)
- ✅ Remember your postgres user password
- ✅ Default port: 5432

### 3. Git (Optional)
Download from [git-scm.com](https://git-scm.com/download/win) if you want to clone the repository

## 🛠️ Installation Steps

### Step 1: Set up the project directory
```cmd
# Create project directory
mkdir C:\KidsKlassiks
cd C:\KidsKlassiks

# Copy all project files to this directory
```

### Step 2: Create virtual environment
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# You should see (venv) in your command prompt
```

### Step 3: Install Python dependencies
```cmd
# Install required packages
pip install fastapi uvicorn jinja2 python-multipart
pip install psycopg2-binary sqlalchemy
pip install openai google-cloud-aiplatform
pip install aiohttp requests beautifulsoup4
pip install python-dotenv

# Or install from requirements.txt if provided
pip install -r requirements.txt
```

### Step 4: Set up PostgreSQL database
```cmd
# Connect to PostgreSQL (replace 'your_password' with your postgres password)
psql -U postgres -h localhost

# In PostgreSQL shell:
CREATE USER glen WITH PASSWORD 'your_password_here';
CREATE DATABASE kidsklassiks OWNER glen;
GRANT ALL PRIVILEGES ON DATABASE kidsklassiks TO glen;
\q
```

### Step 5: Configure environment variables
Create a `.env` file in your project root:

```env
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=kidsklassiks
DATABASE_USER=glen
DATABASE_PASSWORD=your_password_here

# OpenAI Configuration (Required)
OPENAI_API_KEY=your_openai_api_key_here

# Google Vertex AI Configuration (Optional)
VERTEX_PROJECT_ID=your_google_cloud_project_id
VERTEX_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json

# Application Settings
APP_ENV=development
APP_DEBUG=true
SECRET_KEY=your-secret-key-change-in-production
```

### Step 6: Update file paths for Windows
The application uses OS-agnostic paths with `os.path.join()` and `pathlib.Path`, but verify these key files:

**config.py** - Should automatically detect Windows paths
**database.py** - Uses relative paths that work on Windows
**services/** - All file operations use `os.path.join()` for cross-platform compatibility

## 🏃‍♂️ Running the Application

### Start the development server
```cmd
# Make sure virtual environment is activated
venv\Scripts\activate

# Start the FastAPI server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Or use the direct command
uvicorn main:app --reload
```

### Access the application
Open your web browser and go to:
- **Main Application**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health

## 📁 Project Structure

```
KidsKlassiks/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── database.py            # Database operations
├── models.py              # Data models
├── .env                   # Environment variables (create this)
├── requirements.txt       # Python dependencies
├── routes/                # API endpoints
│   ├── __init__.py
│   ├── books.py          # Book management routes
│   ├── adaptations.py    # Adaptation processing routes
│   ├── images.py         # Image generation routes
│   ├── review.py         # Review and editing routes
│   └── settings.py       # Settings management routes
├── services/              # Business logic services
│   ├── __init__.py
│   ├── openai_service.py         # OpenAI API integration
│   ├── vertex_service.py         # Google Vertex AI integration
│   ├── transformation_service.py # Text transformation logic
│   ├── image_generation_service.py # Image generation workflow
│   ├── text_processing.py       # Text processing utilities
│   └── pdf_generator.py         # PDF export functionality
├── templates/             # HTML templates
│   ├── layouts/
│   │   └── base.html     # Base template
│   ├── pages/            # Page templates
│   └── components/       # Reusable components
├── static/               # Static assets
│   ├── css/
│   ├── js/
│   └── images/
├── uploads/              # Uploaded book files
├── generated_images/     # AI-generated images
├── publications/         # Published books
└── exports/             # Exported files
```

## 🔧 Windows-Specific Configuration

### File Path Handling
The application automatically handles Windows file paths using:
- `os.path.join()` for path construction
- `pathlib.Path()` for modern path handling
- Forward slashes in templates (web-compatible)

### Directory Creation
Windows directories are created automatically:
```python
os.makedirs("uploads", exist_ok=True)
os.makedirs("generated_images", exist_ok=True)
os.makedirs("publications", exist_ok=True)
```

### Database Connection
PostgreSQL connection string for Windows:
```
postgresql://glen:password@localhost:5432/kidsklassiks
```

## 🚨 Troubleshooting

### Common Issues on Windows

**1. Python not found**
```cmd
# Add Python to PATH or use full path
C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe
```

**2. PostgreSQL connection issues**
```cmd
# Check if PostgreSQL service is running
services.msc
# Look for "postgresql-x64-xx" service and start it
```

**3. Port already in use**
```cmd
# Find process using port 8000
netstat -ano | findstr :8000
# Kill the process (replace PID with actual process ID)
taskkill /PID 1234 /F
```

**4. Permission issues**
- Run Command Prompt as Administrator
- Check antivirus software isn't blocking Python

**5. Module import errors**
```cmd
# Ensure virtual environment is activated
venv\Scripts\activate
# Reinstall packages if needed
pip install --force-reinstall fastapi uvicorn
```

## 🔑 API Keys Setup

### OpenAI API Key (Required)
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create an account and get your API key
3. Add to `.env` file: `OPENAI_API_KEY=sk-...`

### Google Vertex AI (Optional)
1. Create a Google Cloud Project
2. Enable Vertex AI API
3. Create a service account and download JSON key
4. Set environment variable or add to `.env`

## 🎯 Testing the Installation

### 1. Health Check
```cmd
curl http://127.0.0.1:8000/health
```

### 2. Import a Book
1. Go to http://127.0.0.1:8000/books/import
2. Upload a text file (try the included Peter Pan.txt)
3. Create an adaptation
4. Process chapters
5. Generate images

### 3. Check Logs
Monitor the console output for any errors or warnings.

## 📞 Support

If you encounter issues:
1. Check the console output for error messages
2. Verify all environment variables are set correctly
3. Ensure PostgreSQL is running and accessible
4. Check that all Python packages are installed
5. Verify file permissions in the project directory

## 🔄 Updates and Maintenance

### Updating Dependencies
```cmd
# Activate virtual environment
venv\Scripts\activate

# Update packages
pip install --upgrade fastapi uvicorn openai

# Or update all packages
pip freeze > requirements.txt
pip install --upgrade -r requirements.txt
```

### Database Migrations
The application automatically creates necessary database tables on startup. For manual database management, use the PostgreSQL command line tools or pgAdmin.

---

**Ready to transform classic literature into magical children's stories! 🌟**
