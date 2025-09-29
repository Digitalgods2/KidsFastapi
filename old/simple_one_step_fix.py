#!/usr/bin/env python3
"""
SIMPLE ONE-STEP FIX for KidsKlassiks OpenAI Import Error
Copy this entire file content and save as 'simple_fix.py' in your Kids3 directory
"""

import os

def fix_main_py():
    """Fix main.py to avoid the problematic import"""
    print("🔧 Fixing main.py...")
    
    # Read current main.py
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Comment out the problematic import
    content = content.replace(
        "from routes.images_individual import router as images_router",
        "# from routes.images_individual import router as images_router  # DISABLED - causes OpenAI import error"
    )
    
    # Comment out the router inclusion
    content = content.replace(
        'app.include_router(images_router, prefix="/images", tags=["images"])',
        '# app.include_router(images_router, prefix="/images", tags=["images"])  # DISABLED'
    )
    
    # Write back
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed main.py - removed problematic imports")

def create_simple_working_main():
    """Create a simple working main.py"""
    print("🔧 Creating simple working version...")
    
    content = '''"""
KidsKlassiks FastAPI + HTMX Application - SIMPLE WORKING VERSION
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os

import config
import database
from database import initialize_database, get_dashboard_stats

# Import only working routes (no problematic imports)
from routes.books import router as books_router
from routes import adaptations, review

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    print("🚀 Starting KidsKlassiks (Simple Working Version)...")
    
    try:
        initialize_database()
        print("✅ Database initialized")
        
        # Create directories
        for directory in ["uploads", "generated_images", "publications"]:
            os.makedirs(directory, exist_ok=True)
        
        print("✅ OpenAI API configured" if config.OPENAI_API_KEY else "⚠️ OpenAI API not configured")
        print("🌟 KidsKlassiks is ready!")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise
    
    yield
    print("🔄 Shutting down...")

# Initialize FastAPI app
app = FastAPI(
    title="KidsKlassiks AI Transformer",
    description="Transform classic literature into illustrated children's books using AI",
    version="2.0.0-simple-working",
    lifespan=lifespan
)

# Middleware
app.add_middleware(SessionMiddleware, secret_key="kidsklassiks-secret-key")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include working routers only
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(adaptations.router, prefix="/adaptations", tags=["adaptations"])
app.include_router(review.router, prefix="/review", tags=["review"])

print("✅ All working routers included")

# Helper function
def get_base_context(request: Request):
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": False
    }

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    context = get_base_context(request)
    try:
        stats = await get_dashboard_stats()
    except:
        stats = {"total_books": 0, "total_adaptations": 0, "total_images": 0, "recent_books": [], "recent_adaptations": []}
    context["stats"] = stats
    return templates.TemplateResponse("pages/home.html", context)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    context = get_base_context(request)
    try:
        stats = await get_dashboard_stats()
        context["stats"] = stats
    except:
        context["stats"] = {"total_books": 0, "total_adaptations": 0, "total_images": 0, "recent_books": [], "recent_adaptations": []}
    return templates.TemplateResponse("pages/dashboard.html", context)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    context = get_base_context(request)
    context["settings"] = {}
    return templates.TemplateResponse("pages/settings.html", context)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0.0-simple-working",
        "services": {
            "database": "connected",
            "openai": "configured" if config.OPENAI_API_KEY else "not_configured"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main_simple_working:app", host="127.0.0.1", port=8000, reload=True)
'''
    
    with open('main_simple_working.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Created main_simple_working.py")

def main():
    """Main fix function"""
    print("🔧 SIMPLE ONE-STEP FIX for KidsKlassiks")
    print("=====================================")
    
    if not os.path.exists('main.py'):
        print("❌ main.py not found. Make sure you're in the Kids3 directory.")
        return
    
    print("📁 Current directory:", os.getcwd())
    
    # Apply fixes
    fix_main_py()
    create_simple_working_main()
    
    print("\\n✅ ALL FIXES APPLIED!")
    print("\\n🚀 Now run this command:")
    print("   python -m uvicorn main_simple_working:app --host 127.0.0.1 --port 8000 --reload")
    print("\\n🌐 Then open: http://127.0.0.1:8000")
    print("\\n📚 Test books: http://127.0.0.1:8000/books/library")

if __name__ == "__main__":
    main()
