"""
Publish routes for KidsKlassiks
Handles PDF export and publishing functionality
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
import database_fixed as database
import config
import os

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
async def publish_page(request: Request):
    """Publish page - shows all adaptations with content statistics"""
    context = get_base_context(request)
    
    try:
        # Get all adaptations with content statistics (chapters, images, word count)
        all_adaptations = await database.get_all_adaptations_with_stats()
        context["adaptations"] = all_adaptations
        
        # Add timestamp for cache-busting
        import time
        context["cache_timestamp"] = int(time.time())
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.publish")
        log.error("publish_page_error", extra={"error": str(e), "component": "routes.publish", "request_id": getattr(request.state, 'request_id', None)})
        context["adaptations"] = []
    
    return templates.TemplateResponse("pages/publish.html", context)

@router.get("/adaptation/{adaptation_id}")
async def publish_adaptation(request: Request, adaptation_id: int):
    """Publish a specific adaptation as PDF"""
    context = get_base_context(request)
    
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_by_id(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        context["adaptation"] = adaptation
        
        # Add timestamp for cache-busting
        import time
        context["cache_timestamp"] = int(time.time())
        
        return templates.TemplateResponse("pages/publish_adaptation.html", context)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.publish")
        log.error("publish_adaptation_error", extra={"error": str(e), "component": "routes.publish", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/chapters/{adaptation_id}")
async def get_adaptation_chapters_api(adaptation_id: int):
    """Get chapters for an adaptation - JSON API"""
    try:
        # Get chapters from database
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        
        return {"success": True, "chapters": chapters}
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.publish")
        log.error("get_chapters_api_error", extra={"error": str(e), "component": "routes.publish", "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/export/{adaptation_id}")
async def export_adaptation_pdf(request: Request, adaptation_id: int):
    """Export adaptation as PDF and return file for download"""
    try:
        from services.pdf_generator import PDFGenerator
        
        # Get adaptation details
        adaptation = await database.get_adaptation_by_id(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation['book_id'])
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Get chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        if not chapters:
            return {"success": False, "message": "No chapters found for this adaptation"}
        
        # Map database fields to PDF generator expected fields
        adapted_adaptation = {
            **adaptation,
            'cover_image_url': adaptation.get('cover_url')  # Map cover_url to cover_image_url
        }
        
        adapted_chapters = []
        for ch in chapters:
            adapted_chapters.append({
                **ch,
                # Map transformed_text -> transformed_chapter_text (use original if transformed is empty)
                'transformed_chapter_text': ch.get('transformed_text') or ch.get('original_text_segment', ''),
                # Also provide original_chapter_text as fallback
                'original_chapter_text': ch.get('original_text_segment', '')
            })
        
        # Generate PDF
        pdf_generator = PDFGenerator()
        file_path, error = await pdf_generator.generate_adaptation_pdf(
            adaptation=adapted_adaptation,
            book=book,
            chapters=adapted_chapters,
            include_images=True
        )
        
        if error or not file_path:
            from services.logger import get_logger
            log = get_logger("routes.publish")
            log.error("pdf_generation_failed", extra={"error": error, "component": "routes.publish", "adaptation_id": adaptation_id})
            raise HTTPException(status_code=500, detail=error or "PDF generation failed")
        
        # Return file for download
        filename = os.path.basename(file_path)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.publish")
        log.error("export_adaptation_pdf_error", extra={"error": str(e), "component": "routes.publish", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))
