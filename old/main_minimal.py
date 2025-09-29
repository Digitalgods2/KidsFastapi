"""
KidsKlassiks FastAPI + HTMX Application - MINIMAL VERSION
Main application entry point with minimal imports to avoid OpenAI conflicts
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

# Import database functions directly
try:
    from database import initialize_database, get_dashboard_stats, get_all_settings
    print("✅ Database functions imported successfully")
except Exception as e:
    print(f"❌ Database import failed: {e}")

# Import routes individually to avoid conflicts
try:
    from routes.books import router as books_router
    print("✅ Books router imported successfully")
except Exception as e:
    print(f"❌ Books router import failed: {e}")
    books_router = None

try:
    from routes.images_individual import router as images_router
    print("✅ Images router imported successfully")
except Exception as e:
    print(f"❌ Images router import failed: {e}")
    images_router = None

# Import other routes safely
try:
    from routes.adaptations import router as adaptations_router
    print("✅ Adaptations router imported successfully")
except Exception as e:
    print(f"❌ Adaptations router import failed: {e}")
    adaptations_router = None

try:
    from routes.review import router as review_router
    print("✅ Review router imported successfully")
except Exception as e:
    print(f"❌ Review router import failed: {e}")
    review_router = None

try:
    from routes.settings import router as settings_router
    print("✅ Settings router imported successfully")
except Exception as e:
    print(f"❌ Settings router import failed: {e}")
    settings_router = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Starting KidsKlassiks FastAPI + HTMX Application (Minimal Version)...")
    
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
    version="2.0.0",
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

# Include routers only if they imported successfully
if books_router:
    app.include_router(books_router, prefix="/books", tags=["books"])
    print("✅ Books router included")

if adaptations_router:
    app.include_router(adaptations_router, prefix="/adaptations", tags=["adaptations"])
    print("✅ Adaptations router included")

if review_router:
    app.include_router(review_router, prefix="/review", tags=["review"])
    print("✅ Review router included")

if settings_router:
    app.include_router(settings_router, prefix="/settings", tags=["settings"])
    print("✅ Settings router included")

if images_router:
    app.include_router(images_router, prefix="/images", tags=["images"])
    print("✅ Images router included")

# ==================== HELPER FUNCTIONS ====================

def get_base_context(request: Request):
    """Get base context variables for all templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": config.validate_vertex_ai_config()
    }

# ==================== ROOT ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root page - homepage"""
    context = get_base_context(request)
    
    # Add homepage specific stats
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0-minimal",
        "environment": config.APP_ENV,
        "services": {
            "database": "connected",
            "openai": "configured" if config.OPENAI_API_KEY else "not_configured",
            "vertex_ai": "configured" if config.validate_vertex_ai_config() else "not_configured"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main_minimal:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=config.APP_DEBUG,
        log_level="info" if config.APP_DEBUG else "warning"
    )
