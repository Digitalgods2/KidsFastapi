"""
Review routes for KidsKlassiks
Handles review and editing of adaptations
"""

from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import database_fixed as database
import config
import os
import shutil
import subprocess
from urllib.parse import urlparse
import aiohttp
import base64

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Helpers for image import
ALLOWED_EXTS = {".png", ".jpg", ".jpeg"}

def _parse_size(size_str: str) -> tuple[int, int]:
    try:
        w, h = size_str.lower().split("x")
        return int(w), int(h)
    except Exception:
        return 1024, 1024

def _detect_orientation(tmp_path: str) -> str:
    try:
        from PIL import Image
        with Image.open(tmp_path) as im:
            w, h = im.size
            return "landscape" if w >= h else "portrait"
    except Exception:
        return "landscape"

def _get_target_size_for_import(default_backend: str | None, default_ratio: str | None, tmp_path: str) -> tuple[int, int]:
    try:
        if default_backend and default_ratio:
            from services.backends import get_aspect_ratio_size
            size_str = get_aspect_ratio_size(default_backend, default_ratio)
            return _parse_size(size_str)
    except Exception:
        pass
    # Fallback: pick by orientation
    orient = _detect_orientation(tmp_path)
    if orient == "portrait":
        return 1080, 1920
    else:
        return 1920, 1080

def _run_ffmpeg_resize(src: str, dst: str, width: int, height: int) -> bool:
    # Ensure ffmpeg exists and run resize with letterbox to exact size
    vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", src, "-vf", vf, dst
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return result.returncode == 0 and os.path.exists(dst)
    except FileNotFoundError:
        return False

