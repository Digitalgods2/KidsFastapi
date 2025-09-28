"""
Books routes for KidsKlassiks
Handles import, library management with proper async and state management
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import asyncio
import os
import uuid
import re

import random
import database_fixed as database
from models import BookImportRequest, BookResponse
import config
from services import chat_helper

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Track processing states
processing_states = {}

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

def detect_chapters_universal(text):
    """
    Universal chapter detection for any book format from any era.
    Pure pattern recognition, no book-specific assumptions.
    """
    import re
    
    lines = text.split('\n')
    
    # Comprehensive patterns covering formats from different centuries and styles
    chapter_patterns = [
        # Roman numerals with period and title (19th century common)
        (r'^\s*Chapter\s+([IVXLCDM]+)\.\s+([A-Z][A-Za-z\s,\'-]+)', 'roman_with_title'),
        
        # Numbers with period and title (modern format)
        (r'^\s*Chapter\s+(\d+)\.\s+([A-Z][A-Za-z\s,\'-]+)', 'numeric_with_title'),
        
        # Roman with colon or dash
        (r'^\s*Chapter\s+([IVXLCDM]+)\s*[:\-—–]\s*(.+)', 'roman_with_separator'),
        (r'^\s*Chapter\s+(\d+)\s*[:\-—–]\s*(.+)', 'numeric_with_separator'),
        
        # Standalone formats
        (r'^\s*Chapter\s+([IVXLCDM]+)\s*$', 'roman_simple'),
        (r'^\s*Chapter\s+(\d+)\s*$', 'numeric_simple'),
        
        # Uppercase variants
        (r'^\s*CHAPTER\s+([IVXLCDM]+)', 'roman_uppercase'),
        (r'^\s*CHAPTER\s+(\d+)', 'numeric_uppercase'),
        
        # Abbreviated forms (Victorian era)
        (r'^\s*Chap\.\s*([IVXLCDM]+)', 'roman_abbreviated'),
        (r'^\s*CHAP\.\s*([IVXLCDM]+)', 'roman_abbreviated_caps'),
        (r'^\s*Chap\.\s*(\d+)', 'numeric_abbreviated'),
        (r'^\s*CHAP\.\s*(\d+)', 'numeric_abbreviated_caps'),
        
        # Part/Book divisions (epic novels)
        (r'^\s*PART\s+([IVXLCDM]+)', 'part_roman'),
        (r'^\s*Part\s+([IVXLCDM]+)', 'part_roman_mixed'),
        (r'^\s*BOOK\s+([IVXLCDM]+)', 'book_roman'),
        (r'^\s*Book\s+(\d+)', 'book_numeric'),
        
        # Just numbers or romans with period (minimalist)
        (r'^\s*([IVXLCDM]+)\.\s+[A-Z]', 'roman_minimal'),
        (r'^\s*(\d+)\.\s+[A-Z]', 'numeric_minimal'),
        
        # Centered chapters (older typesetting)
        (r'^\s{10,}Chapter\s+([IVXLCDM]+)', 'roman_centered'),
        (r'^\s{10,}CHAPTER\s+(\d+)', 'numeric_centered'),
        
        # Section symbols
        (r'^\s*§\s*(\d+)', 'section_symbol'),
        
        # Spelled out numbers (classic literature)
        (r'^\s*Chapter\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen|Nineteen|Twenty|Twenty-One|Twenty-Two|Twenty-Three|Twenty-Four|Twenty-Five)', 'spelled_out'),
        (r'^\s*CHAPTER\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)', 'spelled_caps'),
        
        # Letter format (epistolary novels)
        (r'^\s*Letter\s+([IVXLCDM]+|\d+)', 'letter_format'),
        
        # Story/Tale format
        (r'^\s*Story\s+(\d+)[:\.\s]', 'story_format'),
        (r'^\s*Tale\s+(\d+)[:\.\s]', 'tale_format'),
    ]
    
    best_match = None
    best_count = 0
    
    # Try each pattern and use the one that finds the most valid chapters
    for pattern, pattern_name in chapter_patterns:
        temp_chapters = []
        
        for i, line in enumerate(lines):
            if re.match(pattern, line, re.IGNORECASE):
                temp_chapters.append((i, line.strip()))
        
        if temp_chapters:
            # Validate that these are real chapters with proper spacing
            valid_chapters = []
            last_line = -100
            
            for line_num, line_text in temp_chapters:
                # Chapters should be at least 30 lines apart to be valid
                if line_num - last_line > 30:
                    valid_chapters.append((line_num, line_text))
                    last_line = line_num
            
            if len(valid_chapters) > best_count:
                best_count = len(valid_chapters)
                best_match = (pattern_name, valid_chapters)
    
    if best_match:
        pattern_name, chapters = best_match
        try:
            from services.logger import get_logger
            get_logger("routes.books").info(
                "chapter_patterns_detected",
                extra={
                    "component": "routes.books",
                    "count": len(chapters),
                    "pattern": pattern_name,
                    "samples": [
                        {"line": line_num, "text": line_text[:60]}
                        for line_num, line_text in chapters[:3]
                    ],
                },
            )
        except Exception:
            pass
        return len(chapters)
    else:
        try:
            from services.logger import get_logger
            get_logger("routes.books").info(
                "chapter_patterns_none",
                extra={"component": "routes.books"},
            )
        except Exception:
            pass
        return 0

def detect_original_chapters(text):
    """
    Extract actual chapter content as separate texts.
    Returns list of chapter texts or None.
    """
    lines = text.split('\n')
    chapter_starts = []
    
    # Find all chapter start positions using comprehensive patterns
    chapter_patterns = [
        r'^Chapter\s+[IVXLCDM]+',
        r'^Chapter\s+\d+',
        r'^CHAPTER\s+[IVXLCDM]+',
        r'^CHAPTER\s+\d+',
        r'^Part\s+[IVXLCDM]+',
        r'^Part\s+\d+',
        r'^\d+\.\s+[A-Z]',
        r'^[IVXLCDM]+\.\s+[A-Z]',
        r'^Chap\.\s*[IVXLCDM]+',
        r'^Chap\.\s*\d+',
    ]
    
    for i, line in enumerate(lines):
        for pattern in chapter_patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                chapter_starts.append(i)
                break
    
    if not chapter_starts:
        return None
    
    # Extract chapter contents
    chapters = []
    for j in range(len(chapter_starts)):
        start = chapter_starts[j]
        
        # Skip the chapter heading and blank lines
        content_start = start + 1
        while content_start < len(lines) and not lines[content_start].strip():
            content_start += 1
        
        # Find where this chapter ends
        if j < len(chapter_starts) - 1:
            end = chapter_starts[j + 1]
        else:
            # For last chapter, look for ending markers
            end = len(lines)
            for k in range(content_start, len(lines)):
                if re.match(r'^(THE END|FIN|FINIS|END OF|EPILOGUE|\*\*\*)', lines[k], re.IGNORECASE):
                    end = k
                    break
        
        # Extract chapter text
        chapter_lines = lines[content_start:end]
        chapter_text = '\n'.join(chapter_lines).strip()
        
        # Only add if substantial content
        if chapter_text and len(chapter_text) > 100:
            chapters.append(chapter_text)
    
    try:
        from services.logger import get_logger
        get_logger("routes.books").info("chapters_extracted", extra={"component": "routes.books", "count": len(chapters)})
    except Exception:
        pass
    return chapters if chapters else None

@router.get("/library", response_class=HTMLResponse)
async def library_page(request: Request):
    """Library page showing all books"""
    context = get_base_context(request)
    
    try:
        # Include adaptation counts to satisfy template expectations
        books = await database.get_all_books_with_adaptations()
        stats = await database.get_dashboard_stats()
        
        context["books"] = books
        context["stats"] = stats
        context["total_pages"] = 1
        context["current_page"] = 1
        
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.books").error("library_page_error", extra={"component":"routes.books","error":str(e),"request_id": getattr(request.state, 'request_id', None)})
        context["books"] = []
        context["stats"] = {
            "total_books": 0,
            "total_adaptations": 0,
            "active_books": 0,
            "total_images": 0
        }
        context["total_pages"] = 1
        context["current_page"] = 1
    
    return templates.TemplateResponse("pages/library.html", context)

@router.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    """Book import page"""
    context = get_base_context(request)
    
    try:
        books = await database.get_all_books()
        context["recent_books"] = books[:5] if books else []
    except:
        context["recent_books"] = []
    
    return templates.TemplateResponse("pages/import.html", context)

@router.post("/import/file")
async def import_file(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    author: str = Form(""),
    file: UploadFile = File(...)
):
    """Import book from uploaded file"""
    
    process_id = str(uuid.uuid4())
    processing_states[process_id] = {"status": "starting", "progress": 0}
    
    try:
        if not file.filename.endswith(('.txt', '.md')):
            raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")
        
        processing_states[process_id] = {"status": "reading_file", "progress": 25}
        content = await file.read()
        text_content = content.decode('utf-8')
        
        if len(text_content.strip()) < 100:
            raise HTTPException(status_code=400, detail="File content too short")
        
        from services.logger import get_logger, wrap_async_bg
        req_id = getattr(request.state, 'request_id', None)
        background_tasks.add_task(
            wrap_async_bg(process_book_import, req_id),
            process_id,
            title,
            author,
            text_content,
            "upload"
        )
        
        return JSONResponse({
            "success": True,
            "process_id": process_id,
            "message": "Import started",
            "redirect": f"/books/import/status/{process_id}"
        })
        
    except Exception as e:
        processing_states[process_id] = {"status": "error", "error": str(e)}
        from services.logger import get_logger
        get_logger("routes.books").error("file_import_error", extra={"component":"routes.books","error":str(e),"process_id": process_id})
        return JSONResponse({
            "success": False,
            "message": str(e)
        })

@router.post("/import/url")
async def import_url(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    author: str = Form(""),
    url: str = Form(...)
):
    """Import book from URL"""
    
    process_id = str(uuid.uuid4())
    processing_states[process_id] = {"status": "starting", "progress": 0}
    
    try:
        import requests
        
        processing_states[process_id] = {"status": "fetching_url", "progress": 25}
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        text_content = response.text
        
        if len(text_content.strip()) < 100:
            raise HTTPException(status_code=400, detail="Content too short")
        
        from services.logger import wrap_async_bg
        req_id = getattr(request.state, 'request_id', None)
        background_tasks.add_task(
            wrap_async_bg(process_book_import, req_id),
            process_id,
            title,
            author,
            text_content,
            "url"
        )
        
        return JSONResponse({
            "success": True,
            "process_id": process_id,
            "message": "Import started",
            "redirect": f"/books/import/status/{process_id}"
        })
        
    except Exception as e:
        processing_states[process_id] = {"status": "error", "error": str(e)}
        from services.logger import get_logger
        get_logger("routes.books").error("url_import_error", extra={"component":"routes.books","error":str(e),"process_id": process_id, "url": url})
        return JSONResponse({
            "success": False,
            "message": str(e)
        })

@router.get("/import/status/{process_id}")
async def import_status(request: Request, process_id: str):
    """Check import status"""
    if process_id in processing_states:
        state = processing_states[process_id]
        
        if state["status"] == "completed":
            result = {
                "status": "completed",
                "book_id": state.get("book_id"),
                "title": state.get("title"),
                "word_count": state.get("word_count"),
                "chapter_count": state.get("chapter_count")
            }
            
            del processing_states[process_id]
            return JSONResponse(result)
            
        elif state["status"] == "error":
            result = {
                "status": "error",
                "error": state.get("error", "Unknown error")
            }
            
            del processing_states[process_id]
            return JSONResponse(result)
        else:
            return JSONResponse({
                "status": state["status"],
                "progress": state.get("progress", 0)
            })
    else:
        return JSONResponse({"status": "not_found"})

@router.get("/{book_id}/details")
async def book_details(request: Request, book_id: int):
    """Get book details"""
    context = get_base_context(request)
    
    try:
        book = await database.get_book_details(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        context["book"] = book
        return templates.TemplateResponse("pages/book_details.html", context)
        
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.books").error("book_details_error", extra={"component":"routes.books","error":str(e), "book_id": book_id, "request_id": getattr(request.state, 'request_id', None)})
        raise HTTPException(status_code=500, detail="Failed to load book details")


@router.get("/{book_id}/deletion-info")
async def deletion_info(book_id: int):
    """Return counts of related records and files for confirmation UI."""
    try:
        import os
        import database_fixed as db
        # Count adaptations
        conn = db.get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM adaptations WHERE book_id = ?", (book_id,))
            adaptation_count = cur.fetchone()[0] or 0
            cur.execute("SELECT COUNT(*) FROM chapters WHERE adaptation_id IN (SELECT adaptation_id FROM adaptations WHERE book_id = ?)", (book_id,))
            chapter_count = cur.fetchone()[0] or 0
        finally:
            conn.close()
        # Count images on filesystem (simple file count under per-book folder)
        image_count = 0
        try:
            base = os.path.join('generated_images', str(book_id))
            if os.path.isdir(base):
                for root, dirs, files in os.walk(base):
                    image_count += len([f for f in files if not f.startswith('.')])
        except Exception:
            image_count = 0
        return JSONResponse({
            "book_id": book_id,
            "adaptation_count": int(adaptation_count),
            "chapter_count": int(chapter_count),
            "image_count": int(image_count),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.delete("/{book_id}")
async def delete_book(book_id: int):
    """Delete a book completely: DB cascade, run-tracking cleanup, and filesystem removal."""
    try:
        success = await database.delete_book_completely(book_id)
        if success:
            return JSONResponse({"success": True, "message": "Book deleted successfully"})
        else:
            raise HTTPException(status_code=400, detail="Failed to delete book")
    except Exception as e:
        from services.logger import get_logger
        get_logger("routes.books").error("delete_book_error", extra={"component":"routes.books","error":str(e), "book_id": book_id})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-characters")
async def analyze_characters(book_id: int = Form(...)):
    """
    Enhanced character analysis with comprehensive error handling and debugging
    """
    from services.logger import get_logger
    log = get_logger("routes.books")
    log.info("analyze_characters_start", extra={"book_id": book_id})
    
    try:
        # Step 1: Validate OpenAI configuration
        log.info("validate_openai_config_start", extra={"book_id": book_id})
        
        if not config.OPENAI_API_KEY:
            error_msg = "OpenAI API key not found in environment variables"
            log.error("openai_missing_api_key", extra={"book_id": book_id, "error": error_msg})
            return JSONResponse({
                "success": False, 
                "error": "Configuration Error",
                "message": error_msg,
                "debug_info": "Check your .env file for OPENAI_API_KEY"
            })
        
        if config.OPENAI_API_KEY == "YOUR_KEY_HERE" or not config.OPENAI_API_KEY.startswith("sk-"):
            error_msg = "OpenAI API key appears to be invalid format"
            log.error("openai_api_key_invalid_format", extra={"book_id": book_id, "error": error_msg})
            return JSONResponse({
                "success": False, 
                "error": "Configuration Error",
                "message": error_msg,
                "debug_info": "API key should start with 'sk-'"
            })
        
        log.info("openai_api_key_ok", extra={"book_id": book_id})
        
        # Step 2: Get book details
        log.info("get_book_details_start", extra={"book_id": book_id})
        
        book = await database.get_book_details(book_id)
        if not book:
            error_msg = f"Book with ID {book_id} not found in database"
            log.error("book_not_found", extra={"book_id": book_id, "error": error_msg})
            return JSONResponse({
                "success": False, 
                "error": "Book Not Found",
                "message": error_msg
            })
        
        log.info("book_found", extra={"book_id": book_id, "title": book.get('title'), "author": book.get('author')})
        
        # Step 3: Validate file path and read content
        log.info("read_book_content_start", extra={"book_id": book_id})

        # Support both legacy key ('path') and new column ('original_content_path')
        file_path = book.get('path') or book.get('original_content_path')
        
        if not file_path:
            error_msg = "Book file path not found in database"
            log.error("book_file_path_missing", extra={"book_id": book_id, "error": error_msg})
            return JSONResponse({
                "success": False,
                "error": "File Path Error",
                "message": error_msg,
                "debug_info": f"Book record: {book}"
            })
        
        if not os.path.exists(file_path):
            error_msg = f"Book file not found at path: {file_path}"
            log.error("book_file_not_found", extra={"book_id": book_id, "file_path": file_path, "error": error_msg})
            return JSONResponse({
                "success": False,
                "error": "File Not Found",
                "message": error_msg,
                "debug_info": f"Expected path: {file_path}"
            })
        
        # Read file content with fallback encoding
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                log.warning("encoding_fallback_latin1", extra={"book_id": book_id, "file_path": file_path})
            except Exception as e:
                error_msg = f"Failed to read file with any encoding: {str(e)}"
                log.error("book_file_read_error_all_encodings", extra={"book_id": book_id, "file_path": file_path, "error": error_msg})
                return JSONResponse({
                    "success": False,
                    "error": "File Reading Error",
                    "message": error_msg
                })
        except Exception as e:
            error_msg = f"Failed to read book file: {str(e)}"
            log.error("book_file_read_error", extra={"book_id": book_id, "file_path": file_path, "error": error_msg})
            return JSONResponse({
                "success": False,
                "error": "File Reading Error",
                "message": error_msg
            })
        
        log.info("content_loaded", extra={"book_id": book_id, "content_len": len(content)})
        
        # Step 4: Test OpenAI connection with simple request
        log.info("openai_test_start", extra={"book_id": book_id})

        try:
            # Use model from settings if available
            model_name = await database.get_setting("DEFAULT_GPT_MODEL", getattr(config, "DEFAULT_GPT_MODEL", "gpt-4o-mini"))
            # Simple test request via chat_helper (version-agnostic)
            test_text, err = await chat_helper.generate_chat_text(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Respond with exactly: 'API test successful'"}
                ],
                model=model_name,
                temperature=0,
                max_tokens=10,
            )
            if err:
                raise Exception(err)
            test_result = (test_text or "").strip()
            log.info("openai_test_ok", extra={"book_id": book_id, "result": test_result, "model": model_name})

        except Exception as e:
            error_msg = f"OpenAI authentication failed: {str(e)}"
            log.error("openai_test_failed", extra={"book_id": book_id, "error": error_msg, "model": model_name if 'model_name' in locals() else None})
            return JSONResponse({
                "success": False,
                "error": "Authentication Error",
                "message": "Invalid OpenAI API key",
                "debug_info": str(e)
            })

        log.info("analyze_characters_step5_start", extra={"book_id": book_id, "content_len": len(content)})
        
        # Use smaller chunks for more reliable processing
        chunk_size = 8000  # Reduced from 15000 for better reliability
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            chunks.append(chunk)
        
        log.info("chunks_ready", extra={"book_id": book_id, "chunks": len(chunks), "chunk_size": chunk_size})
        
        all_characters = set()
        successful_chunks = 0
        failed_chunks = 0
        
        # Helper: classify retriable errors
        def _is_retriable_error(err: Exception | str) -> bool:
            msg = str(err).lower()
            retriable_markers = [
                "rate limit", "429", "timeout", "timed out", "temporar", "unavailable",
                "apiconnectionerror", "connection", "reset", "503", "502", "504", "server error"
            ]
            return any(m in msg for m in retriable_markers)
        
        # Use model from settings once
        model_name = await database.get_setting("DEFAULT_GPT_MODEL", getattr(config, "DEFAULT_GPT_MODEL", "gpt-4o-mini"))
        
        # Process chunks with controlled retries and error classification
        max_retries = int(os.getenv("MAX_RETRIES", "2"))
        for idx, chunk in enumerate(chunks):
            log.info("chunk_analyze_start", extra={"book_id": book_id, "chunk_index": idx + 1, "total_chunks": len(chunks), "model": model_name})
            
            # Skip very short chunks
            if len(chunk.strip()) < 100:
                log.info("chunk_skipped_short", extra={"book_id": book_id, "chunk_index": idx + 1})
                continue
            
            prompt = f"""Extract character names from this section of "{book['title']}".
