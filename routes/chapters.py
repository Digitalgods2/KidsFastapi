"""
Chapters routes for KidsKlassiks
Handles individual chapter operations, viewing, and image management
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

import database_fixed as database
from services.image_generation_service import ImageGenerationService

router = APIRouter()
image_service = ImageGenerationService()


@router.get("/{chapter_id}/details")
async def get_chapter_details(chapter_id: int):
    """Get detailed information about a specific chapter"""
    try:
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        return JSONResponse({
            "chapter_id": chapter.get("chapter_id"),
            "chapter_number": chapter.get("chapter_number"),
            "title": chapter.get("title"),
            "content": chapter.get("content") or chapter.get("transformed_chapter_text", ""),
            "image_url": chapter.get("image_url"),
            "image_prompt": chapter.get("image_prompt") or chapter.get("ai_generated_image_prompt"),
            "adaptation_id": chapter.get("adaptation_id"),
            "created_at": str(chapter.get("created_at")) if chapter.get("created_at") else None,
            "updated_at": str(chapter.get("updated_at")) if chapter.get("updated_at") else None
        })
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        log.error("get_chapter_details_error", extra={
            "error": str(e), 
            "component": "routes.chapters",
            "chapter_id": chapter_id
        })
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chapter_id}/update")
async def update_chapter(
    chapter_id: int,
    title: str = Form(None),
    content: str = Form(None),
    image_prompt: str = Form(None)
):
    """Update chapter details"""
    try:
        # Get existing chapter
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Update fields that were provided
        if title is not None:
            await database.update_chapter_title(chapter_id, title)
        
        if content is not None:
            await database.update_chapter_content(chapter_id, content)
        
        if image_prompt is not None:
            await database.update_chapter_image_prompt(chapter_id, image_prompt)
        
        return JSONResponse({
            "success": True,
            "message": "Chapter updated successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        log.error("update_chapter_error", extra={
            "error": str(e),
            "component": "routes.chapters", 
            "chapter_id": chapter_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/{chapter_id}/generate-image")
async def generate_chapter_image(
    chapter_id: int,
    custom_prompt: Optional[str] = Form(None),
    image_api: Optional[str] = Form(None)
):
    """Generate or regenerate an image for a chapter"""
    try:
        # Get chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Determine the prompt to use
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Use existing prompt or generate a new one
            prompt = chapter.get("image_prompt") or chapter.get("ai_generated_image_prompt")
            if not prompt:
                # Generate a new prompt
                from services import chat_helper
                content = chapter.get("content") or chapter.get("transformed_chapter_text", "")
                adaptation = await database.get_adaptation_details(chapter["adaptation_id"])
                prompt, err = await chat_helper.generate_chapter_image_prompt(
                    transformed_text=content,
                    chapter_number=chapter["chapter_number"],
                    adaptation=adaptation
                )
                if not prompt:
                    return JSONResponse({
                        "success": False,
                        "error": err or "Failed to generate prompt"
                    }, status_code=400)
                
                # Save the generated prompt
                await database.update_chapter_image_prompt(chapter_id, prompt)
        
        # Resolve image API backend
        if not image_api:
            image_api = await database.get_setting("default_image_backend", "dall-e-3")
        
        # Generate the image
        result = await image_service.generate_single_image(
            prompt=prompt,
            chapter_id=chapter_id,
            adaptation_id=chapter["adaptation_id"],
            api_type=image_api
        )
        
        if result.get("success"):
            # Update database with new image
            image_url = result.get("image_url")
            await database.update_chapter_image(
                chapter_id=chapter_id,
                image_url=image_url,
                image_prompt=prompt
            )
            
            return JSONResponse({
                "success": True,
                "image_url": image_url,
                "prompt": prompt,
                "message": "Image generated successfully"
            })
        else:
            return JSONResponse({
                "success": False,
                "error": result.get("error", "Image generation failed")
            }, status_code=500)
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        log.error("generate_chapter_image_error", extra={
            "error": str(e),
            "component": "routes.chapters",
            "chapter_id": chapter_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.delete("/{chapter_id}/image")
async def delete_chapter_image(chapter_id: int):
    """Delete a chapter's image"""
    try:
        # Get chapter to find image path
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Delete the image file if it exists
        image_url = chapter.get("image_url")
        if image_url:
            import os
            # Convert URL to filesystem path
            if image_url.startswith('/'):
                image_path = image_url[1:]
            else:
                image_path = image_url
            
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    from services.logger import get_logger
                    get_logger("routes.chapters").info("image_deleted", extra={
                        "component": "routes.chapters",
                        "chapter_id": chapter_id,
                        "image_path": image_path
                    })
                except Exception as e:
                    from services.logger import get_logger
                    get_logger("routes.chapters").warning("image_delete_failed", extra={
                        "component": "routes.chapters",
                        "chapter_id": chapter_id,
                        "error": str(e)
                    })
        
        # Remove image URL from database
        await database.update_chapter_image_url(chapter_id, None)
        
        return JSONResponse({
            "success": True,
            "message": "Image deleted successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        log.error("delete_chapter_image_error", extra={
            "error": str(e),
            "component": "routes.chapters",
            "chapter_id": chapter_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/{chapter_id}/regenerate-image")
async def regenerate_chapter_image(
    chapter_id: int,
    image_api: Optional[str] = Form(None)
):
    """Regenerate image using the existing prompt"""
    try:
        # Get chapter details
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Get existing prompt
        prompt = chapter.get("image_prompt") or chapter.get("ai_generated_image_prompt")
        if not prompt:
            return JSONResponse({
                "success": False,
                "error": "No prompt available for regeneration. Please generate a prompt first."
            }, status_code=400)
        
        # Delete old image if it exists
        old_image_url = chapter.get("image_url")
        if old_image_url:
            import os
            image_path = old_image_url[1:] if old_image_url.startswith('/') else old_image_url
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception:
                    pass  # Continue even if deletion fails
        
        # Generate using the generate endpoint
        return await generate_chapter_image(chapter_id, custom_prompt=prompt, image_api=image_api)
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        log.error("regenerate_chapter_image_error", extra={
            "error": str(e),
            "component": "routes.chapters",
            "chapter_id": chapter_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.post("/{chapter_id}/transform")
async def transform_chapter_text(chapter_id: int):
    """Transform chapter text to age-appropriate version using AI"""
    try:
        from services.chat_helper import transform_chapter_text as transform_text
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        
        # Get chapter
        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        
        # Get adaptation details
        adaptation_id = chapter.get("adaptation_id")
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Get original text
        original_text = chapter.get("original_text_segment") or chapter.get("content")
        if not original_text or not original_text.strip():
            return JSONResponse({
                "success": False,
                "error": "No original text found for this chapter"
            }, status_code=400)
        
        log.info("transform_chapter_start", extra={
            "component": "routes.chapters",
            "chapter_id": chapter_id,
            "adaptation_id": adaptation_id,
            "age_group": adaptation.get("target_age_group"),
            "original_length": len(original_text)
        })
        
        # Transform the text
        transformed_text, error = await transform_text(original_text, adaptation, book)
        
        if error or not transformed_text:
            log.error("transform_chapter_failed", extra={
                "component": "routes.chapters",
                "chapter_id": chapter_id,
                "error": error
            })
            return JSONResponse({
                "success": False,
                "error": error or "Transformation failed"
            }, status_code=500)
        
        # Update chapter with transformed text
        success = await database.update_chapter(
            chapter_id=chapter_id,
            transformed_text=transformed_text,
            ai_prompt=chapter.get("ai_prompt") or chapter.get("image_prompt")
        )
        
        if not success:
            return JSONResponse({
                "success": False,
                "error": "Failed to save transformed text"
            }, status_code=500)
        
        log.info("transform_chapter_complete", extra={
            "component": "routes.chapters",
            "chapter_id": chapter_id,
            "original_length": len(original_text),
            "transformed_length": len(transformed_text),
            "reduction_pct": int((1 - len(transformed_text)/len(original_text)) * 100)
        })
        
        return JSONResponse({
            "success": True,
            "transformed_text": transformed_text,
            "original_length": len(original_text),
            "transformed_length": len(transformed_text)
        })
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.chapters")
        log.error("transform_chapter_error", extra={
            "error": str(e),
            "component": "routes.chapters",
            "chapter_id": chapter_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
