"""
Review routes for KidsKlassiks
Handles review and editing of adaptations
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
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

@router.get("/adaptation/{adaptation_id}", response_class=HTMLResponse)
async def review_adaptation(request: Request, adaptation_id: int):
    """Review adaptation page"""
    context = get_base_context(request)
    
    try:
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        book = await database.get_book_details(adaptation["book_id"])
        
        context.update({
            "adaptation": adaptation,
            "chapters": chapters,
            "book": book
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("review_page_error", extra={"error": str(e), "component": "routes.review", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))
    
    return templates.TemplateResponse("pages/review_adaptation.html", context)

@router.post("/chapter/{chapter_id}/update")
async def update_chapter(
    chapter_id: int,
    transformed_text: str = Form(...),
    image_prompt: str = Form(...)
):
    """Update chapter text and prompt"""
    try:
        success = await database.update_chapter(chapter_id, transformed_text, image_prompt)
        if success:
            return JSONResponse({"success": True, "message": "Chapter updated"})
        else:
            raise HTTPException(status_code=400, detail="Failed to update chapter")
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("update_chapter_error", extra={"error": str(e), "component": "routes.review", "request_id": None, "chapter_id": chapter_id})
        raise HTTPException(status_code=500, detail=str(e))