"""
Image generation routes for KidsKlassiks
Handles batch image generation and progress tracking
"""

from fastapi import APIRouter, Request, Form, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from typing import Optional
import asyncio
import json
from datetime import datetime

import database_fixed as database
from services.image_generation_service import ImageGenerationService

router = APIRouter()
templates = Jinja2Templates(directory="templates")
image_service = ImageGenerationService()

# Helper function for base context
def get_base_context(request):
    """Get base context variables for all templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": True,  # Will be updated with actual config
        "vertex_status": True   # Will be updated with actual config
    }

@router.post("/{adaptation_id}/generate_batch")
async def generate_images_batch(
    request: Request,
    adaptation_id: int,
    background_tasks: BackgroundTasks,
    image_api: Optional[str] = Form(None),
    generate_cover: bool = Form(False)
):
    """
    DEPRECATED: Batch image generation is no longer supported.
    Images should be generated one at a time through the unified review interface.
    This endpoint redirects to the review page.
    """
    # Return deprecation notice
    from services.logger import get_logger
    get_logger("routes.images").warning("batch_image_generation_deprecated", extra={
        "adaptation_id": adaptation_id
    })
    
    if request.headers.get("HX-Request"):
        # HTMX response
        return HTMLResponse(f"""
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Batch Image Generation Deprecated</strong>
                <p>Images should now be generated one at a time through the unified review interface.</p>
                <a href="/adaptations/{adaptation_id}/review" class="btn btn-primary mt-2">
                    Go to Review Page
                </a>
            </div>
        """)
    
    return JSONResponse({
        "success": False,
        "deprecated": True,
        "message": "Batch image generation is deprecated. Use the unified review interface.",
        "redirect": f"/adaptations/{adaptation_id}/review"
    }, status_code=410)  # 410 Gone
    
    # Original code below is preserved but unreachable
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        if not chapters:
            raise HTTPException(status_code=400, detail="No chapters found for this adaptation")
        
        # Resolve backend: request value or settings default
        if not image_api:
            get_setting_fn = getattr(database, "get_setting", None)
            if asyncio.iscoroutinefunction(get_setting_fn):
                image_api = await get_setting_fn("default_image_backend", "dall-e-3")
            elif callable(get_setting_fn):
                image_api = get_setting_fn("default_image_backend", "dall-e-3")
            else:
                image_api = "dall-e-3"

        # Enforce sensible batch caps
        import os
        MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "50"))
        total = len(chapters)
        if total > MAX_BATCH_SIZE:
            raise HTTPException(status_code=400, detail=f"Batch too large: {total} > {MAX_BATCH_SIZE}")

        # Create a batch and return its ID immediately
        job_id = image_service.create_batch(adaptation_id, total)

        # Start batch generation in background (use same job_id)
        from services.logger import wrap_async_bg
        req_id = getattr(request.state, 'request_id', None)
        background_tasks.add_task(
            wrap_async_bg(_process_batch_generation, req_id),
            adaptation_id,
            chapters,
            image_api,
            generate_cover,
            adaptation,
            job_id
        )
        
        return JSONResponse({
            "success": True,
            "message": f"Started generating {len(chapters)} images",
            "total_chapters": len(chapters),
            "api_type": image_api,
            "job_id": job_id
        })
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("start_batch_failed", extra={"adaptation_id": adaptation_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

async def _process_batch_generation(adaptation_id: int, chapters: list, 
                                  image_api: str, generate_cover: bool, adaptation: dict, batch_id: str):
    """Background task for processing batch image generation"""
    try:
        # Generate chapter images
        batch_result = await image_service.generate_chapter_images_batch(
            adaptation_id=adaptation_id,
            chapters=chapters,
            image_api=image_api,
            progress_callback=_update_progress
        )
        # ensure we mark provided batch_id as complete
        if batch_result and batch_result.get("batch_id") and batch_result["batch_id"] != batch_id:
            # reconcile by copying results under provided batch id
            image_service.active_generations[batch_id] = image_service.active_generations.get(batch_result["batch_id"], {
                "adaptation_id": adaptation_id,
                "total": len(chapters),
                "completed": len(batch_result.get("images", [])),
                "status": "completed",
                "started_at": datetime.now(),
                "results": batch_result
            })
        
        # Update database with results
        for image_result in batch_result.get("images", []):
            if image_result["success"]:
                await database.update_chapter_image(
                    chapter_id=image_result["chapter_id"],
                    image_url=image_result["image_url"],
                    image_prompt=image_result["prompt"]
                )
        
        # Generate cover image if requested
        if generate_cover:
            book = await database.get_book_details(adaptation["book_id"])
            cover_result = await image_service.generate_cover_image(
                adaptation_id=adaptation_id,
                title=book["title"],
                author=book["author"],
                theme=adaptation.get("overall_theme_tone", "Adventure"),
                api_type=image_api
            )
            
            if cover_result["success"]:
                await database.update_adaptation_cover(
                    adaptation_id=adaptation_id,
                    cover_image_url=cover_result["cover_url"],
                    cover_image_prompt=cover_result["prompt"]
                )
        
        # Update adaptation status
        await database.update_adaptation_status(adaptation_id, "images_generated")

        from services.logger import get_logger
        get_logger("routes.images").info("batch_completed", extra={"adaptation_id": adaptation_id, "chapters": len(chapters)})
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("batch_failed", extra={"adaptation_id": adaptation_id, "error": str(e)})
        await database.update_adaptation_status(adaptation_id, "image_generation_failed")

async def _update_progress(batch_id: str, current: int, total: int, message: str):
    """Progress callback for batch generation"""
    from services.logger import get_logger
    get_logger("routes.images").info("batch_progress", extra={"batch_id": batch_id, "current": current, "total": total, "progress_message": message})

@router.get("/adaptation/{adaptation_id}/status")
async def legacy_generation_status(adaptation_id: int):
    return await get_generation_status(adaptation_id)

@router.get("/{adaptation_id}/generation_status")
async def get_generation_status(adaptation_id: int):
    """Get the status of image generation for an adaptation"""
    try:
        # Get chapters with image status
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        
        total_chapters = len(chapters)
        chapters_with_images = sum(1 for ch in chapters if ch.get('image_url'))
        
        # Check if there's an active batch
        active_batches = []
        for batch_id, batch_info in image_service.active_generations.items():
            if batch_info["adaptation_id"] == adaptation_id:
                active_batches.append({
                    "batch_id": batch_id,
                    "status": batch_info["status"],
                    "completed": batch_info["completed"],
                    "total": batch_info["total"],
                    "started_at": batch_info["started_at"].isoformat()
                })
        
        return JSONResponse({
            "adaptation_id": adaptation_id,
            "total_chapters": total_chapters,
            "chapters_with_images": chapters_with_images,
            "completion_percentage": (chapters_with_images / total_chapters * 100) if total_chapters > 0 else 0,
            "active_batches": active_batches
        })
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("status_failed", extra={"adaptation_id": adaptation_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{adaptation_id}/images", response_class=HTMLResponse)
async def view_generated_images(request: Request, adaptation_id: int):
    """View all generated images for an adaptation"""
    context = get_base_context(request)
    
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        
        # Get chapters with images
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        
        context.update({
            "adaptation": adaptation,
            "book": book,
            "chapters": chapters,
            "total_chapters": len(chapters),
            "chapters_with_images": sum(1 for ch in chapters if ch.get('image_url'))
        })
        
        return templates.TemplateResponse("pages/generated_images.html", context)
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("view_failed", extra={"adaptation_id": adaptation_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{adaptation_id}/regenerate_image")
async def regenerate_single_image(
    adaptation_id: int,
    chapter_id: int = Form(...),
    custom_prompt: Optional[str] = Form(None),
    image_api: str = Form("dall-e-3")
):
    """Regenerate a single image with optional custom prompt"""
    try:
        # Get chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Use custom prompt or generate new one
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = await image_service.generate_image_prompt(chapter, adaptation_id)
        
        # Generate new image
        result = await image_service.generate_single_image(
            prompt=prompt,
            chapter_id=chapter_id,
            adaptation_id=adaptation_id,
            api_type=image_api
        )
        
        if result["success"]:
            # Update database
            await database.update_chapter_image(
                chapter_id=chapter_id,
                image_url=result["image_url"],
                image_prompt=prompt
            )
            
            return JSONResponse({
                "success": True,
                "image_url": result["image_url"],
                "prompt": prompt
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result.get("error", "Image generation failed")
            })
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("single_regen_failed", extra={"adaptation_id": adaptation_id, "chapter_id": chapter_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{adaptation_id}/images/{chapter_id}")
async def delete_chapter_image(adaptation_id: int, chapter_id: int):
    """Delete a chapter image"""
    try:
        # Remove image from database
        success = await database.remove_chapter_image(chapter_id)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": "Image deleted successfully"
            })
        else:
            raise HTTPException(status_code=400, detail="Failed to delete image")
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("delete_failed", extra={"adaptation_id": adaptation_id, "chapter_id": chapter_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/{batch_id}/progress")
async def get_batch_progress(batch_id: str):
    """Get real-time progress for a batch generation"""
    try:
        progress = image_service.get_batch_progress(batch_id)
        
        if progress:
            return JSONResponse({
                "batch_id": batch_id,
                "status": progress["status"],
                "completed": progress["completed"],
                "total": progress["total"],
                "started_at": progress["started_at"].isoformat(),
                "completed_at": progress.get("completed_at", {}).isoformat() if progress.get("completed_at") else None
            })
        else:
            raise HTTPException(status_code=404, detail="Batch not found")
    
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.images").error("batch_progress_failed", extra={"batch_id": batch_id, "error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/{batch_id}/stream")
async def stream_batch_progress(batch_id: str):
    """Server-sent events stream for real-time batch progress"""
    async def generate_progress_stream():
        try:
            while True:
                progress = image_service.get_batch_progress(batch_id)
                
                if progress:
                    data = {
                        "batch_id": batch_id,
                        "status": progress["status"],
                        "completed": progress["completed"],
                        "total": progress["total"]
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # Stop streaming if completed or failed
                    if progress["status"] in ["completed", "failed"]:
                        break
                else:
                    yield f"data: {json.dumps({'error': 'Batch not found'})}\n\n"
                    break
                
                await asyncio.sleep(2)  # Update every 2 seconds
        
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_progress_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