async def _import_image_common(tmp_upload_path: str, target_path: str, default_backend: str | None, default_ratio: str | None) -> str:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    w, h = _get_target_size_for_import(default_backend, default_ratio, tmp_upload_path)

    # Use ffmpeg, fallback to Pillow
    ok = _run_ffmpeg_resize(tmp_upload_path, target_path, w, h)
    if not ok:
        try:
            from PIL import Image
            with Image.open(tmp_upload_path) as im:
                im = im.convert("RGBA" if target_path.lower().endswith(".png") else "RGB")
                im.thumbnail((w, h))
                bg_mode = "RGBA" if target_path.lower().endswith(".png") else "RGB"
                bg_color = (0, 0, 0, 0) if bg_mode == "RGBA" else (255, 255, 255)
                bg = Image.new(bg_mode, (w, h), bg_color)
                # center paste
                x = (w - im.width) // 2
                y = (h - im.height) // 2
                bg.paste(im, (x, y), im if im.mode == "RGBA" else None)
                bg.save(target_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process image: {e}")
    return target_path

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

@router.post("/adaptation/{adaptation_id}/import-cover")
async def import_cover_image(adaptation_id: int, file: UploadFile = File(None), image_url: str | None = Form(None)):
    """Import and replace the cover image. Keeps same filename so existing links continue to work.
    Accepts either a file upload or an image_url (http(s) or data: URL or JSON with base64).
    """
    try:
        # Validate extension or presence of image_url
        ext = None
        if file is not None:
            _, ext = os.path.splitext(file.filename or "")
            ext = (ext or "").lower()
            if ext not in ALLOWED_EXTS:
                raise HTTPException(status_code=400, detail="Only PNG or JPG images are allowed")
        elif not image_url:
            raise HTTPException(status_code=400, detail="Provide either file or image_url")

        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        book_id = adaptation.get("book_id")
        if not book_id:
            raise HTTPException(status_code=400, detail="Adaptation missing book_id")

        # Determine target path
        target_dir = os.path.join("generated_images", str(book_id), "chapters")
        os.makedirs(target_dir, exist_ok=True)
        # Cover filename standard is PNG
        target_filename = f"cover_adaptation_{adaptation_id}.png"
        target_path = os.path.join(target_dir, target_filename)

        # Acquire temp file either from upload or by downloading image_url
        os.makedirs("uploads", exist_ok=True)
        tmp_path = os.path.join("uploads", f"tmp_import_cover_{adaptation_id}{ext or '.png'}")
        if file is not None:
            with open(tmp_path, "wb") as f:
                f.write(await file.read())
        else:
            async def _download(url: str) -> bytes:
                if url.startswith("data:image"):
                    try:
                        header, b64 = url.split(",", 1)
                        return base64.b64decode(b64)
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Invalid data URL: {e}")
                timeout = aiohttp.ClientTimeout(total=25)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        ctype = resp.headers.get("content-type", "")
                        data = await resp.read()
                        # If non-200, try to bubble remote JSON error message
                        if resp.status != 200:
                            detail = f"Failed to fetch image_url: HTTP {resp.status}"
                            try:
                                import json
                                payload = json.loads(data)
                                if isinstance(payload, dict) and payload.get("error"):
                                    detail = f"Remote error: {payload.get('error')}"
                                elif isinstance(payload, dict) and payload.get("detail"):
                                    detail = f"Remote error: {payload.get('detail')}"
                            except Exception:
                                # fallback to text snippet
                                try:
                                    text_snip = data.decode("utf-8", "ignore")[:200]
                                    if text_snip.strip():
                                        detail = f"{detail} - {text_snip}"
                                except Exception:
                                    pass
                            raise HTTPException(status_code=400, detail=detail)
                        # If JSON or JSON-like, parse for base64 or bubble error
                        try:
                            should_try_json = ("application/json" in ctype) or (data and data.lstrip()[:1] in (b"{", b"[") )
                            if should_try_json:
                                import json
                                payload = json.loads(data)
                                if isinstance(payload, dict):
                                    if payload.get("error"):
                                        raise HTTPException(status_code=400, detail=f"Remote error: {payload.get('error')}")
                                    b64 = payload.get("base64") or payload.get("data") or payload.get("image_base64")
                                    if b64 and isinstance(b64, str):
                                        if b64.startswith("data:image"):
                                            b64 = b64.split(",", 1)[1]
                                        return base64.b64decode(b64)
                        except HTTPException:
                            raise
                        except Exception:
                            pass
                        return data
            data = await _download(image_url)
            with open(tmp_path, "wb") as f:
                f.write(data)

        # Load settings
        try:
            default_backend = await database.get_setting("default_image_backend", None)
        except Exception:
            default_backend = None
        try:
            default_ratio = await database.get_setting("default_aspect_ratio", None)
        except Exception:
            default_ratio = None

        # Process and overwrite
        await _import_image_common(tmp_path, target_path, default_backend, default_ratio)

        # Do not change DB link; but return a cache-busting URL for UI refresh
        served_url = f"/{target_dir}/{target_filename}?v={int(__import__('time').time())}"
        return JSONResponse({"success": True, "image_url": served_url})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chapter/{chapter_id}/import-image")
async def import_chapter_image(chapter_id: int, file: UploadFile = File(None), image_url: str | None = Form(None)):
    """Import and replace a chapter image, keeping filename if one exists; otherwise create a sensible default and update DB.
    Accepts either a file upload or an image_url (http(s) or data: URL or JSON with base64).
    """
    try:
        # Validate ext or presence of image_url
        ext = None
        if file is not None:
            _, ext = os.path.splitext(file.filename or "")
            ext = (ext or "").lower()
            if ext not in ALLOWED_EXTS:
                raise HTTPException(status_code=400, detail="Only PNG or JPG images are allowed")
        elif not image_url:
            raise HTTPException(status_code=400, detail="Provide either file or image_url")

        chapter = await database.get_chapter_details(chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found")
        adaptation_id = chapter.get("adaptation_id")
        if not adaptation_id:
            raise HTTPException(status_code=400, detail="Chapter missing adaptation_id")
        adaptation = await database.get_adaptation_details(adaptation_id)
        book_id = adaptation.get("book_id") if adaptation else None
        if not book_id:
            raise HTTPException(status_code=400, detail="Adaptation/book missing")

        existing_url = chapter.get("image_url") or ""
        target_dir = os.path.join("generated_images", str(book_id), "chapters")
        os.makedirs(target_dir, exist_ok=True)

        if existing_url:
            # Derive existing path to keep same filename
            parsed = urlparse(existing_url)
            path = (parsed.path or existing_url).lstrip("/")
            if not path.startswith(target_dir):
                path = os.path.join(target_dir, os.path.basename(path.split("?")[0]))
            target_path = path.split("?")[0]
        else:
            # No existing image; create default filename
            chapter_number = chapter.get("chapter_number") or chapter_id
            target_path = os.path.join(target_dir, f"adaptation_{adaptation_id}_chapter_{chapter_number}_import.png")

        # Acquire temp file
        os.makedirs("uploads", exist_ok=True)
        tmp_path = os.path.join("uploads", f"tmp_import_chapter_{chapter_id}{ext or '.png'}")
        if file is not None:
            with open(tmp_path, "wb") as f:
                f.write(await file.read())
        else:
            async def _download(url: str) -> bytes:
                if url.startswith("data:image"):
                    try:
                        header, b64 = url.split(",", 1)
                        return base64.b64decode(b64)
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Invalid data URL: {e}")
                timeout = aiohttp.ClientTimeout(total=25)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        ctype = resp.headers.get("content-type", "")
                        data = await resp.read()
                        # If non-200, try to bubble remote JSON error message
                        if resp.status != 200:
                            detail = f"Failed to fetch image_url: HTTP {resp.status}"
                            try:
                                import json
                                payload = json.loads(data)
                                if isinstance(payload, dict) and payload.get("error"):
                                    detail = f"Remote error: {payload.get('error')}"
                                elif isinstance(payload, dict) and payload.get("detail"):
                                    detail = f"Remote error: {payload.get('detail')}"
                            except Exception:
                                # fallback to text snippet
                                try:
                                    text_snip = data.decode("utf-8", "ignore")[:200]
                                    if text_snip.strip():
                                        detail = f"{detail} - {text_snip}"
                                except Exception:
                                    pass
                            raise HTTPException(status_code=400, detail=detail)
                        # If JSON or JSON-like, parse for base64 or bubble error
                        try:
                            should_try_json = ("application/json" in ctype) or (data and data.lstrip()[:1] in (b"{", b"[") )
                            if should_try_json:
                                import json
                                payload = json.loads(data)
                                if isinstance(payload, dict):
                                    if payload.get("error"):
                                        raise HTTPException(status_code=400, detail=f"Remote error: {payload.get('error')}")
                                    b64 = payload.get("base64") or payload.get("data") or payload.get("image_base64")
                                    if b64 and isinstance(b64, str):
                                        if b64.startswith("data:image"):
                                            b64 = b64.split(",", 1)[1]
                                        return base64.b64decode(b64)
                        except HTTPException:
                            raise
                        except Exception:
                            pass
                        return data
            data = await _download(image_url)
            with open(tmp_path, "wb") as f:
                f.write(data)

        # Load settings
        try:
            default_backend = await database.get_setting("default_image_backend", None)
        except Exception:
            default_backend = None
        try:
            default_ratio = await database.get_setting("default_aspect_ratio", None)
        except Exception:
            default_ratio = None

        if not os.path.splitext(target_path)[1]:
            target_path += ".png"

        # Process and overwrite
        await _import_image_common(tmp_path, target_path, default_backend, default_ratio)

        served_url = f"/{target_path}?v={int(__import__('time').time())}"

        # If chapter didn't have an image_url before, update DB now
        if not existing_url:
            try:
                await database.update_chapter_image(
                    chapter_id=chapter_id,
                    image_url=served_url.split("?")[0],
                    image_prompt=chapter.get("ai_prompt") or chapter.get("image_prompt") or ""
                )
            except Exception:
                pass

        return JSONResponse({"success": True, "image_url": served_url})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            # Return graceful 200 with explicit message so UI can show it
            return JSONResponse({"success": False, "error": f"AI generation failed: {error}"})

        if not cover_prompt:
            return JSONResponse({"success": False, "error": "AI returned empty cover prompt"})

        # Save the generated prompt to database
        success = await database.update_adaptation_cover_image_prompt_only(adaptation_id, cover_prompt)

        if success:
            return JSONResponse({
                "success": True,
                "cover_prompt": cover_prompt,
                "message": "AI-generated cover prompt created successfully"
            })
        else:
            return JSONResponse({"success": False, "error": "Failed to save cover prompt"})

    except HTTPException as he:
        # Convert to 200 with error so UI doesn't display 'Unknown error'
        return JSONResponse({"success": False, "error": he.detail if hasattr(he, 'detail') else str(he)})
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.review")
        log.error("generate_cover_prompt_error", extra={"error": str(e), "component": "routes.review", "request_id": None, "adaptation_id": adaptation_id})
        return JSONResponse({"success": False, "error": str(e)})

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
        import traceback
        log = get_logger("routes.review")
        error_detail = str(e) if str(e) else repr(e)
        log.error("regenerate_cover_error", extra={
            "error": error_detail, 
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "component": "routes.review", 
            "request_id": None, 
            "adaptation_id": adaptation_id
        })
        raise HTTPException(status_code=500, detail=error_detail if error_detail else "Error regenerating cover image")