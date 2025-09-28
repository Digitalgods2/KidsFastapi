"""
Images gallery routes for KidsKlassiks
Handles viewing and managing generated images
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import database_fixed as database
import config

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Helper function for base context
def get_base_context(request):
    """Get base context variables for all templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": config.validate_vertex_ai_config()
    }

@router.get("/", response_class=HTMLResponse)
async def images_gallery(request: Request):
    """Images gallery page - shows all generated images"""
    context = get_base_context(request)
    
    try:
        # Get all generated images
        images = await database.get_generated_images()
        context["images"] = images
        
        # Get some statistics
        adaptations_count = len(set(img.get('adaptation_id') for img in images if img.get('adaptation_id')))
        chapters_count = len(set(img.get('chapter_id') for img in images if img.get('chapter_id')))
        
        context["adaptations_count"] = adaptations_count
        context["chapters_count"] = chapters_count
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_gallery")
        log.error("images_gallery_error", extra={"error": str(e), "component": "routes.images_gallery", "request_id": getattr(request.state, 'request_id', None)})
        context["images"] = []
        context["adaptations_count"] = 0
        context["chapters_count"] = 0
    
    return templates.TemplateResponse("pages/images.html", context)
