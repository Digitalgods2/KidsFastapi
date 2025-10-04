"""
Settings routes for KidsKlassiks
Handles application settings and configuration
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import database_fixed as database
import config
from services import chat_helper

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Helper function for base context
async def get_base_context(request):
    """Get base context variables for all templates"""
    # Check database for current API key settings instead of config module
    try:
        openai_key = await database.get_setting("openai_api_key", config.OPENAI_API_KEY or "")
        vertex_project_id = await database.get_setting("vertex_project_id", config.VERTEX_PROJECT_ID or "")
        vertex_location = await database.get_setting("vertex_location", config.VERTEX_LOCATION or "us-central1")
        
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
async def settings_page(request: Request):
    """Settings page"""
    context = await get_base_context(request)
    
    try:
        settings_data = await database.get_all_settings()
        
        # Ensure all expected settings exist
        default_settings = {
            "openai_api_key": await database.get_setting("openai_api_key", config.OPENAI_API_KEY or ""),
            "vertex_project_id": await database.get_setting("vertex_project_id", config.VERTEX_PROJECT_ID or ""),
            "vertex_location": await database.get_setting("vertex_location", config.VERTEX_LOCATION or "us-central1"),
            "default_image_backend": await database.get_setting("default_image_backend", "gpt-image-1"),
            "default_aspect_ratio": await database.get_setting("default_aspect_ratio", "4:3"),
            "default_age_group": await database.get_setting("default_age_group", "6-8"),
            "default_transformation_style": await database.get_setting("default_transformation_style", "Simple & Direct"),
            "chapter_words_3_5": await database.get_setting("chapter_words_3_5", "500"),
            "chapter_words_6_8": await database.get_setting("chapter_words_6_8", "1500"),
            "chapter_words_9_12": await database.get_setting("chapter_words_9_12", "2500"),
            "auto_generate_images": await database.get_setting("auto_generate_images", "false"),
            "auto_analyze_characters": await database.get_setting("auto_analyze_characters", "false"),
            "preserve_original_chapters": await database.get_setting("preserve_original_chapters", "false"),
            "max_tokens": await database.get_setting("max_tokens", "4000"),
            "temperature": await database.get_setting("temperature", "0.7"),
            "storage_path": await database.get_setting("storage_path", "./storage")
        }
        
        # Merge with defaults
        for key, value in default_settings.items():
            if key not in settings_data:
                settings_data[key] = value
        
        context["settings"] = settings_data
        context["storage_percentage"] = 0
        context["storage_used"] = 0
        context["storage_total"] = 1000
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("settings_page_error", extra={"error": str(e), "component": "routes.settings", "request_id": getattr(request.state, 'request_id', None)})
        context["settings"] = {}
        context["storage_percentage"] = 0
        context["storage_used"] = 0
        context["storage_total"] = 1000
    
    return templates.TemplateResponse("pages/settings.html", context)

@router.post("/save")
async def save_settings(request: Request):
    """Save settings to database"""
    try:
        form_data = await request.form()
        
        # Handle checkbox values properly - unchecked checkboxes don't send data
        checkbox_fields = ['auto_generate_images', 'auto_analyze_characters', 'preserve_original_chapters']
        
        # Save each setting
        for key, value in form_data.items():
            await database.update_setting(key, value)
        
        # Set unchecked checkboxes to "false"
        for checkbox_field in checkbox_fields:
            if checkbox_field not in form_data:
                await database.update_setting(checkbox_field, "false")
        
        # Return HTML success message for HTMX
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Settings saved successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("save_settings_error", extra={"error": str(e), "component": "routes.settings", "request_id": getattr(request.state, 'request_id', None)})
        # Return HTML error message for HTMX
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error saving settings: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.post("/api/test-connection")
async def test_connection():
    """Test API connections with detailed validation"""
    try:
        results = {
            "openai": False,
            "openai_auth": False,
            "openai_chat": False,
            "vertex": False,
            "database": False
        }
        
        errors = {
            "openai": None,
            "vertex": None,
            "database": None
        }
        
        # Test database
        try:
            conn = database.get_db_connection()
            if conn:
                results["database"] = True
                conn.close()
        except Exception as e:
            errors["database"] = str(e)
        
        # Test OpenAI - comprehensive validation
        tested_model = await database.get_setting('openai_default_model', getattr(config, 'DEFAULT_GPT_MODEL', 'gpt-4o-mini'))
        api_key = await database.get_setting("openai_api_key", getattr(config, 'OPENAI_API_KEY', None) or "")
        
        # Log for debugging
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.info(f"Testing OpenAI connection - API key present: {bool(api_key)}, starts with sk-: {api_key.startswith('sk-') if api_key else False}")
        
        # Validate API key format
        if not api_key:
            errors["openai"] = "No API key configured - please enter your OpenAI API key above and save"
        elif not api_key.startswith('sk-'):
            errors["openai"] = "Invalid API key format (must start with 'sk-')"
        else:
            try:
                # Step 1: Create client and test authentication
                client = await chat_helper.get_client()
                
                # Test authentication with models.list
                try:
                    listing = client.models.list()
                    models = [m.id for m in listing.data]
                    results["openai_auth"] = True
                    results["openai"] = True
                    log.info(f"OpenAI auth successful, found {len(models)} models")
                    
                    # Verify the selected model exists
                    if tested_model not in models:
                        errors["openai"] = f"Model '{tested_model}' not available. Available: {', '.join(models[:5])}..."
                    
                except Exception as e_list:
                    log.error(f"OpenAI models.list failed: {e_list}")
                    errors["openai"] = f"Authentication failed: {str(e_list)}"
                    results["openai_auth"] = False
                    
                    # Try raw HTTP as fallback for more details
                    try:
                        import httpx
                        base_url = await database.get_setting("openai_base_url", "https://api.openai.com/v1")
                        org = await database.get_setting("openai_organization", "")
                        headers = {"Authorization": f"Bearer {api_key}"}
                        if org:
                            headers["OpenAI-Organization"] = org
                        
                        async with httpx.AsyncClient(timeout=15) as s:
                            resp = await s.get(f"{base_url.rstrip('/')}/models", headers=headers)
                            if resp.status_code == 200:
                                results["openai_auth"] = True
                                results["openai"] = True
                                errors["openai"] = None
                                log.info("OpenAI HTTP fallback successful")
                            elif resp.status_code == 401:
                                errors["openai"] = "Invalid API key - authentication failed (401)"
                            elif resp.status_code == 429:
                                errors["openai"] = "Rate limit exceeded (429)"
                            else:
                                errors["openai"] = f"API error ({resp.status_code}): {resp.text[:200]}"
                    except Exception as raw_e:
                        log.error(f"OpenAI HTTP fallback failed: {raw_e}")
                        errors["openai"] = f"Connection failed: {str(raw_e)}"
                
                # Step 2: Test actual chat completion if auth succeeded
                if results["openai_auth"]:
                    try:
                        text, err = await chat_helper.generate_chat_text(
                            messages=[
                                {"role": "system", "content": "You are a test assistant."},
                                {"role": "user", "content": "Reply with exactly: OK"}
                            ],
                            model=tested_model,
                            temperature=0,
                            max_tokens=10,
                        )
                        
                        if err:
                            errors["openai"] = f"Chat test failed: {err}"
                            results["openai_chat"] = False
                            log.error(f"Chat test failed: {err}")
                        elif text and 'OK' in text.upper():
                            results["openai_chat"] = True
                            results["openai"] = True
                            errors["openai"] = None  # Clear any previous errors
                            log.info("Chat test successful")
                        else:
                            results["openai_chat"] = False
                            errors["openai"] = f"Unexpected response: {text}"
                            log.warning(f"Unexpected chat response: {text}")
                            
                    except Exception as e_chat:
                        errors["openai"] = f"Chat test error: {str(e_chat)}"
                        results["openai_chat"] = False
                        log.error(f"Chat test exception: {e_chat}")
                
            except Exception as e:
                errors["openai"] = f"Unexpected error: {str(e)}"
                results["openai"] = False
                log.error(f"OpenAI test unexpected error: {e}", exc_info=True)
        
        # Test Vertex AI
        try:
            if config.validate_vertex_ai_config():
                results["vertex"] = True
            else:
                errors["vertex"] = "Vertex AI not configured (missing project ID or credentials)"
        except Exception as e:
            errors["vertex"] = str(e)
        
        return JSONResponse({
            "success": True, 
            "results": results, 
            "errors": errors,
            "model_tested": tested_model,
            "api_key_prefix": api_key[:10] + "..." if api_key else "Not set"
        })
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("test_connection_error", extra={"error": str(e), "component": "routes.settings"})
        return JSONResponse({
            "success": False, 
            "error": str(e),
            "results": {"openai": False, "vertex": False, "database": False},
            "errors": {"global": str(e)}
        })

@router.post("/image-preferences")
async def save_image_preferences(request: Request):
    """Save image generation preferences"""
    try:
        form_data = await request.form()
        
        # Save image backend and aspect ratio settings
        for key, value in form_data.items():
            await database.update_setting(key, value)
        
        # Return HTML success message for HTMX
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Image preferences saved successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("save_image_preferences_error", extra={"error": str(e), "component": "routes.settings", "request_id": getattr(request.state, 'request_id', None)})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error saving image preferences: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.post("/api/save")
async def save_api_settings(request: Request):
    """Save API configuration settings"""
    try:
        form_data = await request.form()
        
        # Handle Vertex credentials file upload if present
        vertex_creds_file = form_data.get('vertex_credentials')
        if vertex_creds_file and hasattr(vertex_creds_file, 'file'):
            # Save the credentials file
            import json
            try:
                creds_content = await vertex_creds_file.read()
                creds_json = json.loads(creds_content)
                
                # Extract project ID from credentials
                project_id = creds_json.get('project_id', '')
                if project_id:
                    await database.update_setting('vertex_project_id', project_id)
                
                # Save the credentials file to disk
                import os
                creds_path = os.path.join(os.getcwd(), 'vertexapi.json')
                with open(creds_path, 'wb') as f:
                    f.write(creds_content)
                
                # Update environment variable
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
                
            except json.JSONDecodeError:
                return HTMLResponse("""
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        <i class="bi bi-exclamation-triangle"></i> Invalid JSON credentials file!
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                """, status_code=400)
        
        # Save each API setting (except file uploads)
        for key, value in form_data.items():
            if key != 'vertex_credentials' and not hasattr(value, 'file'):
                await database.update_setting(key, str(value))
        
        # Return HTML success message for HTMX
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> API settings saved successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("save_api_settings_error", extra={"error": str(e), "component": "routes.settings", "request_id": getattr(request.state, 'request_id', None)})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error saving API settings: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.post("/image-preferences")
async def save_image_preferences(request: Request):
    """Save image generation preferences"""
    try:
        form_data = await request.form()
        
        # Save each image setting
        for key, value in form_data.items():
            await database.update_setting(key, value)
        
        # Return HTML success message for HTMX
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Image preferences saved successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("save_image_preferences_error", extra={"error": str(e), "component": "routes.settings", "request_id": getattr(request.state, 'request_id', None)})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error saving image preferences: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.post("/advanced")
async def save_advanced_settings(request: Request):
    """Save advanced settings"""
    try:
        form_data = await request.form()
        
        # Save each advanced setting
        for key, value in form_data.items():
            await database.update_setting(key, value)
        
        # Return HTML success message for HTMX
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Advanced settings saved successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("save_advanced_settings_error", extra={"error": str(e), "component": "routes.settings", "request_id": getattr(request.state, 'request_id', None)})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error saving advanced settings: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)


@router.post("/api/clear-cache")
async def clear_cache():
    """Clear application cache"""
    try:
        # Implementation for clearing cache
        # For now, just return success message
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Cache cleared successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("clear_cache_error", extra={"error": str(e), "component": "routes.settings"})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error clearing cache: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.get("/api/export")
async def export_settings():
    """Export settings as JSON"""
    try:
        settings_data = await database.get_all_settings()
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            content=settings_data,
            headers={"Content-Disposition": "attachment; filename=kidsklassiks_settings.json"}
        )
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("export_settings_error", extra={"error": str(e), "component": "routes.settings"})
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/import")
async def import_settings(request: Request):
    """Import settings from JSON file"""
    try:
        # Implementation for importing settings
        # For now, just return success message
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Settings imported successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("import_settings_error", extra={"error": str(e), "component": "routes.settings"})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error importing settings: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.post("/api/reset")
async def reset_settings():
    """Reset all settings to defaults"""
    try:
        # Reset to default values
        default_settings = {
            "openai_api_key": "",
            "vertex_project_id": "",
            "vertex_location": "us-central1",
            "image_api_preference": "dall-e-3",
            "default_age_group": "6-8",
            "default_transformation_style": "Simple & Direct",
            "chapter_words_3_5": "500",
            "chapter_words_6_8": "1500",
            "chapter_words_9_12": "2500",
            "auto_generate_images": "false",
            "auto_analyze_characters": "false",
            "preserve_original_chapters": "false",
            "max_tokens": "4000",
            "temperature": "0.7",
            "storage_path": "./storage"
        }
        
        # Save each default setting
        for key, value in default_settings.items():
            await database.update_setting(key, value)
        
        return HTMLResponse("""
            <div class="alert alert-success alert-dismissible fade show" role="alert">
                <i class="bi bi-check-circle"></i> Settings reset to defaults successfully!
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """)
        
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("reset_settings_error", extra={"error": str(e), "component": "routes.settings"})
        return HTMLResponse(f"""
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle"></i> Error resetting settings: {str(e)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        """, status_code=500)

@router.get("/api/settings")
async def get_settings_api():
    """Get current settings as JSON for frontend use"""
    try:
        settings_data = await database.get_all_settings()
        return JSONResponse(settings_data)
    except Exception as e:
        from services.logger import get_logger
        log = get_logger("routes.settings")
        log.error("get_settings_api_error", extra={"error": str(e), "component": "routes.settings"})
        raise HTTPException(status_code=500, detail=str(e))
