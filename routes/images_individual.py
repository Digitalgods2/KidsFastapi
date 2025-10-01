"""
Individual Image Generation Routes for KidsKlassiks
Matches the original Streamlit workflow with individual chapter control
"""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import json

import database_fixed as database
import config
from services.image_generation_service import ImageGenerationService
from services.backends import SUPPORTED_BACKENDS, validate_backend

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Request models
class ImagePromptRequest(BaseModel):
    prompt: str
    api_type: Optional[str] = None  # if None, will use default from settings

class GenerateImageRequest(BaseModel):
    prompt: str
    model: Optional[str] = "dall-e-3"
    size: Optional[str] = "1024x1024"
    quality: Optional[str] = "standard"

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

@router.get("/adaptation/{adaptation_id}/chapters")
async def chapter_images_page(request: Request, adaptation_id: int):
    """Individual chapter image generation page"""
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation['book_id'])
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Get chapters
        chapters_raw = await database.get_adaptation_chapters(adaptation_id)
        # Map DB field names to template-expected keys for compatibility
        chapters = []
        for ch in chapters_raw:
            m = dict(ch)
            m["id"] = ch.get("chapter_id")
            m["transformed_chapter_text"] = ch.get("transformed_text")
            m["ai_generated_image_prompt"] = ch.get("ai_prompt")
            m["user_edited_image_prompt"] = ch.get("user_prompt")
            chapters.append(m)
        
        context = get_base_context(request)
        context.update({
            "adaptation": adaptation,
            "book": book,
            "chapters": chapters
        })
        
        return templates.TemplateResponse("pages/chapter_images.html", context)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("chapter_images_page_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-cover-prompt/{adaptation_id}")
