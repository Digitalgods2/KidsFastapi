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
    """Images gallery page - shows all generated images with filtering"""
    context = get_base_context(request)
    
    try:
        # Get all generated images
        all_images = await database.get_generated_images()
        
        # Get filter parameters
        filter_book = request.query_params.get('book')
        filter_adaptation = request.query_params.get('adaptation')
        
        # Apply filters
        images = all_images
        if filter_book:
            images = [img for img in images if str(img.get('book_id')) == filter_book]
        if filter_adaptation:
            images = [img for img in images if str(img.get('adaptation_id')) == filter_adaptation]
        
        context["images"] = images
        context["filter_book"] = filter_book
        context["filter_adaptation"] = filter_adaptation
        
        # Get unique books and adaptations for filter dropdowns
        books = {}
        adaptations = {}
        for img in all_images:
            book_id = img.get('book_id')
            adaptation_id = img.get('adaptation_id')
            if book_id and book_id not in books:
                # Format import date if available
                book_imported = img.get('book_imported', '')
                import_date = ''
                if book_imported:
                    # Extract date portion (YYYY-MM-DD)
                    import_date = book_imported[:10] if len(book_imported) >= 10 else book_imported
                
                books[book_id] = {
                    'id': book_id,
                    'title': img.get('book_title', f'Book {book_id}'),
                    'author': img.get('book_author', ''),
                    'imported_at': import_date
                }
            if adaptation_id and adaptation_id not in adaptations:
                # Format adaptation created date if available
                adaptation_created = img.get('adaptation_created', '')
                created_date = ''
                if adaptation_created:
                    # Extract date portion (YYYY-MM-DD)
                    created_date = adaptation_created[:10] if len(adaptation_created) >= 10 else adaptation_created
                
                adaptations[adaptation_id] = {
                    'id': adaptation_id,
                    'book_title': img.get('book_title', ''),
                    'target_age': img.get('target_age_group', ''),
                    'style': img.get('transformation_style', '')[:50] + '...' if img.get('transformation_style', '') else '',
                    'created_at': created_date
                }
        
        context["available_books"] = list(books.values())
        context["available_adaptations"] = list(adaptations.values())
        
        # Get some statistics
        books_count = len(books)
        adaptations_count = len(set(img.get('adaptation_id') for img in all_images if img.get('adaptation_id')))
        chapters_count = len(set(img.get('chapter_id') for img in images if img.get('chapter_id')))
        
        context["books_count"] = books_count
        context["adaptations_count"] = adaptations_count
        context["chapters_count"] = chapters_count
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_gallery")
        log.error("images_gallery_error", extra={"error": str(e), "component": "routes.images_gallery", "request_id": getattr(request.state, 'request_id', None)})
        context["images"] = []
        context["available_books"] = []
        context["available_adaptations"] = []
        context["books_count"] = 0
        context["adaptations_count"] = 0
        context["chapters_count"] = 0
    
    return templates.TemplateResponse("pages/images.html", context)
