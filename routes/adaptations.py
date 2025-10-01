"""
Adaptations routes for KidsKlassiks
Handles adaptation creation, management, and processing
"""

from fastapi import APIRouter, Request, Form, HTTPException, BackgroundTasks
from services.character_analyzer import CharacterAnalyzer

from services.transformation_service import TransformationService

transformation_service = TransformationService()
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from typing import Optional
import asyncio
import os
from datetime import datetime, timezone

import database_fixed as database
import config

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Helper function for base context - with database API key support
async def get_base_context(request):
    """Get base context variables for all templates"""
    # Check database for current API key settings instead of config module
    try:
        openai_key = await database.get_setting("openai_api_key", config.OPENAI_API_KEY or "")
        vertex_project_id = await database.get_setting("vertex_project_id", config.VERTEX_PROJECT_ID or "")
        
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
        "notifications": [],
        "openai_status": openai_configured,
        "vertex_status": vertex_configured
    }

@router.get("/", response_class=HTMLResponse)
async def adaptations_list(request: Request):
    """List all adaptations"""
    context = await get_base_context(request)
    
    try:
        # Get all adaptations with statistics
        adaptations = await database.get_all_adaptations_with_stats()
        
        # Calculate counts for tabs
        completed_count = sum(1 for a in adaptations 
                             if a.get('chapter_count', 0) > 0 
                             and a.get('image_count', 0) >= a.get('chapter_count', 0))
        progress_count = sum(1 for a in adaptations 
                            if a.get('chapter_count', 0) > 0 
                            and a.get('image_count', 0) < a.get('chapter_count', 0))
        
        context["adaptations"] = adaptations
        context["all_count"] = len(adaptations)
        context["completed_count"] = completed_count
        context["progress_count"] = progress_count
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("adaptations_list_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": getattr(request.state, 'request_id', None)})
        context["adaptations"] = []
        context["all_count"] = 0
        context["completed_count"] = 0
        context["progress_count"] = 0
    
    return templates.TemplateResponse("pages/adaptations.html", context)

@router.get("/create", response_class=HTMLResponse)
async def create_adaptation_page(request: Request, book_id: Optional[str] = None):
    """Create new adaptation page"""
    context = await get_base_context(request)
    
    try:
        # Get all books for selection
        books = await database.get_all_books()
        context["books"] = books
        
        # If book_id provided, pre-select that book
        if book_id:
            try:
                book_id_int = int(book_id)
                selected_book = await database.get_book_details(book_id_int)
                if selected_book:
                    context["selected_book"] = selected_book
                else:
                    # Invalid book_id provided, redirect to create page without book_id
                    return RedirectResponse(url="/adaptations/create", status_code=302)
            except (ValueError, TypeError):
                # Invalid book_id format, redirect to create page without book_id
                return RedirectResponse(url="/adaptations/create", status_code=302)
        else:
            context["selected_book"] = None
            
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("create_adaptation_page_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": getattr(request.state, 'request_id', None)})
        context["books"] = []
        context["selected_book"] = None
    
    return templates.TemplateResponse("pages/create_adaptation.html", context)

@router.post("/create")
async def create_adaptation(
    request: Request,
    book_id: int = Form(...),
    target_age_group: str = Form(...),
    transformation_style: str = Form(...),
    overall_theme_tone: str = Form(...),
    key_characters_to_preserve: str = Form(""),
    chapter_structure_choice: str = Form("Auto-segment by word count")
):
    """Create a new adaptation"""
    try:
        # Create adaptation in database
        adaptation_id = await database.create_adaptation(
            book_id=book_id,
            target_age_group=target_age_group,
            transformation_style=transformation_style,
            overall_theme_tone=overall_theme_tone,
            key_characters_to_preserve=key_characters_to_preserve,
            chapter_structure_choice=chapter_structure_choice
        )
        
        if adaptation_id:
            # Start the new workflow automatically
            from services.workflow_manager import workflow_manager
            workflow_id = await workflow_manager.start_adaptation_workflow(
                book_id=book_id,
                adaptation_id=adaptation_id,
                background=True
            )
            
            # Return HTML response for HTMX with redirect to workflow status
            html_response = f"""
            <div class="alert alert-success">
                <i class="bi bi-check-circle"></i>
                <strong>Adaptation Created Successfully!</strong>
                <p class="mb-0 mt-2">Starting automatic workflow processing...</p>
                <p class="mb-0">This includes character analysis, text transformation, and prompt generation.</p>
            </div>
            <script>
                setTimeout(function() {{
                    window.location.href = '/workflow/status/{workflow_id}';
                }}, 2000);
            </script>
            """
            return HTMLResponse(content=html_response)
        else:
            html_error = """
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Error!</strong> Failed to create adaptation. Please try again.
            </div>
            """
            return HTMLResponse(content=html_error, status_code=400)
            
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("create_adaptation_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": getattr(request.state, 'request_id', None)})
        html_error = f"""
        <div class="alert alert-danger">
            <i class="bi bi-exclamation-triangle"></i>
            <strong>Error!</strong> {str(e)}
        </div>
        """
        return HTMLResponse(content=html_error, status_code=500)

