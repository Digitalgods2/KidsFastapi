"""
Review routes for KidsKlassiks
Handles review and editing of adaptations
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
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

@router.post("/adaptation/{adaptation_id}/update-cover-prompt")
async def update_cover_prompt(
    adaptation_id: int,
    cover_prompt: str = Form(...)
):
    """Update adaptation cover prompt"""
    try:
        success = await database.update_adaptation_cover_image_prompt_only(adaptation_id, cover_prompt)
        if success:
            return JSONResponse({"success": True, "message": "Cover prompt updated"})
        else:
            raise HTTPException(status_code=400, detail="Failed to update cover prompt")
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("update_cover_prompt_error", extra={"error": str(e), "component": "routes.review", "request_id": None, "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adaptation/{adaptation_id}/generate-cover-prompt")
async def generate_cover_prompt_endpoint(adaptation_id: int):
    """Generate AI-powered cover prompt by analyzing the entire book"""
    try:
        from services.chat_helper import analyze_book_for_cover_prompt
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Read book content
        book_path = book.get("path")
        if not book_path or not os.path.exists(book_path):
            raise HTTPException(status_code=404, detail="Book file not found")
        
        try:
            with open(book_path, 'r', encoding='utf-8') as f:
                book_content = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading book file: {str(e)}")
        
        # Generate cover prompt using AI
        cover_prompt, error = await analyze_book_for_cover_prompt(book_content, book, adaptation)
        
        if error:
            raise HTTPException(status_code=500, detail=f"AI generation failed: {error}")
        
        if not cover_prompt:
            raise HTTPException(status_code=500, detail="AI returned empty cover prompt")
        
        # Save the generated prompt to database
        success = await database.update_adaptation_cover_image_prompt_only(adaptation_id, cover_prompt)
        
        if success:
            return JSONResponse({
                "success": True, 
                "cover_prompt": cover_prompt,
                "message": "AI-generated cover prompt created successfully"
            })
        else:
            raise HTTPException(status_code=500, detail="Failed to save cover prompt")
            
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("generate_cover_prompt_error", extra={"error": str(e), "component": "routes.review", "request_id": None, "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adaptation/{adaptation_id}/generate-cover")
async def generate_cover(adaptation_id: int):
    """Generate cover image for adaptation"""
    try:
        from services.image_generation_service import ImageGenerationService
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Generate cover image
        image_service = ImageGenerationService()
        
        # If there's a custom cover prompt, use it; otherwise use default
        if adaptation.get("cover_prompt"):
            # Get user's preferred API from database, fallback to config
            api_type = await database.get_setting('default_image_backend', config.DEFAULT_IMAGE_MODEL)
            
            # Check if prompt contains text instructions and warn user about Imagen limitations
            cover_prompt = adaptation["cover_prompt"]
            has_text_instructions = any(word in cover_prompt.lower() for word in [
                'title', 'text', 'written by', 'author', 'typography', 'font', 'lettering'
            ])
            
            warning_message = None
            if has_text_instructions and (api_type.startswith('vertex') or api_type.startswith('imagen')):
                from services.logger import get_logger
                log = get_logger("routes.review")
                log.warning("text_with_imagen_warning", extra={
                    "component": "routes.review",
                    "api_type": api_type,
                    "reason": "Cover prompt contains text instructions, but Imagen cannot render text reliably"
                })
                warning_message = ("⚠️ Note: Your prompt includes text instructions (title, author), but Vertex/Imagen "
                                 "models have limited text rendering capabilities. For best results with text on covers, "
                                 "consider using GPT-Image-1 or DALL-E 3 in your settings.")
            
            # Use custom prompt
            result = await image_service.generate_single_image(
                prompt=cover_prompt,
                chapter_id=0,  # 0 for cover
                adaptation_id=adaptation_id,
                api_type=api_type
            )
            
            if result["success"]:
                # Move to per-book directory
                import shutil, os
                book_id = adaptation.get('book_id')
                if book_id:
                    target_dir = os.path.join("generated_images", str(book_id), "chapters")
                else:
                    target_dir = os.path.join("generated_images", "orphaned", "chapters")
                os.makedirs(target_dir, exist_ok=True)

                cover_filename = f"cover_adaptation_{adaptation_id}.png"
                cover_path = os.path.join(target_dir, cover_filename)

                shutil.copy2(result["local_path"], cover_path)

                # Add timestamp to bust browser cache
                import time
                timestamp = int(time.time())
                cover_url = f"/{target_dir}/{cover_filename}?v={timestamp}"
                
                # Update database
                await database.update_adaptation_cover_image(
                    adaptation_id, 
                    adaptation["cover_prompt"], 
                    cover_url
                )
        else:
            # Get user's preferred API from database, fallback to config
            api_type = await database.get_setting('default_image_backend', config.DEFAULT_IMAGE_MODEL)
            
            # Use default cover generation
            result = await image_service.generate_cover_image(
                adaptation_id=adaptation_id,
                title=book.get("title", ""),
                author=book.get("author", ""),
                theme=adaptation.get("overall_theme_tone", ""),
                api_type=api_type
            )
            
            if result["success"]:
                # Update database with default prompt
                cover_prompt = f"Children's book cover for {book.get('title', '')} by {book.get('author', '')}"
                await database.update_adaptation_cover_image(
                    adaptation_id, 
                    cover_prompt, 
                    result["cover_url"]
                )
        
        if result["success"]:
            response_data = {"success": True, "message": "Cover generated successfully"}
            if warning_message:
                response_data["warning"] = warning_message
            return JSONResponse(response_data)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Cover generation failed"))
            
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("generate_cover_error", extra={"error": str(e), "component": "routes.review", "request_id": None, "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adaptation/{adaptation_id}/regenerate-cover")
async def regenerate_cover(adaptation_id: int):
    """Regenerate cover image for adaptation using existing prompt"""
    try:
        from services.image_generation_service import ImageGenerationService
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        if not adaptation.get("cover_prompt"):
            raise HTTPException(status_code=400, detail="No cover prompt found. Please set a cover prompt first.")
        
        # Get user's preferred API from database, fallback to config
        api_type = await database.get_setting('default_image_backend', config.DEFAULT_IMAGE_MODEL)
        
        # Check if prompt contains text instructions and warn user about Imagen limitations
        cover_prompt = adaptation["cover_prompt"]
        has_text_instructions = any(word in cover_prompt.lower() for word in [
            'title', 'text', 'written by', 'author', 'typography', 'font', 'lettering'
        ])
        
        warning_message = None
        if has_text_instructions and (api_type.startswith('vertex') or api_type.startswith('imagen')):
            from services.logger import get_logger
            log = get_logger("routes.review")
            log.warning("text_with_imagen_warning_regenerate", extra={
                "component": "routes.review",
                "api_type": api_type,
                "reason": "Cover prompt contains text instructions, but Imagen cannot render text reliably"
            })
            warning_message = ("⚠️ Note: Your prompt includes text instructions (title, author), but Vertex/Imagen "
                             "models have limited text rendering capabilities. For best results with text on covers, "
                             "consider using GPT-Image-1 or DALL-E 3 in your settings.")
        
        # Generate cover image with existing prompt
        image_service = ImageGenerationService()
        result = await image_service.generate_single_image(
            prompt=cover_prompt,
            chapter_id=0,  # 0 for cover
            adaptation_id=adaptation_id,
            api_type=api_type
        )
        
        if result["success"]:
            # Move to per-book directory
            import shutil, os
            book_id = adaptation.get('book_id')
            if book_id:
                target_dir = os.path.join("generated_images", str(book_id), "chapters")
            else:
                target_dir = os.path.join("generated_images", "orphaned", "chapters")
            os.makedirs(target_dir, exist_ok=True)

            cover_filename = f"cover_adaptation_{adaptation_id}.png"
            cover_path = os.path.join(target_dir, cover_filename)

            shutil.copy2(result["local_path"], cover_path)

            # Add timestamp to bust browser cache
            import time
            timestamp = int(time.time())
            cover_url = f"/{target_dir}/{cover_filename}?v={timestamp}"
            
            # Update database
            await database.update_adaptation_cover_image(
                adaptation_id, 
                adaptation["cover_prompt"], 
                cover_url
            )
            
            response_data = {"success": True, "message": "Cover regenerated successfully", "cover_url": cover_url}
            if warning_message:
                response_data["warning"] = warning_message
            return JSONResponse(response_data)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Cover regeneration failed"))
            
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("regenerate_cover_error", extra={"error": str(e), "component": "routes.review", "request_id": None, "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))