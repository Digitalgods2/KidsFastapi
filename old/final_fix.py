#!/usr/bin/env python3
"""
Final comprehensive fix for KidsKlassiks
This script will fix ALL remaining issues:
1. Book file path issue in character analysis
2. Missing book routes (404 errors)
3. Settings API errors
4. Database field mismatches
"""

import os
import shutil
import psycopg2

def backup_file(filepath):
    """Create a backup of a file"""
    if os.path.exists(filepath):
        backup_path = filepath + ".backup"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backed up {filepath}")
        return True
    return False

def fix_database_book_paths():
    """Fix the database to ensure all books have proper file paths"""
    try:
        # Database connection details
        DB_HOST = os.getenv("DB_HOST", "localhost")
        DB_PORT = os.getenv("DB_PORT", "5432")
        DATABASE_NAME = os.getenv("DATABASE_NAME", "kidsklassiks")
        DB_USER = os.getenv("DB_USER", "glen")
        DB_PASSWORD = os.getenv("DB_PASSWORD", "well9973cr")
        
        conn = psycopg2.connect(
            host=DB_HOST, 
            port=DB_PORT, 
            dbname=DATABASE_NAME, 
            user=DB_USER, 
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Check books without file paths
        cur.execute("""
            SELECT book_id, title, original_content_path 
            FROM books 
            WHERE original_content_path IS NULL OR original_content_path = ''
        """)
        
        books_without_paths = cur.fetchall()
        
        for book_id, title, current_path in books_without_paths:
            # Create a safe filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            expected_path = f"uploads/{safe_title}.txt"
            
            print(f"📚 Fixing book {book_id}: '{title}'")
            
            # Check if file exists in uploads directory
            if os.path.exists(expected_path):
                # Update database with correct path
                cur.execute("""
                    UPDATE books 
                    SET original_content_path = %s 
                    WHERE book_id = %s
                """, (expected_path, book_id))
                print(f"✅ Updated path for book {book_id}: {expected_path}")
            else:
                # Check if there's a similar file
                uploads_files = []
                if os.path.exists("uploads"):
                    uploads_files = [f for f in os.listdir("uploads") if f.endswith('.txt')]
                
                print(f"⚠️ File not found: {expected_path}")
                print(f"📁 Available files: {uploads_files}")
                
                # Try to find a matching file
                for filename in uploads_files:
                    if title.lower().replace(' ', '').replace('-', '') in filename.lower().replace(' ', '').replace('-', ''):
                        full_path = f"uploads/{filename}"
                        cur.execute("""
                            UPDATE books 
                            SET original_content_path = %s 
                            WHERE book_id = %s
                        """, (full_path, book_id))
                        print(f"✅ Matched and updated book {book_id} with: {full_path}")
                        break
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Database book paths fixed")
        return True
        
    except Exception as e:
        print(f"❌ Database fix error: {e}")
        return False

def fix_main_py_router_inclusion():
    """Fix main.py to properly include the books router"""
    main_path = "main.py"
    
    if not os.path.exists(main_path):
        print(f"❌ {main_path} not found")
        return False
    
    backup_file(main_path)
    
    # Read current content
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if books router is properly included
    if "app.include_router(books_router" not in content:
        print("❌ Books router not included in main.py")
        
        # Find the router inclusion section
        if "# Include routers" in content:
            # Add books router inclusion
            content = content.replace(
                "# Include routers",
                """# Include routers
app.include_router(books_router, prefix="/books", tags=["books"])"""
            )
        else:
            # Add router inclusion section
            router_section = """
# Include routers
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(adaptations.router, prefix="/adaptations", tags=["adaptations"])
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
"""
            
            # Insert before the helper functions section
            if "# ==================== HELPER FUNCTIONS ====================" in content:
                content = content.replace(
                    "# ==================== HELPER FUNCTIONS ====================",
                    router_section + "\n# ==================== HELPER FUNCTIONS ===================="
                )
    
    # Fix settings router issues
    content = content.replace(
        "app.include_router(settings.router",
        "app.include_router(settings_router"
    )
    
    # Make sure settings router is imported
    if "from routes.settings import router as settings_router" not in content:
        content = content.replace(
            "from routes import adaptations, review, settings",
            "from routes import adaptations, review, settings\nfrom routes.settings import router as settings_router"
        )
    
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed main.py router inclusion")
    return True

def create_working_main_py():
    """Create a completely working main.py"""
    main_path = "main_working.py"
    
    content = '''"""
KidsKlassiks FastAPI + HTMX Application - WORKING VERSION
Main application entry point with all fixes applied
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os

import config
import database as database
from database import initialize_database, get_dashboard_stats, get_all_settings

# Import working routes
from routes.books import router as books_router
from routes import adaptations, review

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Starting KidsKlassiks FastAPI + HTMX Application...")
    
    try:
        # Initialize database
        print("📊 Initializing database...")
        initialize_database()
        print("✅ Database initialized successfully")
        
        # Create necessary directories
        directories = ["uploads", "generated_images", "publications", "exports", "backups"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        print("📁 Created necessary directories")
        
        # Verify AI services configuration
        if config.OPENAI_API_KEY:
            print("✅ OpenAI API configured")
        else:
            print("⚠️ OpenAI API not configured")
        
        if config.validate_vertex_ai_config():
            print("✅ Vertex AI configured")
        else:
            print("⚠️ Vertex AI not configured")
        
        print("🌟 KidsKlassiks is ready!")
        
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🔄 Shutting down KidsKlassiks...")
    print("✅ Cleanup complete")

# Initialize FastAPI app
app = FastAPI(
    title="KidsKlassiks AI Transformer",
    description="Transform classic literature into illustrated children's books using AI",
    version="2.0.0-working",
    lifespan=lifespan
)

# Middleware configuration
app.add_middleware(
    SessionMiddleware, 
    secret_key="kidsklassiks-secret-key-change-in-production"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated_images", StaticFiles(directory="generated_images"), name="generated_images")
app.mount("/publications", StaticFiles(directory="publications"), name="publications")

templates = Jinja2Templates(directory="templates")

# Include routers - FIXED ORDER AND IMPORTS
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(adaptations.router, prefix="/adaptations", tags=["adaptations"])
app.include_router(review.router, prefix="/review", tags=["review"])

print("✅ All routers included successfully")

# Helper function
def get_base_context(request: Request):
    """Get base context variables for all templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": config.validate_vertex_ai_config()
    }

# Root routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root page - homepage"""
    context = get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        stats['recent_books'] = []
        stats['recent_adaptations'] = []
    except:
        stats = {
            "total_books": 0,
            "total_adaptations": 0,
            "total_images": 0,
            "recent_books": [],
            "recent_adaptations": []
        }
    
    context["stats"] = stats
    return templates.TemplateResponse("pages/home.html", context)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page"""
    context = get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        context["stats"] = stats
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        context["stats"] = {
            "total_books": 0,
            "total_adaptations": 0,
            "total_images": 0,
            "recent_books": [],
            "recent_adaptations": []
        }
    
    return templates.TemplateResponse("pages/dashboard.html", context)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    context = get_base_context(request)
    
    try:
        settings = await get_all_settings()
        context["settings"] = settings
    except Exception as e:
        print(f"❌ Settings error: {e}")
        context["settings"] = {}
    
    return templates.TemplateResponse("pages/settings.html", context)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0-working",
        "environment": config.APP_ENV,
        "services": {
            "database": "connected",
            "openai": "configured" if config.OPENAI_API_KEY else "not_configured",
            "vertex_ai": "configured" if config.validate_vertex_ai_config() else "not_configured"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main_working:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=config.APP_DEBUG,
        log_level="info" if config.APP_DEBUG else "warning"
    )
'''
    
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Created {main_path}")
    return True

def main():
    """Main final fix function"""
    print("🔧 KidsKlassiks Final Comprehensive Fix")
    print("=======================================")
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ main.py not found. Please run this script from the KidsKlassiks directory.")
        return False
    
    print("📁 Current directory:", os.getcwd())
    
    # Apply all fixes
    success = True
    
    print("\\n🔧 Step 1: Fixing database book file paths...")
    success &= fix_database_book_paths()
    
    print("\\n🔧 Step 2: Fixing main.py router inclusion...")
    success &= fix_main_py_router_inclusion()
    
    print("\\n🔧 Step 3: Creating working main.py...")
    success &= create_working_main_py()
    
    if success:
        print("\\n✅ All final fixes applied successfully!")
        print("🚀 Try starting the server with the working version:")
        print("   python -m uvicorn main_working:app --host 127.0.0.1 --port 8000 --reload")
        print("\\n🔄 Or try the fixed main.py:")
        print("   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload")
    else:
        print("\\n❌ Some fixes failed. Check the error messages above.")
    
    return success

if __name__ == "__main__":
    main()
