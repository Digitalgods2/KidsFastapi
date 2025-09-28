"""
KidsKlassiks FastAPI + HTMX Application
Clean, working version with all fixes applied
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration and database
import config
from database import initialize_database, get_dashboard_stats, get_all_settings

# Import routers - using fixed versions
from routes.books import router as books_router
from routes.adaptations import router as adaptations_router
from routes.review import router as review_router
from routes.settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting KidsKlassiks FastAPI + HTMX Application...")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        initialize_database()
        logger.info("✅ Database initialized successfully")
        
        # Create necessary directories
        directories = [
            "uploads", 
            "generated_images", 
            "generated_images/chapters",
            "generated_images/covers",
            "publications", 
            "exports", 
            "backups"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        logger.info("📁 Created necessary directories")
        
        # Verify AI services configuration
        if config.OPENAI_API_KEY:
            logger.info("✅ OpenAI API configured")
        else:
            logger.warning("⚠️ OpenAI API not configured - some features will be unavailable")
        
        if config.validate_vertex_ai_config():
            logger.info("✅ Vertex AI configured")
        else:
            logger.info("ℹ️ Vertex AI not configured - using OpenAI only")
        
        logger.info("🌟 KidsKlassiks is ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down KidsKlassiks...")
    logger.info("✅ Cleanup complete")

# Initialize FastAPI app
app = FastAPI(
    title="KidsKlassiks AI Transformer",
    description="Transform classic literature into illustrated children's books using AI",
    version="3.0.0",
    lifespan=lifespan
)

# Middleware configuration
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "kidsklassiks-secret-key-change-in-production")
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

# Include routers with proper prefixes
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(adaptations_router, prefix="/adaptations", tags=["adaptations"])
app.include_router(review_router, prefix="/review", tags=["review"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])

# ==================== HELPER FUNCTIONS ====================

def get_base_context(request: Request) -> dict:
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
    """Landing page"""
    context = get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        context["stats"] = stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        context["stats"] = {
            "total_books": 0,
            "total_adaptations": 0,
            "total_images": 0,
            "recent_books": [],
            "recent_adaptations": []
        }
    
    return templates.TemplateResponse("pages/home.html", context)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page with statistics"""
    context = get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        context["stats"] = stats
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        context["stats"] = {
            "total_books": 0,
            "total_adaptations": 0,
            "total_images": 0,
            "active_books": 0,
            "recent_books": [],
            "recent_adaptations": [],
            "storage_used": "0 MB"
        }
    
    return templates.TemplateResponse("pages/dashboard.html", context)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "version": "3.0.0",
        "environment": config.APP_ENV,
        "services": {
            "database": "connected",
            "openai": "configured" if config.OPENAI_API_KEY else "not_configured",
            "vertex_ai": "configured" if config.validate_vertex_ai_config() else "not_configured"
        }
    })

@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return JSONResponse({
        "name": "KidsKlassiks API",
        "version": "3.0.0",
        "description": "AI-Powered Children's Book Adaptations",
        "architecture": "FastAPI + HTMX",
        "features": [
            "Book import and management",
            "AI-powered text transformation", 
            "Image generation with multiple models",
            "Real-time processing updates",
            "PDF export and publishing"
        ]
    })

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 page"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"error": "Not found", "status_code": 404},
            status_code=404
        )
    
    context = get_base_context(request)
    context.update({
        "error_code": 404,
        "error_message": "Page not found"
    })
    
    return JSONResponse({"error": "Page not found"}, status_code=404)

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 error page"""
    logger.error(f"Internal server error: {exc}")
    
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"error": "Internal server error", "status_code": 500},
            status_code=500
        )
    
    context = get_base_context(request)
    context.update({
        "error_code": 500,
        "error_message": "Internal server error"
    })
    
    return JSONResponse({"error": "Page not found"}, status_code=404)

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 8000))
    host = os.getenv("APP_HOST", "127.0.0.1")
    
    uvicorn.run(
        "main_clean:app", 
        host=host, 
        port=port, 
        reload=config.APP_DEBUG,
        log_level="info" if config.APP_DEBUG else "warning"
    )