@router.get("/{adaptation_id}/review", response_class=HTMLResponse)
async def review_adaptation(request: Request, adaptation_id: int):
    """Unified review and edit page for adaptation"""
    context = await get_base_context(request)
    
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        
        # Calculate statistics
        transformed_count = sum(1 for ch in chapters if ch.get("transformed_text"))
        prompts_count = sum(1 for ch in chapters if ch.get("ai_prompt"))
        images_count = sum(1 for ch in chapters if ch.get("image_url"))
        
        context["adaptation"] = adaptation
        context["chapters"] = chapters
        context["book"] = book
        context["transformed_count"] = transformed_count
        context["prompts_count"] = prompts_count
        context["images_count"] = images_count
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("review_adaptation_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))
    
    return templates.TemplateResponse("pages/unified_review.html", context)

@router.get("/{adaptation_id}/process", response_class=HTMLResponse)
async def process_adaptation_page(request: Request, adaptation_id: int):
    """Process adaptation page with step-by-step pipeline"""
    context = await get_base_context(request)
    
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        
        # Chapters as source of truth for counts
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        chapters_count = len(chapters)
        chapters_with_images = sum(1 for ch in chapters if ch.get("image_url"))

        context["adaptation"] = adaptation
        context["book"] = book
        context["chapters_count"] = chapters_count
        context["chapters_with_images"] = chapters_with_images
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("process_adaptation_page_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))
    
    return templates.TemplateResponse("pages/process_adaptation.html", context)

@router.get("/in-progress", response_class=HTMLResponse)
async def adaptations_in_progress(request: Request):
    context = await get_base_context(request)
    try:
        all_items = await database.get_all_adaptations_with_stats()
        
        # Calculate counts
        completed_count = sum(1 for a in all_items 
                             if a.get('chapter_count', 0) > 0 
                             and a.get('image_count', 0) >= a.get('chapter_count', 0))
        progress_count = sum(1 for a in all_items 
                            if a.get('chapter_count', 0) > 0 
                            and a.get('image_count', 0) < a.get('chapter_count', 0))
        
        # Filter for in progress only
        filtered = [a for a in all_items 
                   if a.get('chapter_count', 0) > 0 
                   and a.get('image_count', 0) < a.get('chapter_count', 0)]
        
        context["adaptations"] = filtered
        context["all_count"] = len(all_items)
        context["completed_count"] = completed_count
        context["progress_count"] = progress_count
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.adaptations").error("adaptations_in_progress_error", extra={"component":"routes.adaptations","error":str(e)})
        context["adaptations"] = []
        context["all_count"] = 0
        context["completed_count"] = 0
        context["progress_count"] = 0
    return templates.TemplateResponse("pages/adaptations.html", context)

@router.get("/completed", response_class=HTMLResponse)
async def adaptations_completed(request: Request):
    context = await get_base_context(request)
    try:
        all_items = await database.get_all_adaptations_with_stats()
        
        # Calculate counts
        completed_count = sum(1 for a in all_items 
                             if a.get('chapter_count', 0) > 0 
                             and a.get('image_count', 0) >= a.get('chapter_count', 0))
        progress_count = sum(1 for a in all_items 
                            if a.get('chapter_count', 0) > 0 
                            and a.get('image_count', 0) < a.get('chapter_count', 0))
        
        # Filter for completed only
        filtered = [a for a in all_items 
                   if a.get('chapter_count', 0) > 0 
                   and a.get('image_count', 0) >= a.get('chapter_count', 0)]
        
        context["adaptations"] = filtered
        context["all_count"] = len(all_items)
        context["completed_count"] = completed_count
        context["progress_count"] = progress_count
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.adaptations").error("adaptations_completed_error", extra={"component":"routes.adaptations","error":str(e)})
        context["adaptations"] = []
        context["all_count"] = 0
        context["completed_count"] = 0
        context["progress_count"] = 0
    return templates.TemplateResponse("pages/adaptations.html", context)

@router.get("/{adaptation_id}", response_class=HTMLResponse)
async def view_adaptation(request: Request, adaptation_id: int):
    """View a specific adaptation with full details"""
    context = await get_base_context(request)
    
    try:
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        
        # Count chapters with images
        chapters_with_images = sum(1 for ch in chapters if ch.get("image_url"))
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        
        context["adaptation"] = adaptation
        context["chapters"] = chapters
        context["chapters_with_images"] = chapters_with_images
        context["book"] = book
        
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("view_adaptation_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": getattr(request.state, 'request_id', None), "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))
    
    return templates.TemplateResponse("pages/view_adaptation.html", context)

@router.get("/{adaptation_id}/chapter_map")
async def get_chapter_map(adaptation_id: int, offset: int = 0, limit: int = 200):
    try:
        last = await database.get_last_adaptation_run(adaptation_id)
        if not last:
            return JSONResponse({"success": False, "error": "no_runs"}, status_code=404)
        ops = last.get("operations") or []
        fm = last.get("final_map") or []
        total_ops = len(ops)
        total_map = len(fm)
        o = max(0, int(offset))
        l = max(1, min(1000, int(limit)))
        return JSONResponse({
            "run_id": last.get("run_id"),
            "detected_count": last.get("detected_count"),
            "target_count": last.get("target_count"),
            "operations": ops[o:o+l],
            "final_map": fm[o:o+l],
            "operations_total": total_ops,
            "final_map_total": total_map,
            "offset": o,
            "limit": l,
            "started_at": last.get("started_at"),
            "finished_at": last.get("finished_at"),
            "duration_ms": last.get("duration_ms"),
            "status": last.get("status"),
            "error": last.get("error")
        })
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.adaptations").error("get_chapter_map_error", extra={"component":"routes.adaptations","error":str(e),"adaptation_id":adaptation_id})
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/{adaptation_id}/status")
async def adaptation_status(adaptation_id: int):
    """Unified adaptation status endpoint with flat fields."""
    try:
        status = await database.get_adaptation_progress(adaptation_id)
        if not status:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        # Attach last run summary
        last = await database.get_last_adaptation_run(adaptation_id)
        # Stale run timeout enforcement: if the last run is still running but exceeded timeout, mark as failed
        try:
            if last and last.get("status") == "running":
                from config import STALE_RUN_TIMEOUT_SECONDS
                started = last.get("started_at")
                if isinstance(started, str) and started.endswith("Z"):
                    started_dt = datetime.fromisoformat(started.replace('Z','+00:00'))
                    age = (datetime.now(timezone.utc) - started_dt).total_seconds()
                    if age > max(0, int(STALE_RUN_TIMEOUT_SECONDS)):
                        try:
                            await database.finish_adaptation_run(last.get("run_id"), datetime.now(timezone.utc), 0, [], [], status='failed', error='run_abandoned')
                            await database.clear_active_run(adaptation_id)
                            last["status"] = 'failed'
                            last["error"] = 'run_abandoned'
                        except Exception:
                            pass
        except Exception:
            pass
        if last:
            status["last_run"] = {
                "run_id": last.get("run_id"),
                "detected_count": last.get("detected_count"),
                "target_count": last.get("target_count"),
                "operations_count": len(last.get("operations") or []),
                "finished_at": last.get("finished_at"),
                "status": last.get("status"),
                "error": last.get("error"),
                "chapter_map_url": f"/adaptations/{adaptation_id}/chapter_map",
                "final_map": last.get("final_map"),
            }
            # Persisted run continuity: if run_id is absent in the primary status payload,
            # but DB shows a running last_run, surface that run_id so UI can continue tracking after restarts.
            if not status.get("run_id") and (last.get("status") == "running"):
                status["run_id"] = last.get("run_id")
            # Expose detector from CHAP-MAP summary, if present
            try:
                ops = last.get("operations") or []
                if ops and isinstance(ops, list) and isinstance(ops[0], dict) and ops[0].get("type") == "summary":
                    status["detector"] = ops[0].get("detector")
            except Exception:
                pass
        # Always include a status_version default to avoid UI drift
        status["status_version"] = status.get("status_version", 1)
        return JSONResponse(status)
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.adaptations").error("adaptation_status_error", extra={"component":"routes.adaptations","error":str(e),"adaptation_id":adaptation_id})
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/{adaptation_id}/curate_characters")
async def curate_characters(adaptation_id: int):
    """Curate characters for an adaptation: normalize, frequency-rank, cap via setting; persist and return counts."""
    try:
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        curated = await CharacterAnalyzer.curate_for_adaptation(adaptation, chapters)
        await database.update_adaptation_key_characters(adaptation_id, curated)
        return JSONResponse({
            "success": True,
            "curated_count": len(curated),
            "characters": curated
        })
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.adaptations").error("curate_characters_error", extra={"component":"routes.adaptations","error":str(e),"adaptation_id":adaptation_id})
        return JSONResponse({"success": False, "error": str(e)})


@router.delete("/{adaptation_id}")
async def delete_adaptation(adaptation_id: int):
    """Delete an adaptation"""
    try:
        success = await database.delete_adaptation(adaptation_id)
        if success:
            return JSONResponse({"success": True, "message": "Adaptation deleted successfully"})
        else:
            raise HTTPException(status_code=400, detail="Failed to delete adaptation")
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("delete_adaptation_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": None, "adaptation_id": adaptation_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{adaptation_id}/process_chapters")
async def process_chapters(adaptation_id: int, background_tasks: BackgroundTasks, htmx: bool = False, redirect: bool = True, request: Request = None):
    """Process the book and create chapters for the adaptation"""
    wants_html = bool(htmx) or (request is not None and str(request.headers.get('HX-Request', '')).lower() == 'true')
    # Acquire DB advisory lock to prevent concurrent runs
    lock_conn = await database.try_acquire_adaptation_lock(adaptation_id)
    if lock_conn is None:
        holder = database.get_current_run(adaptation_id)
        if wants_html:
            html = '<div class="alert alert-warning">Processing already in progress for this adaptation.</div>'
            return HTMLResponse(html, status_code=409)
        return JSONResponse({"error":"run_in_progress","holder_run_id": holder}, status_code=409)
    # Assign a run_id for this operation
    # Per-adaptation rate limit: if an active run exists and it was started less than COOLDOWN seconds ago, return 429
    try:
        from config import REPROCESS_COOLDOWN_SECONDS
        active = await database.get_active_run(adaptation_id)
        if active and active.get('updated_at'):
            started = active['updated_at']
            if isinstance(started, str) and started.endswith('Z'):
                started_dt = datetime.fromisoformat(started.replace('Z','+00:00'))
            else:
                started_dt = started if hasattr(started, 'tzinfo') else None
            if started_dt:
                age = (datetime.now(timezone.utc) - (started_dt.astimezone(timezone.utc) if started_dt.tzinfo else started_dt.replace(tzinfo=timezone.utc))).total_seconds()
                if age < max(0, int(REPROCESS_COOLDOWN_SECONDS)):
                    retry_after = int(max(1, int(REPROCESS_COOLDOWN_SECONDS) - age))
                    if wants_html:
                        html = f'<div class="alert alert-warning">Please wait {retry_after}s before starting another run.</div>'
                        resp = HTMLResponse(html, status_code=429)
                        resp.headers["Retry-After"] = str(retry_after)
                        return resp
                    return JSONResponse({"error":"rate_limited","retry_after_seconds": retry_after}, status_code=429, headers={"Retry-After": str(retry_after)})
    except Exception:
        pass

    import uuid
    run_id = str(uuid.uuid4())
    database.set_current_run(adaptation_id, run_id)
    try:
        await database.upsert_active_run(adaptation_id, run_id, stage='starting')
    except Exception:
        pass
    try:
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            await database.release_adaptation_lock(lock_conn)
            raise HTTPException(status_code=404, detail="Adaptation not found")

        book = await database.get_book_details(adaptation["book_id"])
        if not book:
            await database.release_adaptation_lock(lock_conn)
            raise HTTPException(status_code=404, detail="Book not found")

        # Read book content with safe encoding handling (support legacy 'path' key)
        file_path = book.get("path") or book.get("original_content_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail=f"Book file not found at: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback for older latin-1/Windows-1252 encoded files
            with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                content = f.read()

        # Strategy selection based on adaptation settings
        choice = (adaptation.get("chapter_structure_choice") or "").strip()
        age_group = (adaptation.get("target_age_group") or "").strip()
        # Normalize chapter structure choice from UI labels to internal codes
        _lc = choice.lower()
        if 'keep' in _lc:
            choice = 'keep_original'
        elif 'auto' in _lc or 'word' in _lc:
            choice = 'auto_wordcount'

        async def _finish_run_safe(run_id, finished_at, duration_ms, operations, final_map, status, error, meta=None):
            try:
                return await database.finish_adaptation_run(run_id, finished_at, duration_ms, operations, final_map, status=status, error=error, meta=meta)
            except TypeError:
                # Backward-compat for test doubles or older DB API without meta
                return await database.finish_adaptation_run(run_id, finished_at, duration_ms, operations, final_map, status, error)


        def _words(s: str) -> int:
            import re
            return len(re.findall(r"\w+", s or ""))

        def _wpc_for_age(age: str) -> int:
            # Original text segmentation - larger chunks that will be simplified
            # The transformation will reduce these to age-appropriate lengths
            if age == "3-5":
                return 800   # Will be reduced to ~150 words after transformation
            if age == "6-8":
                return 1000  # Will be reduced to ~300 words after transformation
            if age == "9-12":
                return 1500  # Will be reduced to ~500 words after transformation
            return 1000  # Default

        def _segment_by_wordcount(txt: str, wpc: int) -> list[str]:
            import re
            # HTML-aware paragraph boundaries: blank lines, </p>, <br>
            paras = [p for p in re.split(r"\n\s*\n|</p>|<br\s*/?>", txt or "", flags=re.IGNORECASE) if p.strip()]
            segs: list[str] = []
            cur: list[str] = []
            cur_words = 0
            for p in paras:
                pw = _words(p)
                # If adding this paragraph would exceed ~1.2x of target and we have some content, start a new segment
                if cur and (cur_words + pw) >= max(wpc, int(1.2*wpc)):
                    segs.append("\n\n".join(cur).strip())
                    cur = [p]
                    cur_words = pw
                else:
                    cur.append(p)
                    cur_words += pw
            if cur:
                # If the last segment is too small (< 0.3x wpc) and we have previous, merge
                if segs and _words("\n\n".join(cur)) < max(1, int(0.3*wpc)):
                    last = segs.pop()
                    segs.append((last + "\n\n" + "\n\n".join(cur)).strip())
                else:
                    segs.append("\n\n".join(cur).strip())
            # Fallback: if we still have no segments but text exists
            if not segs and (txt or "").strip():
                segs = [txt.strip()]
            return segs

        # Determine existing chapters and enforce strict rules for keep_original on first run
        existing = await database.get_chapters_for_adaptation(adaptation_id)
        if choice == "keep_original" and not existing:
            orig = book.get("chapter_count")
            if not orig or int(orig) < 1:
                from services.logger import get_logger
                log = get_logger("routes.adaptations")
                started_at = datetime.now(timezone.utc)
                # Record failed run without detection
                await database.create_adaptation_run(adaptation_id, run_id, 0, 0, started_at)
                await _finish_run_safe(run_id, datetime.now(timezone.utc), 0, [], [], status='failed', error='no_original_chapter_count', meta={"rule":"strict_keep_original","detected_count":0,"target_count":0})
                log.warning("chapter_normalization_refused", extra={
                    "component":"routes.adaptations","adaptation_id":adaptation_id,
                    "book_id": book.get("book_id"), "reason":"no_original_chapter_count", "run_id": run_id
                })
                if wants_html:
                    html = '<div class="alert alert-danger">Original chapter count is required for “Keep original”. Set it on the book or choose “Auto-segment by word count”.</div>'
                    return HTMLResponse(html, status_code=400)
                return JSONResponse({"error":"no_original_chapter_count"}, status_code=400)

        # Detect chapters or auto-segment by word count
        detected = []
        segments = []
        if choice == "auto_wordcount":
            wpc = _wpc_for_age(age_group)
            # HTML-aware paragraph boundaries for wordcount segmentation
            segments = _segment_by_wordcount(content, wpc)
            detected = [{"content": s} for s in segments]
        else:
            detected = transformation_service.detect_chapters_in_text(content)
            segments = [c.get("content", "") for c in detected]
            # Record which detector produced the segments (toc vs regex)
            try:
                from services.logger import get_logger
                get_logger("routes.adaptations").info(
                    "chapter_detection_method",
                    extra={
                        "component": "routes.adaptations",
                        "method": getattr(transformation_service, 'last_method', None) or 'regex',
                        "detected_count": len(segments),
                        "adaptation_id": adaptation_id,
                    },
                )
            except Exception:
                pass

        # Determine target_count: prefer existing if present to avoid churn on reruns
        if existing:
            target_count = len(existing)
        else:
            if choice == "auto_wordcount":
                target_count = len(segments)
            else:
                # keep_original path: we already enforced presence of chapter_count when first run
                target_count = int(book.get("chapter_count") or 0)

        # Normalize to target_count (conservative merge/split) with audit trail
        source_map = [[i] for i in range(len(segments))]  # track original detected indices
        import re, time
        def words(s):
            return len(re.findall(r"\w+", s or ""))
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        detected_count = len(segments)
        started_at = datetime.now(timezone.utc)
        await database.create_adaptation_run(adaptation_id, run_id, detected_count, int(target_count), started_at)
        # Persist active run for restart continuity
        try:
            await database.upsert_active_run(adaptation_id, run_id, stage='normalizing')
        except Exception:
            pass

        if detected_count == 0:
            finished_at = datetime.now(timezone.utc)
            meta = {"rule": ("strict_keep_original" if choice == "keep_original" else "auto_wordcount"), "detected_count": 0, "target_count": int(target_count) if 'target_count' in locals() else 0}
            await _finish_run_safe(run_id, finished_at, 0, [], [], status='failed', error='empty_input', meta=meta)
            if wants_html:
                html = '<div class="alert alert-danger">No recognizable chapter markers were found. Try “Auto-segment by word count”.</div>'
                return HTMLResponse(html, status_code=400)
            return JSONResponse({"success": False, "error": "No chapters detected"}, status_code=400)
        operations = []
        # Safety: cap operations length to avoid bloating rows
        from config import CHAPMAP_MAX_OPS
        def _push_op(op):
            if len(operations) < max(0, int(CHAPMAP_MAX_OPS)):
                operations.append(op)
        # Merge
        while len(segments) > int(target_count) and len(segments) > 1:
            # find shortest adjacent pair sum — deterministic by first-best tie-breaker
            best_i, best_sum = 0, None
            for i in range(len(segments)-1):
                s = words(segments[i]) + words(segments[i+1])
                if best_sum is None or s < best_sum:
                    best_sum, best_i = s, i
            lengths_before = [words(segments[best_i]), words(segments[best_i+1])]
            merged = segments[best_i] + "\n\n" + segments[best_i+1]
            log.info("chapter_merge", extra={"component":"routes.adaptations","i":best_i,"merge_words":best_sum})
            segments[best_i:best_i+2] = [merged]
            # update source_map to reflect merge
            merged_sources = source_map[best_i] + source_map[best_i+1]
            source_map[best_i:best_i+2] = [merged_sources]
            _push_op({"type":"merge","from":[best_i,best_i+1],"to":best_i,"lengths_before":lengths_before,"lengths_after":[words(merged)]})
        # Split
        def split_once(txt: str):
            # HTML-aware paragraph boundaries: treat </p> and <br> as paragraph breaks too
            paras = [p for p in re.split(r"\n\s*\n|</p>|<br\s*/?>", txt, flags=re.IGNORECASE) if p.strip()]
            if len(paras) < 2:
                mid = max(1, len(txt)//2)
                return txt[:mid], txt[mid:]
            mid = len(paras)//2
            left = "\n\n".join(paras[:mid])
            right = "\n\n".join(paras[mid:])
            return left, right
        while len(segments) < int(target_count) and segments:
            # split longest deterministically (first index on ties)
            li = max(range(len(segments)), key=lambda i: words(segments[i]))
            a,b = split_once(segments[li])
            # paragraph if either HTML breaks or blank lines are in the original
            method = "paragraph" if ("\n\n" in segments[li] or "</p>" in segments[li].lower() or "<br" in segments[li].lower()) else "midpoint"
            log.info("chapter_split_detail", extra={"component":"routes.adaptations","method":method,"i":li})
            log.info("chapter_split", extra={"component":"routes.adaptations","i":li,"left_words":words(a),"right_words":words(b)})
            segments[li:li+1] = [a,b]
            # duplicate source mapping for both outputs, since both derive from the same detected segment
            src = source_map[li]
            source_map[li:li+1] = [src.copy(), src.copy()]
            _push_op({"type":"split","from":[li],"to":li,"lengths_before":[words(a)+words(b)],"lengths_after":[words(a),words(b)]})

        # Build final_map: final index to source indices
        final_map = []
        for idx in range(min(len(segments), int(target_count))):
            final_map.append({"final_index": idx, "source_indices": source_map[idx]})

        # Transform text for age group immediately after chapter creation
        from services.chat_helper import transform_chapter_text
        from services.logger import get_logger
        transform_log = get_logger("routes.adaptations.transform")
        
        # Process and transform chapters
        transformed_segments = []
        for idx, segment_text in enumerate(segments[:int(target_count)]):
            chapter_num = idx + 1
            
            # Transform text based on age group if auto_wordcount mode
            if choice == "auto_wordcount" and segment_text:
                transform_log.info("transforming_chapter_on_create", extra={
                    "component": "routes.adaptations",
                    "chapter_number": chapter_num,
                    "original_length": len(segment_text),
                    "age_group": age_group
                })
                
                try:
                    transformed_text, error = await transform_chapter_text(
                        segment_text,
                        age_group,
                        book_title=book.get("title", "Unknown"),
                        chapter_number=chapter_num,
                        preserve_names=adaptation.get("key_characters_to_preserve", "")
                    )
                    
                    if error or not transformed_text:
                        transform_log.warning("chapter_transform_failed", extra={
                            "component": "routes.adaptations",
                            "chapter_number": chapter_num,
                            "error": error or "Empty result"
                        })
                        # Keep original if transform fails
                        transformed_segments.append((segment_text, segment_text))
                    else:
                        transform_log.info("chapter_transform_success", extra={
                            "component": "routes.adaptations",
                            "chapter_number": chapter_num,
                            "transformed_length": len(transformed_text)
                        })
                        transformed_segments.append((segment_text, transformed_text))
                except Exception as e:
                    transform_log.error("chapter_transform_exception", extra={
                        "component": "routes.adaptations",
                        "chapter_number": chapter_num,
                        "error": str(e)
                    })
                    # Keep original if transform fails
                    transformed_segments.append((segment_text, segment_text))
            else:
                # For keep_original mode, don't transform
                transformed_segments.append((segment_text, ""))
        
        # Persist chapters with both original and transformed text
        ok = await database.replace_adaptation_chapters_with_transform(
            adaptation_id, 
            transformed_segments
        )
        if not ok:
            # Fallback to original method if new one doesn't exist
            ok = await database.replace_adaptation_chapters(
                adaptation_id, 
                [seg[0] for seg in transformed_segments]
            )
        if not ok:
            await _finish_run_safe(run_id, datetime.now(timezone.utc), 0, operations, final_map, status='failed', error='persist_failed', meta={"rule": ("strict_keep_original" if choice == "keep_original" else "auto_wordcount")})
            # Return an HTML fragment for HTMX
            if wants_html:
                html = f'<div class="alert alert-danger">Failed to persist normalized chapters.</div>'
                return HTMLResponse(html, status_code=500)
            return JSONResponse({"error":"persist_failed"}, status_code=500)

        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - started_at).total_seconds()*1000)
        # Emit summary meta
        meta = {
            "rule": "strict_keep_original" if choice == "keep_original" else "auto_wordcount",
            "detector": ("auto_wordcount" if choice == "auto_wordcount" else ("toc" if getattr(transformation_service, 'last_method', None) == 'toc' else "regex")),
            "target_count": int(target_count),
            "detected_count": int(detected_count),
            "merge_ops": len([op for op in operations if op.get('type') == 'merge']),
            "split_ops": len([op for op in operations if op.get('type') == 'split'])
        }
        await _finish_run_safe(run_id, finished_at, duration_ms, operations, final_map, status='succeeded', error=None, meta=meta)
        try:
            await database.clear_active_run(adaptation_id)
        except Exception:
            pass
        # Ensure Content-Type matches path expectations
        # (HTML for HTMX, JSON for API/tests)

        # After chapters are created, immediately transform them if age group is set
        if adaptation.get("target_age_group"):
            from services.chat_helper import transform_chapter_text as transform_text
            log.info("auto_transforming_chapters", extra={
                "component": "routes.adaptations",
                "adaptation_id": adaptation_id,
                "chapter_count": int(target_count),
                "age_group": adaptation.get("target_age_group")
            })
            
            # Get the newly created chapters
            new_chapters = await database.get_chapters_for_adaptation(adaptation_id)
            transform_count = 0
            
            for chapter in new_chapters:
                chapter_id = chapter.get("chapter_id")
                original_text = chapter.get("original_text_segment")
                
                if original_text and not chapter.get("transformed_text"):
                    try:
                        transformed_text, error = await transform_text(original_text, adaptation, book)
                        if transformed_text and not error:
                            await database.update_chapter_transformed_text(chapter_id, transformed_text)
                            transform_count += 1
                            log.info("chapter_auto_transformed", extra={
                                "component": "routes.adaptations",
                                "chapter_id": chapter_id,
                                "original_words": len(original_text.split()),
                                "transformed_words": len(transformed_text.split())
                            })
                    except Exception as e:
                        log.error("auto_transform_error", extra={
                            "component": "routes.adaptations",
                            "chapter_id": chapter_id,
                            "error": str(e)
                        })
            
            if transform_count > 0:
                log.info("auto_transform_complete", extra={
                    "component": "routes.adaptations",
                    "adaptation_id": adaptation_id,
                    "transformed_count": transform_count,
                    "total_count": int(target_count)
                })
        
        # Success HTML fragment. For HTMX requests, return updated chapters table partial
        if wants_html:
            chapters = await database.get_chapters_for_adaptation(adaptation_id)
            from fastapi.templating import Jinja2Templates
            templates_local = Jinja2Templates(directory="templates")
            context = {"request": request, "chapters": chapters}
            return templates_local.TemplateResponse("components/chapters_table.html", context)
        return JSONResponse({"success": True, "chapters_count": int(target_count)})

    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("process_chapters_error", extra={"error": str(e), "component": "routes.adaptations", "request_id": None, "adaptation_id": adaptation_id})
        try:
            finished_at = datetime.now(timezone.utc)
            await _finish_run_safe(run_id, finished_at, 0, [], [], status='failed', error=str(e), meta={"rule": ("strict_keep_original" if choice == "keep_original" else "auto_wordcount")})
        except Exception:
            pass
        try:
            await database.clear_active_run(adaptation_id)
        except Exception:
            pass
        if wants_html:
            html = f'<div class="alert alert-danger">{str(e)}</div>'
            return HTMLResponse(html, status_code=400)
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        # Always release the advisory lock
        try:
            await database.release_adaptation_lock(lock_conn)
        except Exception:
            pass
        finally:
            try:
                database.clear_current_run(adaptation_id)
            except Exception:
                pass


@router.post("/{adaptation_id}/transform-all")
async def transform_all_chapters(adaptation_id: int):
    """Transform all chapters of an adaptation to age-appropriate versions"""
    try:
        from services.chat_helper import transform_chapter_text as transform_text
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            raise HTTPException(status_code=404, detail="Adaptation not found")
        
        # Get book details
        book = await database.get_book_details(adaptation["book_id"])
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Get all chapters
        chapters = await database.get_chapters_for_adaptation(adaptation_id)
        if not chapters:
            return JSONResponse({
                "success": False,
                "error": "No chapters found for this adaptation"
            }, status_code=400)
        
        log.info("transform_all_start", extra={
            "component": "routes.adaptations",
            "adaptation_id": adaptation_id,
            "chapter_count": len(chapters),
            "age_group": adaptation.get("target_age_group")
        })
        
        results = []
        success_count = 0
        error_count = 0
        
        for chapter in chapters:
            chapter_id = chapter.get("chapter_id")
            chapter_number = chapter.get("chapter_number")
            
            # Skip if already transformed
            if chapter.get("transformed_text") and chapter.get("transformed_text").strip():
                log.info("chapter_already_transformed", extra={
                    "component": "routes.adaptations",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number
                })
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "skipped",
                    "message": "Already transformed"
                })
                continue
            
            # Get original text
            original_text = chapter.get("original_text_segment")
            if not original_text or not original_text.strip():
                log.warning("chapter_no_original_text", extra={
                    "component": "routes.adaptations",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number
                })
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "error",
                    "error": "No original text"
                })
                error_count += 1
                continue
            
            # Transform the text
            log.info("transforming_chapter", extra={
                "component": "routes.adaptations",
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "original_length": len(original_text)
            })
            
            transformed_text, error = await transform_text(original_text, adaptation, book)
            
            if error or not transformed_text:
                log.error("chapter_transform_failed", extra={
                    "component": "routes.adaptations",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "error": error
                })
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "error",
                    "error": error or "Transformation failed"
                })
                error_count += 1
                continue
            
            # Update chapter with transformed text
            update_success = await database.update_chapter_text_and_prompt(
                chapter_id=chapter_id,
                transformed_text=transformed_text,
                user_prompt=""  # Empty prompt since this is AI-generated
            )
            
            if not update_success:
                log.error("chapter_update_failed", extra={
                    "component": "routes.adaptations",
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number
                })
                results.append({
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "status": "error",
                    "error": "Failed to save"
                })
                error_count += 1
                continue
            
            log.info("chapter_transformed", extra={
                "component": "routes.adaptations",
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "original_length": len(original_text),
                "transformed_length": len(transformed_text)
            })
            
            results.append({
                "chapter_id": chapter_id,
                "chapter_number": chapter_number,
                "status": "success",
                "original_length": len(original_text),
                "transformed_length": len(transformed_text)
            })
            success_count += 1
        
        log.info("transform_all_complete", extra={
            "component": "routes.adaptations",
            "adaptation_id": adaptation_id,
            "total_chapters": len(chapters),
            "success_count": success_count,
            "error_count": error_count
        })
        
        return JSONResponse({
            "success": True,
            "total_chapters": len(chapters),
            "success_count": success_count,
            "error_count": error_count,
            "results": results
        })
    
    except HTTPException:
        raise
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.adaptations")
        log.error("transform_all_error", extra={
            "error": str(e),
            "component": "routes.adaptations",
            "adaptation_id": adaptation_id
        })
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