async def generate_cover_prompt(adaptation_id: int):
    """Generate AI cover image prompt for adaptation"""
    try:
        # Get adaptation and book details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            return JSONResponse({"success": False, "error": "Adaptation not found"})
        
        book = await database.get_book_details(adaptation['book_id'])
        if not book:
            return JSONResponse({"success": False, "error": "Book not found"})
        
        # Generate cover prompt using modern chat helper
        from services import chat_helper
        prompt, err = await chat_helper.generate_cover_prompt(book, adaptation)
        if not prompt:
            return JSONResponse({"success": False, "error": err or "Failed to generate cover prompt"})
        # Save the prompt to database
        await database.update_adaptation_cover_image_prompt_only(adaptation_id, prompt)
        return JSONResponse({"success": True, "prompt": prompt})
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("generate_cover_prompt_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "adaptation_id": adaptation_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/save-cover-prompt/{adaptation_id}")
async def save_cover_prompt(adaptation_id: int, request: ImagePromptRequest):
    """Save cover image prompt without generating image"""
    try:
        # Validate adaptation exists
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            return JSONResponse({"success": False, "error": "Adaptation not found"})
        
        # Save the prompt to database
        success = await database.update_adaptation_cover_image_prompt_only(adaptation_id, request.prompt)
        
        if success:
            return JSONResponse({"success": True, "message": "Cover prompt saved successfully"})
        else:
            return JSONResponse({"success": False, "error": "Failed to save prompt to database"})
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("save_cover_prompt_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "adaptation_id": adaptation_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/generate-cover-image/{adaptation_id}")
async def generate_cover_image(adaptation_id: int, request: ImagePromptRequest):
    """Generate cover image for adaptation"""
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            return JSONResponse({"success": False, "error": "Adaptation not found"})
        
        # Use the unified ImageGenerationService
        image_service = ImageGenerationService()

        # Resolve backend via central registry and validate
        if request.api_type is not None:
            if not validate_backend(request.api_type):
                raise HTTPException(status_code=400, detail=f"Unsupported image backend: {request.api_type}. Supported: {sorted(list(SUPPORTED_BACKENDS))}")
            backend = request.api_type
        else:
            backend = await database.get_setting("default_image_backend", "dall-e-3")
            if not validate_backend(backend):
                raise HTTPException(status_code=400, detail=f"Unsupported default image backend in settings: {backend}. Supported: {sorted(list(SUPPORTED_BACKENDS))}")

        gen_result = await image_service.generate_single_image(
            prompt=request.prompt,
            chapter_id=0,  # 0 used for cover
            adaptation_id=adaptation_id,
            api_type=backend
        )

        if not gen_result.get("success"):
            return JSONResponse({"success": False, "error": gen_result.get("error", "Generation failed")})

        local_path = gen_result.get("local_path")
        if not local_path:
            return JSONResponse({"success": False, "error": "Image path missing after generation"})

        # Move/Copy image to hierarchical directory structure: /generated_images/{book_id}/covers/
        book_id = adaptation.get('book_id')
        if book_id:
            cover_dir = os.path.join("generated_images", str(book_id), "covers")
        else:
            cover_dir = os.path.join("generated_images", "orphaned", "covers")
        os.makedirs(cover_dir, exist_ok=True)
        cover_filename = f"cover_adaptation_{adaptation_id}.png"
        cover_path = os.path.join(cover_dir, cover_filename)

        import shutil
        shutil.copy2(local_path, cover_path)

        # Update DB with served URL
        cover_url = f"/{cover_dir}/{cover_filename}"
        await database.update_adaptation_cover_image(adaptation_id, request.prompt, cover_url)

        return JSONResponse({
            "success": True,
            "image_url": cover_url,
            "api_type": backend
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("generate_cover_image_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "adaptation_id": adaptation_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/generate-chapter-prompt/{chapter_id}")
async def generate_chapter_prompt(chapter_id: int):
    """Generate AI image prompt for a specific chapter"""
    try:
        # Get chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            return JSONResponse({"success": False, "error": "Chapter not found"})
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(chapter['adaptation_id'])
        if not adaptation:
            return JSONResponse({"success": False, "error": "Adaptation not found"})
        
        # Generate chapter image prompt using modern chat helper
        from services import chat_helper
        # Use transformed_text if available, otherwise fallback to original_text_segment
        transformed_text = chapter.get('transformed_text', '') or chapter.get('original_text_segment', '')
        if not transformed_text:
            return JSONResponse({"success": False, "error": "No text content available for this chapter"})
        prompt, err = await chat_helper.generate_chapter_image_prompt(
            transformed_text=transformed_text,
            chapter_number=chapter['chapter_number'],
            adaptation=adaptation,
        )
        if not prompt:
            return JSONResponse({"success": False, "error": err or "Failed to generate chapter prompt"})
        # Save the prompt to database
        await database.update_chapter_image_prompt(chapter_id, prompt)
        return JSONResponse({"success": True, "prompt": prompt})
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("generate_chapter_prompt_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "chapter_id": chapter_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/generate-chapter-image/{chapter_id}")
async def generate_chapter_image(chapter_id: int, request: ImagePromptRequest):
    """Generate image for a specific chapter"""
    try:
        # Get chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            return JSONResponse({"success": False, "error": "Chapter not found"})
        
        # Resolve backend via central registry and validate
        if request.api_type is not None:
            if not validate_backend(request.api_type):
                raise HTTPException(status_code=400, detail=f"Unsupported image backend: {request.api_type}. Supported: {sorted(list(SUPPORTED_BACKENDS))}")
            backend = request.api_type
        else:
            backend = await database.get_setting("default_image_backend", "dall-e-3")
            if not validate_backend(backend):
                raise HTTPException(status_code=400, detail=f"Unsupported default image backend in settings: {backend}. Supported: {sorted(list(SUPPORTED_BACKENDS))}")

        # Route to appropriate service via central image service
        image_service = ImageGenerationService()
        gen_result = await image_service.generate_single_image(
            prompt=request.prompt,
            chapter_id=chapter_id,
            adaptation_id=chapter['adaptation_id'],
            api_type=backend
        )

        if not gen_result.get("success"):
            return JSONResponse({"success": False, "error": gen_result.get("error", "Generation failed")})

        image_url = gen_result.get("image_url")
        # Guard against missing image URL
        if not image_url:
            return JSONResponse({"success": False, "error": "Failed to generate image"})

        # ImageGenerationService also returns local_path for internal use if needed
        local_path = gen_result.get("local_path")
        if not local_path:
            return JSONResponse({"success": False, "error": "Image path missing after generation"})

        # Persist served URL for consistency with batch flow and templates
        await database.update_chapter_image_url(chapter_id, image_url)

        return JSONResponse({
            "success": True,
            "image_url": image_url
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("generate_chapter_image_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "chapter_id": chapter_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })
@router.post("/save-chapter-prompt/{chapter_id}")
async def save_chapter_prompt(chapter_id: int, request: ImagePromptRequest):
    """Save edited image prompt for a chapter"""
    try:
        # Update the chapter prompt in database
        await database.update_chapter_image_prompt(chapter_id, request.prompt)
        
        return JSONResponse({
            "success": True,
            "message": "Prompt saved successfully"
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("save_chapter_prompt_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "chapter_id": chapter_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/generate-all-prompts/{adaptation_id}")
async def generate_all_prompts(adaptation_id: int):
    """Generate AI image prompts for all chapters in batch"""
    try:
        from services import chat_helper
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            return JSONResponse({"success": False, "error": "Adaptation not found"})
        
        # Get all chapters for this adaptation
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        if not chapters:
            return JSONResponse({"success": False, "error": "No chapters found for this adaptation"})
        
        log.info("batch_prompt_generation_start", extra={
            "component": "routes.images_individual",
            "adaptation_id": adaptation_id,
            "chapter_count": len(chapters)
        })
        
        results = []
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for chapter in chapters:
            chapter_id = chapter.get('chapter_id')
            chapter_number = chapter.get('chapter_number')
            
            # Skip if prompt already exists
            existing_prompt = chapter.get('image_prompt') or chapter.get('ai_generated_image_prompt')
            if existing_prompt:
                log.info("chapter_prompt_exists", extra={
                    "component": "routes.images_individual",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number
                })
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "skipped",
                    "message": "Prompt already exists"
                })
                skipped_count += 1
                continue
            
            # Use transformed_text if available, otherwise fallback to original_text_segment
            text_content = chapter.get('transformed_text', '') or chapter.get('original_text_segment', '')
            if not text_content:
                log.warning("chapter_no_text_content", extra={
                    "component": "routes.images_individual",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number
                })
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "error",
                    "error": "No text content available"
                })
                error_count += 1
                continue
            
            # Generate the prompt
            try:
                prompt, err = await chat_helper.generate_chapter_image_prompt(
                    transformed_text=text_content,
                    chapter_number=chapter_number,
                    adaptation=adaptation,
                )
                
                if prompt and not err:
                    # Save the prompt to database
                    await database.update_chapter_image_prompt(chapter_id, prompt)
                    success_count += 1
                    
                    log.info("chapter_prompt_generated", extra={
                        "component": "routes.images_individual",
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "prompt_length": len(prompt)
                    })
                    
                    results.append({
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "status": "success",
                        "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt
                    })
                else:
                    error_count += 1
                    log.error("chapter_prompt_generation_failed", extra={
                        "component": "routes.images_individual",
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "error": err
                    })
                    
                    results.append({
                        "chapter_id": chapter_id,
                        "chapter_number": chapter_number,
                        "status": "error",
                        "error": err or "Failed to generate prompt"
                    })
                    
            except Exception as e:
                error_count += 1
                log.error("chapter_prompt_generation_exception", extra={
                    "component": "routes.images_individual",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "error": str(e)
                })
                
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "error",
                    "error": str(e)
                })
        
        log.info("batch_prompt_generation_complete", extra={
            "component": "routes.images_individual",
            "adaptation_id": adaptation_id,
            "total_count": len(chapters),
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count
        })
        
        return JSONResponse({
            "success": True,
            "summary": {
                "total": len(chapters),
                "generated": success_count,
                "errors": error_count,
                "skipped": skipped_count
            },
            "results": results
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("batch_prompt_generation_error", extra={
            "error": str(e),
            "component": "routes.images_individual",
            "adaptation_id": adaptation_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/skip-chapter-image/{chapter_id}")
async def skip_chapter_image(chapter_id: int):
    """Mark chapter image as skipped"""
    try:
        # Update chapter status to indicate image was skipped
        await database.update_chapter_status(chapter_id, "image_skipped")
        
        return JSONResponse({
            "success": True,
            "message": "Chapter image skipped"
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("skip_chapter_image_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "chapter_id": chapter_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.delete("/delete-chapter-image/{chapter_id}")
async def delete_chapter_image(chapter_id: int):
    """Delete chapter image"""
    try:
        # Get current chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            return JSONResponse({"success": False, "error": "Chapter not found"})
        
        # Delete the image file if it exists
        if chapter.get('image_url'):
            image_path = chapter['image_url']
            # Convert served URL to filesystem path if needed
            if image_path.startswith('/'):
                image_fs = image_path[1:]
            else:
                image_fs = image_path
            if os.path.exists(image_fs):
                os.remove(image_fs)
                from services.logger import get_logger
                get_logger("routes.images_individual").info("image_deleted", extra={"component":"routes.images_individual","request_id":None,"chapter_id":chapter_id,"image_path":image_fs})
        
        # Remove image URL from database
        await database.update_chapter_image_url(chapter_id, None)
        
        return JSONResponse({
            "success": True,
            "message": "Image deleted successfully"
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("delete_chapter_image_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "chapter_id": chapter_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.post("/regenerate-chapter-image/{chapter_id}")
async def regenerate_chapter_image(chapter_id: int):
    """Regenerate image for a chapter using existing prompt"""
    try:
        # Get chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            return JSONResponse({"success": False, "error": "Chapter not found"})
        
        # Get the current prompt
        prompt = chapter.get('user_edited_image_prompt') or chapter.get('ai_generated_image_prompt')
        if not prompt:
            return JSONResponse({"success": False, "error": "No prompt available for regeneration"})
        
        # Delete old image if it exists
        if chapter.get('image_url') and os.path.exists(chapter['image_url']):
            os.remove(chapter['image_url'])
        
        # Generate new image
        request_data = ImagePromptRequest(prompt=prompt)
        return await generate_chapter_image(chapter_id, request_data)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("regenerate_chapter_image_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "chapter_id": chapter_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

# Batch operations (optional, for convenience)
@router.post("/generate-all-prompts/{adaptation_id}")
async def generate_all_prompts(adaptation_id: int):
    """Generate prompts for all chapters (convenience function)"""
    try:
        # Get all chapters for the adaptation
        chapters = await database.get_adaptation_chapters(adaptation_id)
        
        results = []
        for chapter in chapters:
            try:
                resp = await generate_chapter_prompt(chapter['id'])
                # Determine success from child response
                if isinstance(resp, JSONResponse):
                    payload = resp.body
                    try:
                        data = json.loads(payload)
                    except Exception:
                        data = {}
                    success = bool(data.get("success"))
                    error = data.get("error")
                else:
                    success = True
                    error = None
                results.append({
                    "chapter_id": chapter['id'],
                    "chapter_number": chapter['chapter_number'],
                    "success": success,
                    **({"error": error} if error else {})
                })
            except Exception as e:
                results.append({
                    "chapter_id": chapter['id'],
                    "chapter_number": chapter['chapter_number'],
                    "success": False,
                    "error": str(e)
                })
        
        return JSONResponse({
            "success": True,
            "results": results,
            "message": f"Generated prompts for {len([r for r in results if r['success']])} chapters"
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("generate_all_prompts_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "adaptation_id": adaptation_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })

@router.get("/adaptation/{adaptation_id}/status")
async def get_image_generation_status(adaptation_id: int):
    """Get image generation status for an adaptation with flat fields and stage/timestamps."""
    try:
        # DB is the source of truth for counts
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        total_chapters = len(chapters)
        chapters_with_images = sum(1 for c in chapters if c.get('image_url'))
        chapters_with_prompts = sum(1 for c in chapters if c.get('ai_generated_image_prompt') or c.get('user_edited_image_prompt'))

        # Adaptation details for cover
        adaptation = await database.get_adaptation_details(adaptation_id)
        has_cover = bool(adaptation.get('cover_image_url'))
        has_cover_prompt = bool(adaptation.get('cover_image_prompt'))

        # Stage/run mapping from ImageGenerationService.active_generations
        from services.image_generation_service import ImageGenerationService
        service = ImageGenerationService()
        stage = 'idle'
        stage_detail = None
        run_id = None
        last_update_ts = None
        last_error = None
        if service.active_generations:
            for bid, info in service.active_generations.items():
                if info.get('adaptation_id') == adaptation_id:
                    run_id = bid
                    status = info.get('status', 'processing')
                    stage = {
                        'queued':'queued',
                        'processing':'prompting',
                        'completed':'completed',
                        'failed':'failed'
                    }.get(status, 'prompting')
                    if info.get('completed_at'):
                        last_update_ts = info['completed_at'].isoformat()
                    elif info.get('started_at'):
                        last_update_ts = info['started_at'].isoformat()
                    last_error = info.get('error')
                    break

        completion_percentage = int((chapters_with_images / total_chapters) * 100) if total_chapters > 0 else 0

        return JSONResponse({
            "stage": stage,
            "stage_detail": stage_detail,
            "run_id": run_id,
            "last_update_ts": last_update_ts,
            "total_chapters": total_chapters,
            "chapters_with_prompts": chapters_with_prompts,
            "chapters_with_images": chapters_with_images,
            "has_cover": has_cover,
            "has_cover_prompt": has_cover_prompt,
            "completion_percentage": completion_percentage,
            "images_done": chapters_with_images,
            "last_error": last_error
        })
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.images_individual")
        log.error("get_image_generation_status_error", extra={"error": str(e), "component": "routes.images_individual", "request_id": None, "adaptation_id": adaptation_id})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })