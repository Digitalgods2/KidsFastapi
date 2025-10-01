"""
KidsKlassiks FastAPI + HTMX Application
Main application entry point with FastAPI setup and routing
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.gzip import GZipMiddleware

import uvicorn
import os

import config
import database_fixed as database
from database_fixed import initialize_database, get_dashboard_stats, get_all_settings
from routes import adaptations, review, settings, publish
from routes.books import router as books_router
from routes.chapters import router as chapters_router
from routes.images_individual import router as images_router
from routes.images_gallery import router as images_gallery_router
from routes.images import router as images_status_router
from routes.health import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    from services.logger import get_logger
    _log = get_logger("main")
    _log.info("startup")
    
    try:
        # Initialize database
        _log.info("db_init_start")
        initialize_database()
        try:
            from database_fixed import get_sqlite_path, ensure_aux_tables
            ensure_aux_tables()
            _log.info(f"DB -> {get_sqlite_path()}")
        except Exception:
            pass
        _log.info("db_init_ok")
        
        # Create necessary directories
        directories = [
            "uploads",
            "generated_images",
            "generated_images/chapters",
            "generated_images/covers",
            "publications",
            "exports",
            "backups",
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        _log.info("dirs_ready", extra={"dirs": directories})
        
        # Verify AI services configuration
        if config.OPENAI_API_KEY:
            _log.info("openai_configured")
        else:
            _log.warning("openai_not_configured")
        
        if config.validate_vertex_ai_config():
            _log.info("vertex_configured")
        else:
            _log.warning("vertex_not_configured")

        # Validate default image backend from DB settings (fail fast)
        try:
            from services.backends import validate_backend
            default_backend = await database.get_setting("default_image_backend", "dall-e-3")
            if not validate_backend(default_backend):
                raise RuntimeError(f"Invalid default_image_backend in DB: {default_backend}")
            _log.info("default_image_backend", extra={"backend": default_backend})
        except Exception as ve:
            _log.error("startup_validation_error", extra={"error": str(ve)})
            raise
        
        _log.info("ready")
        
    except Exception as e:
        _log.error("startup_failed", extra={"error": str(e)})
        raise
    
    yield
    
    # Shutdown
    _log.info("shutdown")
    _log.info("cleanup_complete")

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
# Enable gzip for production-like responses
app.add_middleware(GZipMiddleware, minimum_size=512)

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

# Cache headers for generated images (1 day)
@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    try:
        path = request.url.path or ""
        if path.startswith("/generated_images/") and response.status_code == 200:
            # Let StaticFiles set correct content-type; we add cache headers
            response.headers["Cache-Control"] = "public, max-age=86400"
        return response
    except Exception:
        return response

templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(adaptations.router, prefix="/adaptations", tags=["adaptations"])
app.include_router(chapters_router, prefix="/chapters", tags=["chapters"])
app.include_router(review.router, prefix="/review", tags=["review"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(publish.router, prefix="/publish", tags=["publish"])
app.include_router(images_router, prefix="/images", tags=["images"])
app.include_router(images_status_router, prefix="/images", tags=["images-status"])  # mounts legacy alias and generation_status
app.include_router(images_gallery_router, prefix="/gallery", tags=["gallery"])
app.include_router(health_router, tags=["ops"])

# ==================== HELPER FUNCTIONS ====================

async def get_base_context(request: Request):
    """Get base context variables for all templates"""
    # Check database for current API key settings instead of config module
    try:
        openai_key = await database.get_setting("openai_api_key", config.OPENAI_API_KEY or "")
        vertex_project_id = await database.get_setting("vertex_project_id", config.VERTEX_PROJECT_ID or "")
        vertex_location = await database.get_setting("vertex_location", config.VERTEX_LOCATION or "us-central1")
        
        # Check if OpenAI is configured (API key exists and starts with sk-)
        openai_configured = bool(openai_key and openai_key.startswith('sk-'))
        
        # Check if Vertex AI is configured (has project ID)
        vertex_configured = bool(vertex_project_id and vertex_project_id.strip())
        
    except Exception:
        # Fallback to config module if database read fails
        openai_configured = bool(config.OPENAI_API_KEY)
        vertex_configured = config.validate_vertex_ai_config()
    
    return {
        "request": request,
        "notifications_count": 0,
        "request_id": getattr(request.state, 'request_id', None),
        "notifications": [],
        "openai_status": openai_configured,
        "vertex_status": vertex_configured
    }

# Request ID middleware (HF3)
from services.logger import set_request_id, reset_request_id
from starlette.middleware.base import BaseHTTPMiddleware
import uuid as _uuid


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID") or _uuid.uuid4().hex
        token = set_request_id(rid)
        setattr(request.state, "request_id", rid)
        try:
            response = await call_next(request)
        finally:
            reset_request_id(token)
        response.headers["X-Request-ID"] = rid
        return response


# Register middleware once
app.add_middleware(RequestIdMiddleware)

# ==================== ROOT ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root page - homepage"""
    context = await get_base_context(request)
    
    # Add homepage specific stats
    try:
        stats = await get_dashboard_stats()
        # Add placeholder data for recent items (can be implemented later)
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

@app.get("/dashboard")
async def dashboard(request: Request):
    """Dashboard page"""
    context = await get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        
        # Get recent books (last 5)
        recent_books = await database.get_recent_books(limit=5)
        stats['recent_books'] = recent_books
        
        # Get recent adaptations (last 5)
        recent_adaptations = await database.get_recent_adaptations(limit=5)
        stats['recent_adaptations'] = recent_adaptations
        
        # Get adaptation status counts
        adaptation_stats = await database.get_adaptation_status_counts()
        stats['completed_adaptations'] = adaptation_stats.get('completed', 0)
        stats['in_progress_adaptations'] = adaptation_stats.get('in_progress', 0)
        
        # Calculate storage used (rough estimate)
        storage_mb = await database.get_storage_usage()
        stats['storage_used'] = f"{storage_mb}MB"
        
        # AI service status
        stats['openai_status'] = bool(config.OPENAI_API_KEY)
        stats['vertex_status'] = config.validate_vertex_ai_config()
        
    except Exception as e:
        from services.logger import get_logger
        get_logger("main").error("dashboard_error", extra={"error": str(e)})
        stats = {
            "total_books": 0,
            "total_adaptations": 0,
            "active_books": 0,
            "total_images": 0,
            "recent_books": [],
            "recent_adaptations": [],
            "completed_adaptations": 0,
            "in_progress_adaptations": 0,
            "storage_used": "0MB",
            "openai_status": bool(config.OPENAI_API_KEY),
            "vertex_status": config.validate_vertex_ai_config()
        }
    
    context["stats"] = stats
    return templates.TemplateResponse("pages/dashboard.html", context)

# Settings route is now handled by the settings router

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": config.APP_ENV,
        "services": {
            "database": "connected",
            "openai": "configured" if config.OPENAI_API_KEY else "not_configured",
            "vertex_ai": "configured" if config.validate_vertex_ai_config() else "not_configured"
        }
    }

@app.get("/healthz")
async def healthz():
    """Comprehensive health probe covering DB, chat_helper, and image backends.
    Non-invasive: avoids external network calls.
    """
    from services.chat_helper import get_client
    from services.backends import validate_backend
    import traceback

    status = {
        "status": "ok",
        "version": "2.0.0",
        "environment": config.APP_ENV,
        "checks": {
            "database": {"ok": False, "error": None},
            "chat": {"ok": False, "error": None},
            "image_backend": {"ok": False, "default_backend": None, "error": None},
        },
    }

    # DB probe: simple settings read
    try:
        _ = await database.get_setting("default_image_backend", "dall-e-3")
        status["checks"]["database"]["ok"] = True
    except Exception as e:
        status["status"] = "degraded"
        status["checks"]["database"]["error"] = str(e)

    # Chat probe: instantiate client only
    try:
        _ = await get_client()
        status["checks"]["chat"]["ok"] = True
    except Exception as e:
        status["checks"]["chat"]["error"] = str(e)
        status["status"] = "degraded"

    # Image backend probe: validate configured default only
    try:
        default_backend = await database.get_setting("default_image_backend", "dall-e-3")
        status["checks"]["image_backend"]["default_backend"] = default_backend
        if validate_backend(default_backend):
            status["checks"]["image_backend"]["ok"] = True
        else:
            status["checks"]["image_backend"]["error"] = f"invalid_default_backend:{default_backend}"
            status["status"] = "degraded"
    except Exception as e:
        status["checks"]["image_backend"]["error"] = str(e)
        status["status"] = "degraded"

    return status


@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return {
        "name": "KidsKlassiks API",
        "version": "2.0.0",
        "description": "AI-Powered Children's Book Adaptations",
        "architecture": "FastAPI + HTMX",
        "features": [
            "Book import and management",
            "AI-powered text transformation", 
            "Image generation with multiple models",
            "Real-time processing updates",
            "PDF export and publishing"
        ]
    }

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 page"""
    if request.url.path.startswith("/api/"):
        return {"error": "Not found", "status_code": 404}
    
    context = await get_base_context(request)
    context.update({
        "error_code": 404,
        "error_message": "Page not found"
    })
    
    return templates.TemplateResponse(
        "layouts/base.html", 
        context,
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 page"""
    if config.APP_DEBUG:
        print(f"❌ Internal error: {exc}")
    
    if request.url.path.startswith("/api/"):
        return {"error": "Internal server error", "status_code": 500}
    
    context = await get_base_context(request)
    context.update({
        "error_code": 500,
        "error_message": "Internal server error"
    })
    

@app.get("/_debug/db")
async def debug_db():
    """Return current DB configuration and file info.
    Always safe. Useful to verify pinned SQLite path across restarts.
    """
    try:
        from database_fixed import get_database_debug
        return get_database_debug()
    except Exception as e:
        return {"error": str(e), "cwd": os.getcwd()}

    return templates.TemplateResponse(
        "layouts/base.html",
        context,
        status_code=500
    )

# ==================== DEVELOPMENT ROUTES ====================

if config.APP_DEBUG:
    @app.get("/debug/config")
    async def debug_config():
        """Debug configuration endpoint (development only)"""
        return {
            "app_env": config.APP_ENV,
            "debug": config.APP_DEBUG,
            "database_configured": bool(config.DATABASE_NAME),
            "openai_configured": bool(config.OPENAI_API_KEY),
            "vertex_configured": config.validate_vertex_ai_config()
        }

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=config.APP_DEBUG,
        log_level="info" if config.APP_DEBUG else "warning"
    )