Find ALL characters mentioned: main characters, minor characters, named people, animals with names.
Only return actual character names, not descriptions or titles alone.

Text section:
{chunk[:4000]}

Return ONLY comma-separated character names. If no characters found, return "None"."""
            
            attempt = 0
            while True:
                try:
                    text, err = await chat_helper.generate_chat_text(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": "You are an expert at identifying character names in literature. Extract only actual names of characters."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=300,
                    )
                    if err:
                        raise Exception(err)
                    chunk_characters = (text or "").strip()
                    if chunk_characters and chunk_characters.lower() != "none":
                        characters_in_chunk = [c.strip() for c in chunk_characters.split(',') if c.strip() and len(c.strip()) > 1]
                        all_characters.update(characters_in_chunk)
                        log.info("chunk_characters_found", extra={"book_id": book_id, "chunk_index": idx + 1, "found": len(characters_in_chunk)})
                    else:
                        log.info("chunk_no_characters", extra={"book_id": book_id, "chunk_index": idx + 1})
                    successful_chunks += 1
                    # Small pacing delay
                    await asyncio.sleep(0.05)
                    break
                except Exception as e:
                    retriable = _is_retriable_error(e)
                    if retriable and attempt < max_retries:
                        delay = min(0.5 * (2 ** attempt), 3.0) * (0.8 + 0.4 * random.random())
                        log.warning("chunk_retry", extra={"book_id": book_id, "chunk_index": idx + 1, "attempt": attempt + 1, "max_retries": max_retries, "delay": round(delay, 3), "error": str(e)})
                        await asyncio.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        error_class = "retriable" if retriable else "non_retriable"
                        log.error("chunk_failed", extra={"book_id": book_id, "chunk_index": idx + 1, "attempt": attempt, "error_class": error_class, "error": str(e)})
                        failed_chunks += 1
                        break
        
        log.info("chunks_processed", extra={"book_id": book_id, "ok": successful_chunks, "failed": failed_chunks})
        
        # Step 6: Clean and deduplicate characters
        log.info("clean_dedupe_start", extra={"book_id": book_id})
        
        unique_characters = []
        seen_lower = set()
        
        for char in sorted(all_characters):
            if char and len(char) > 1 and len(char) < 50:  # Reasonable name length
                char_clean = char.strip().strip('"').strip("'")
                char_lower = char_clean.lower()
                
                # Skip common non-character words
                skip_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'chapter', 'book', 'story', 'tale'}
                if char_lower not in skip_words and char_lower not in seen_lower:
                    seen_lower.add(char_lower)
                    unique_characters.append(char_clean)
        
        log.info("characters_unique", extra={"book_id": book_id, "count": len(unique_characters), "preview": unique_characters[:10]})
        
        # Step 7: Detect chapters and update database
        log.info("detect_chapters_start", extra={"book_id": book_id})
        
        try:
            chapter_count = detect_chapters_universal(content)
            word_count = len(content.split())
            
            log.info("analysis_results", extra={"book_id": book_id, "word_count": word_count, "chapter_count": chapter_count})
            
            # Update database
            await database.update_book_analysis(
                book_id, 
                word_count, 
                chapter_count, 
                unique_characters
            )
            
            log.info("database_updated", extra={"book_id": book_id})
            
        except Exception as e:
            log.warning("database_update_failed", extra={"book_id": book_id, "error": str(e)})
            # Continue anyway, we still have the characters
            chapter_count = 0
            word_count = len(content.split())
        
        # Step 8: Return success response
        log.info("analyze_characters_done", extra={"book_id": book_id, "unique_count": len(unique_characters)})
        
        return JSONResponse({
            "success": True,
            "characters": unique_characters,
            "message": f"Successfully found {len(unique_characters)} characters",
            "word_count": word_count,
            "chapter_count": chapter_count,
            "debug_info": {
                "chunks_processed": successful_chunks,
                "chunks_failed": failed_chunks,
                "total_chunks": len(chunks),
                "content_length": len(content)
            }
        })
        
    except Exception as e:
        error_msg = f"Unexpected error during character analysis: {str(e)}"
        log.error("analyze_characters_exception", extra={"book_id": book_id, "error": error_msg})
        import traceback
        return JSONResponse({
            "success": False,
            "error": "Analysis Error",
            "message": "Character analysis failed due to an unexpected error",
            "debug_info": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        })

# Background processing functions
async def process_book_import(process_id: str, title: str, author: str, content: str, source_type: str):
    """Process book import with universal analysis"""
    try:
        processing_states[process_id] = {"status": "validating", "progress": 50}
        
        word_count = len(content.split())
        chapter_count = detect_chapters_universal(content)
        
        from services.logger import get_logger
        get_logger("routes.books").info("import_analysis", extra={
            "component":"routes.books",
            "title": title,
            "author": author,
            "word_count": word_count,
            "chapter_count": chapter_count,
            "process_id": process_id
        })
        
        processing_states[process_id] = {"status": "saving", "progress": 75}
        
        book_id = await database.import_book(title, author, content, source_type)
        
        if book_id:
            await database.update_book_analysis(book_id, word_count, chapter_count)
            
            processing_states[process_id] = {
                "status": "completed",
                "progress": 100,
                "book_id": book_id,
                "title": title,
                "word_count": word_count,
                "chapter_count": chapter_count
            }
            
            from services.logger import get_logger
            get_logger("routes.books").info("import_success", extra={"component":"routes.books","book_id": book_id, "process_id": process_id})
        else:
            raise ValueError("Database save failed")
            
    except Exception as e:
        processing_states[process_id] = {"status": "error", "error": str(e)}
        from services.logger import get_logger
        get_logger("routes.books").error("import_failed", extra={"component":"routes.books","error": str(e), "process_id": process_id})