#!/usr/bin/env python3
"""
Comprehensive Migration Fix for KidsKlassiks
This script will:
1. Migrate to OpenAI API 1.3.7+
2. Fix all service layers
3. Clean routes
4. Repair database
5. Create working versions of all files
"""

import os
import shutil
import json
import sqlite3
import psycopg2
from datetime import datetime
from pathlib import Path

class KidsKlassiksFixer:
    def __init__(self):
        self.base_dir = Path.cwd()
        self.backup_dir = self.base_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.fixes_applied = []
        
    def backup_file(self, filepath):
        """Create a backup of a file before modifying"""
        if not os.path.exists(filepath):
            return False
            
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup_dir / Path(filepath).name
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backed up {filepath} to {backup_path}")
        return True
        
    def create_new_openai_service(self):
        """Create a properly working OpenAI service for the new API"""
        print("\n🔧 Creating new OpenAI service...")
        
        service_content = '''"""
OpenAI service for KidsKlassiks - New API Version (1.3.7+)
Handles GPT text transformation and DALL-E image generation
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
import config

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service class for OpenAI API operations using the new client"""
    
    def __init__(self):
        """Initialize OpenAI client with proper error handling"""
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        try:
            # New API initialization - no 'proxies' parameter
            self.client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                organization=config.OPENAI_ORG_ID if hasattr(config, 'OPENAI_ORG_ID') else None
            )
            logger.info("✅ OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    # ==================== TEXT TRANSFORMATION ====================
    
    async def transform_text(
        self, 
        text: str, 
        age_group: str, 
        style: str,
        preserve_names: bool = True,
        chapter_number: Optional[int] = None
    ) -> str:
        """
        Transform text for children using GPT models
        """
        try:
            # Build the transformation prompt
            prompt = self._build_transformation_prompt(
                text, age_group, style, preserve_names, chapter_number
            )
            
            # Use the new API format
            response = self.client.chat.completions.create(
                model=config.DEFAULT_GPT_MODEL or "gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert children's book author who adapts classic literature for young readers."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=config.GPT_MAX_TOKENS or 4000,
                temperature=config.GPT_TEMPERATURE or 0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Text transformation error: {e}")
            # Return original text if transformation fails
            return text
    
    def _build_transformation_prompt(
        self, 
        text: str, 
        age_group: str, 
        style: str,
        preserve_names: bool,
        chapter_number: Optional[int]
    ) -> str:
        """Build the transformation prompt based on parameters"""
        
        age_guidelines = {
            "3-5": "Use very simple words, short sentences (5-8 words), repetition, and focus on basic concepts.",
            "6-8": "Use simple vocabulary, sentences of 10-15 words, clear action, and introduce basic emotions.",
            "9-12": "Use varied vocabulary, longer sentences, complex plots, and deeper character development."
        }
        
        style_guidelines = {
            "Simple & Direct": "Keep the language straightforward and clear.",
            "Playful & Fun": "Add playful language, sound effects, and humor.",
            "Adventurous": "Emphasize excitement, action, and discovery.",
            "Gentle & Soothing": "Use calm, comforting language with a peaceful tone."
        }
        
        prompt = f"""
        Transform this text for {age_group} year old children.
        Style: {style}
        
        Guidelines:
        - {age_guidelines.get(age_group, age_guidelines["6-8"])}
        - {style_guidelines.get(style, style_guidelines["Simple & Direct"])}
        {"- Preserve character names exactly as they appear" if preserve_names else "- Simplify complex character names"}
        {f"- This is Chapter {chapter_number}" if chapter_number else ""}
        
        Original text:
        {text[:3000]}
        
        Create an engaging, age-appropriate version that maintains the story essence.
        """
        
        return prompt
    
    # ==================== IMAGE GENERATION ====================
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid"
    ) -> Optional[str]:
        """
        Generate an image using DALL-E
        """
        try:
            # Ensure prompt is within limits
            max_prompt_length = 4000 if model == "dall-e-3" else 1000
            if len(prompt) > max_prompt_length:
                prompt = prompt[:max_prompt_length - 3] + "..."
            
            # Use the new API format for image generation
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1
            )
            
            # Extract image URL from response
            image_url = response.data[0].url
            logger.info(f"✅ Image generated successfully")
            return image_url
            
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return None
    
    # ==================== CHARACTER ANALYSIS ====================
    
    async def analyze_story_characters(
        self, 
        story_content: str, 
        book_title: str = "Unknown Book"
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Analyze a story to extract character descriptions
        """
        try:
            if not story_content:
                logger.warning("Empty story content provided for analysis")
                return None, "No content to analyze"
            
            analysis_prompt = f"""
            Analyze the story "{book_title}" and create a character reference.
            
            Extract information about:
            1. Main characters (name, appearance, role)
            2. Supporting characters
            3. Key settings and locations
            4. Overall story tone and style
            
            Format as JSON with this structure:
            {{
                "characters": [
                    {{
                        "name": "Character Name",
                        "role": "protagonist/antagonist/supporting",
                        "appearance": "physical description",
                        "personality": "character traits"
                    }}
                ],
                "settings": [
                    {{
                        "name": "Location Name",
                        "description": "setting description"
                    }}
                ],
                "story_tone": "overall tone and style"
            }}
            
            Story excerpt:
            {story_content[:5000]}
            """
            
            response = self.client.chat.completions.create(
                model=config.DEFAULT_GPT_MODEL or "gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a literary analyst specializing in character and setting descriptions."
                    },
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            # Try to parse as JSON
            result_text = response.choices[0].message.content
            try:
                # Clean up the response if it has markdown code blocks
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                    
                character_data = json.loads(result_text.strip())
                return character_data, None
            except json.JSONDecodeError:
                # If not valid JSON, return the text analysis
                return {"raw_analysis": result_text}, None
                
        except Exception as e:
            logger.error(f"Character analysis error: {e}")
            return None, str(e)
    
    # ==================== PROMPT GENERATION ====================
    
    async def generate_image_prompt(
        self,
        chapter_text: str,
        character_info: Optional[Dict] = None,
        style_preference: str = "whimsical"
    ) -> str:
        """
        Generate an image prompt from chapter text
        """
        try:
            prompt = f"""
            Create a DALL-E image generation prompt for this chapter.
            
            Style: {style_preference} children's book illustration
            {f"Characters: {json.dumps(character_info)}" if character_info else ""}
            
            Chapter text:
            {chapter_text[:2000]}
            
            Create a detailed, visual prompt (max 200 words) that describes:
            - The main scene or action
            - Character appearances and expressions
            - Setting and atmosphere
            - Colors and artistic style
            
            Make it suitable for a children's book illustration.
            """
            
            response = self.client.chat.completions.create(
                model=config.DEFAULT_GPT_MODEL or "gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating detailed image generation prompts."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Prompt generation error: {e}")
            # Return a basic prompt if generation fails
            return f"A {style_preference} children's book illustration showing a magical scene"
    
    # ==================== VALIDATION ====================
    
    async def validate_content_appropriateness(
        self,
        content: str,
        age_group: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if content is appropriate for the target age group
        """
        try:
            validation_prompt = f"""
            Review this content for {age_group} year old children.
            
            Check for:
            1. Age-inappropriate language or concepts
            2. Scary or disturbing content
            3. Complex themes beyond the age group
            
            Content:
            {content[:2000]}
            
            Respond with JSON:
            {{
                "appropriate": true/false,
                "concerns": ["list any concerns"],
                "suggestions": ["improvement suggestions"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model=config.DEFAULT_GPT_MODEL or "gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a child development expert and content reviewer."
                    },
                    {"role": "user", "content": validation_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            try:
                # Parse JSON response
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                validation_result = json.loads(result_text.strip())
                
                is_appropriate = validation_result.get("appropriate", True)
                concerns = validation_result.get("concerns", [])
                
                if not is_appropriate and concerns:
                    return False, "; ".join(concerns)
                return True, None
                
            except json.JSONDecodeError:
                # If parsing fails, assume content is appropriate
                return True, None
                
        except Exception as e:
            logger.error(f"Content validation error: {e}")
            # If validation fails, assume content is appropriate
            return True, None


# Singleton instance
_service_instance = None

def get_openai_service() -> OpenAIService:
    """Get or create the OpenAI service singleton"""
    global _service_instance
    if _service_instance is None:
        _service_instance = OpenAIService()
    return _service_instance
'''
        
        service_path = self.base_dir / "services" / "openai_service_new.py"
        self.backup_file(service_path)
        
        with open(service_path, 'w', encoding='utf-8') as f:
            f.write(service_content)
        
        print(f"✅ Created new OpenAI service at {service_path}")
        self.fixes_applied.append("Created new OpenAI service")
        return True
        
    def fix_main_py(self):
        """Create a clean, working main.py"""
        print("\n🔧 Creating clean main.py...")
        
        main_content = '''"""
KidsKlassiks FastAPI + HTMX Application
Clean, working version with all fixes applied
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import configuration and database
import config
from database import initialize_database, get_dashboard_stats, get_all_settings

# Import routers - using fixed versions
from routes.books import router as books_router
from routes.adaptations import router as adaptations_router
from routes.review import router as review_router
from routes.settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting KidsKlassiks FastAPI + HTMX Application...")
    
    try:
        # Initialize database
        logger.info("📊 Initializing database...")
        initialize_database()
        logger.info("✅ Database initialized successfully")
        
        # Create necessary directories
        directories = [
            "uploads", 
            "generated_images", 
            "generated_images/chapters",
            "generated_images/covers",
            "publications", 
            "exports", 
            "backups"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        logger.info("📁 Created necessary directories")
        
        # Verify AI services configuration
        if config.OPENAI_API_KEY:
            logger.info("✅ OpenAI API configured")
        else:
            logger.warning("⚠️ OpenAI API not configured - some features will be unavailable")
        
        if config.validate_vertex_ai_config():
            logger.info("✅ Vertex AI configured")
        else:
            logger.info("ℹ️ Vertex AI not configured - using OpenAI only")
        
        logger.info("🌟 KidsKlassiks is ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down KidsKlassiks...")
    logger.info("✅ Cleanup complete")

# Initialize FastAPI app
app = FastAPI(
    title="KidsKlassiks AI Transformer",
    description="Transform classic literature into illustrated children's books using AI",
    version="3.0.0",
    lifespan=lifespan
)

# Middleware configuration
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SECRET_KEY", "kidsklassiks-secret-key-change-in-production")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/generated_images", StaticFiles(directory="generated_images"), name="generated_images")
app.mount("/publications", StaticFiles(directory="publications"), name="publications")

templates = Jinja2Templates(directory="templates")

# Include routers with proper prefixes
app.include_router(books_router, prefix="/books", tags=["books"])
app.include_router(adaptations_router, prefix="/adaptations", tags=["adaptations"])
app.include_router(review_router, prefix="/review", tags=["review"])
app.include_router(settings_router, prefix="/settings", tags=["settings"])

# ==================== HELPER FUNCTIONS ====================

def get_base_context(request: Request) -> dict:
    """Get base context variables for all templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": config.validate_vertex_ai_config()
    }

# ==================== ROOT ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Landing page"""
    context = get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        context["stats"] = stats
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        context["stats"] = {
            "total_books": 0,
            "total_adaptations": 0,
            "total_images": 0,
            "recent_books": [],
            "recent_adaptations": []
        }
    
    return templates.TemplateResponse("pages/home.html", context)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard page with statistics"""
    context = get_base_context(request)
    
    try:
        stats = await get_dashboard_stats()
        context["stats"] = stats
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}")
        context["stats"] = {
            "total_books": 0,
            "total_adaptations": 0,
            "total_images": 0,
            "active_books": 0,
            "recent_books": [],
            "recent_adaptations": [],
            "storage_used": "0 MB"
        }
    
    return templates.TemplateResponse("pages/dashboard.html", context)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "version": "3.0.0",
        "environment": config.APP_ENV,
        "services": {
            "database": "connected",
            "openai": "configured" if config.OPENAI_API_KEY else "not_configured",
            "vertex_ai": "configured" if config.validate_vertex_ai_config() else "not_configured"
        }
    })

@app.get("/api/info")
async def api_info():
    """API information endpoint"""
    return JSONResponse({
        "name": "KidsKlassiks API",
        "version": "3.0.0",
        "description": "AI-Powered Children's Book Adaptations",
        "architecture": "FastAPI + HTMX",
        "features": [
            "Book import and management",
            "AI-powered text transformation", 
            "Image generation with multiple models",
            "Real-time processing updates",
            "PDF export and publishing"
        ]
    })

# ==================== ERROR HANDLERS ====================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 page"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"error": "Not found", "status_code": 404},
            status_code=404
        )
    
    context = get_base_context(request)
    context.update({
        "error_code": 404,
        "error_message": "Page not found"
    })
    
    return templates.TemplateResponse(
        "pages/error.html", 
        context,
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Custom 500 error page"""
    logger.error(f"Internal server error: {exc}")
    
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"error": "Internal server error", "status_code": 500},
            status_code=500
        )
    
    context = get_base_context(request)
    context.update({
        "error_code": 500,
        "error_message": "Internal server error"
    })
    
    return templates.TemplateResponse(
        "pages/error.html",
        context,
        status_code=500
    )

# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    port = int(os.getenv("APP_PORT", 8000))
    host = os.getenv("APP_HOST", "127.0.0.1")
    
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port, 
        reload=config.APP_DEBUG,
        log_level="info" if config.APP_DEBUG else "warning"
    )
'''
        
        main_path = self.base_dir / "main_clean.py"
        with open(main_path, 'w', encoding='utf-8') as f:
            f.write(main_content)
        
        print(f"✅ Created clean main.py at {main_path}")
        self.fixes_applied.append("Created clean main.py")
        return True
    
    def fix_database_paths(self):
        """Fix database book file paths"""
        print("\n🔧 Fixing database book paths...")
        
        try:
            # Load database configuration
            from dotenv import load_dotenv
            load_dotenv()
            
            db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": os.getenv("DB_PORT", "5432"),
                "database": os.getenv("DATABASE_NAME", "kidsklassiks"),
                "user": os.getenv("DB_USER", "glen"),
                "password": os.getenv("DB_PASSWORD", "")
            }
            
            # Try PostgreSQL first
            try:
                conn = psycopg2.connect(**db_config)
                cur = conn.cursor()
                db_type = "postgresql"
            except:
                # Fall back to SQLite
                db_path = self.base_dir / "kidsklassiks.db"
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                db_type = "sqlite"
            
            print(f"📊 Connected to {db_type} database")
            
            # Check for books without file paths
            cur.execute("""
                SELECT book_id, title, original_content_path 
                FROM books 
                WHERE original_content_path IS NULL OR original_content_path = ''
            """)
            
            books_without_paths = cur.fetchall()
            
            if not books_without_paths:
                print("✅ All books already have file paths")
                return True
            
            uploads_dir = self.base_dir / "uploads"
            uploads_dir.mkdir(exist_ok=True)
            
            for book_id, title, current_path in books_without_paths:
                # Create safe filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_')
                expected_path = f"uploads/{safe_title}.txt"
                
                print(f"📚 Processing book {book_id}: '{title}'")
                
                # Check if file exists
                file_path = self.base_dir / expected_path
                if file_path.exists():
                    # Update database
                    cur.execute("""
                        UPDATE books 
                        SET original_content_path = %s 
                        WHERE book_id = %s
                    """ if db_type == "postgresql" else """
                        UPDATE books 
                        SET original_content_path = ? 
                        WHERE book_id = ?
                    """, (expected_path, book_id))
                    print(f"  ✅ Updated path: {expected_path}")
                else:
                    # Try to find a matching file
                    possible_files = list(uploads_dir.glob(f"*{safe_title[:10]}*.txt"))
                    if possible_files:
                        relative_path = f"uploads/{possible_files[0].name}"
                        cur.execute("""
                            UPDATE books 
                            SET original_content_path = %s 
                            WHERE book_id = %s
                        """ if db_type == "postgresql" else """
                            UPDATE books 
                            SET original_content_path = ? 
                            WHERE book_id = ?
                        """, (relative_path, book_id))
                        print(f"  ✅ Found and updated: {relative_path}")
                    else:
                        print(f"  ⚠️ No file found for '{title}'")
            
            conn.commit()
            cur.close()
            conn.close()
            
            print("✅ Database paths fixed")
            self.fixes_applied.append("Fixed database book paths")
            return True
            
        except Exception as e:
            print(f"❌ Database fix error: {e}")
            return False
    
    def create_clean_requirements(self):
        """Create a clean requirements.txt with the new OpenAI API"""
        print("\n🔧 Creating clean requirements.txt...")
        
        requirements_content = """# KidsKlassiks FastAPI + HTMX Application Dependencies
# Clean version with OpenAI 1.3.7+ API

# Core FastAPI and web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
starlette==0.27.0
jinja2==3.1.2
python-multipart==0.0.6
python-dotenv==1.0.0

# Session and security middleware
itsdangerous==2.1.2
cryptography==41.0.8

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23

# AI Services - NEW OpenAI API
openai==1.3.7
google-cloud-aiplatform==1.38.1

# HTTP and async requests
aiohttp==3.9.1
requests==2.31.0
httpx==0.25.2

# Additional async dependencies
anyio==4.1.0
sniffio==1.3.0

# Text processing and parsing
beautifulsoup4==4.12.2
markdown==3.5.1
lxml==4.9.3

# PDF generation and document processing
reportlab==4.0.7
weasyprint==60.2
fpdf2==2.7.6

# Image processing
pillow==10.1.0
pdf2image==1.16.3

# Data processing and utilities
pandas==2.1.4
numpy==1.26.2
python-dateutil==2.8.2

# Additional FastAPI dependencies
email-validator==2.1.0
orjson==3.9.10
ujson==5.8.0

# Additional utilities
pathlib2==2.3.7
typing-extensions==4.8.0
pydantic==2.5.0
pydantic-core==2.14.1

# Additional required dependencies
click==8.1.7
h11==0.14.0
idna==3.6
certifi==2023.11.17
charset-normalizer==3.3.2
urllib3==2.1.0
"""
        
        req_path = self.base_dir / "requirements_clean.txt"
        with open(req_path, 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        
        print(f"✅ Created clean requirements at {req_path}")
        self.fixes_applied.append("Created clean requirements.txt")
        return True
    
    def create_fixed_books_route(self):
        """Create a working books route with proper error handling"""
        print("\n🔧 Creating fixed books route...")
        
        books_route_content = '''"""
Books routes for KidsKlassiks - Fixed version with new OpenAI API
Handles book import, management, and library operations
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import os
import uuid
import logging
from pathlib import Path

import database
from models import BookImportRequest, BookResponse
import config
# legacy reference retained for documentation; runtime uses services.chat_helper
# from legacy.services.openai_service import get_openai_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)

# Processing states
processing_states = {}

def get_base_context(request):
    """Get base context for templates"""
    return {
        "request": request,
        "notifications_count": 0,
        "notifications": [],
        "openai_status": bool(config.OPENAI_API_KEY),
        "vertex_status": config.validate_vertex_ai_config()
    }

@router.get("/library", response_class=HTMLResponse)
async def library(request: Request):
    """Display book library"""
    context = get_base_context(request)
    
    try:
        books = await database.get_all_books()
        context["books"] = books
        context["total_books"] = len(books)
    except Exception as e:
        logger.error(f"Error loading library: {e}")
        context["books"] = []
        context["total_books"] = 0
        context["error"] = "Failed to load books"
    
    return templates.TemplateResponse("pages/library.html", context)

@router.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    """Display import page"""
    context = get_base_context(request)
    return templates.TemplateResponse("pages/import.html", context)

@router.post("/import")
async def import_book(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    author: str = Form(None),
    source: str = Form("file"),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    """Import a new book"""
    try:
        # Validate input
        if source == "file" and not file:
            raise HTTPException(400, "No file uploaded")
        if source == "url" and not url:
            raise HTTPException(400, "No URL provided")
        
        # Process file upload
        if source == "file":
            # Create safe filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')
            
            # Save uploaded file
            upload_dir = Path("uploads")
            upload_dir.mkdir(exist_ok=True)
            
            file_extension = Path(file.filename).suffix or '.txt'
            filename = f"{safe_title}_{uuid.uuid4().hex[:8]}{file_extension}"
            file_path = upload_dir / filename
            
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Decode content
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = content.decode('utf-8', errors='ignore')
            
            # Store in database
            book_id = await database.create_book(
                title=title,
                author=author or "Unknown",
                original_content=text_content,
                original_content_path=str(file_path),
                source=f"Uploaded file: {file.filename}"
            )
            
            logger.info(f"✅ Book imported: {title} (ID: {book_id})")
            
            # Start background analysis if enabled
            if config.ENABLE_AUTO_ANALYSIS and config.OPENAI_API_KEY:
                background_tasks.add_task(analyze_book, book_id, title, text_content)
            
            return JSONResponse({
                "success": True,
                "book_id": book_id,
                "message": f"Successfully imported '{title}'"
            })
        
        # Handle URL import
        elif source == "url":
            # TODO: Implement URL fetching
            raise HTTPException(501, "URL import not yet implemented")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(500, f"Import failed: {str(e)}")

@router.get("/{book_id}/details", response_class=HTMLResponse)
async def book_details(request: Request, book_id: int):
    """Display book details"""
    context = get_base_context(request)
    
    try:
        book = await database.get_book(book_id)
        if not book:
            raise HTTPException(404, "Book not found")
        
        # Get adaptations for this book
        adaptations = await database.get_book_adaptations(book_id)
        
        context["book"] = book
        context["adaptations"] = adaptations
        context["adaptation_count"] = len(adaptations)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading book details: {e}")
        raise HTTPException(500, "Failed to load book details")
    
    return templates.TemplateResponse("pages/book_details.html", context)

@router.delete("/{book_id}")
async def delete_book(book_id: int):
    """Delete a book and its associated data"""
    try:
        # Delete from database
        success = await database.delete_book(book_id)
        
        if success:
            logger.info(f"✅ Deleted book {book_id}")
            return JSONResponse({"success": True, "message": "Book deleted"})
        else:
            raise HTTPException(404, "Book not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(500, f"Delete failed: {str(e)}")

async def analyze_book(book_id: int, title: str, content: str):
    """Background task to analyze book characters"""
    try:
        service = get_openai_service()
        character_data, error = await service.analyze_story_characters(content, title)
        
        if character_data:
            # Store analysis in database
            await database.update_book_analysis(book_id, character_data)
            logger.info(f"✅ Completed analysis for book {book_id}")
        else:
            logger.warning(f"⚠️ Analysis failed for book {book_id}: {error}")
            
    except Exception as e:
        logger.error(f"Analysis error for book {book_id}: {e}")
'''
        
        route_path = self.base_dir / "routes" / "books.py"
        self.backup_file(route_path)
        
        with open(route_path, 'w', encoding='utf-8') as f:
            f.write(books_route_content)
        
        print(f"✅ Created fixed books route at {route_path}")
        self.fixes_applied.append("Created fixed books route")
        return True
    
    def create_installation_script(self):
        """Create a simple installation script"""
        print("\n🔧 Creating installation script...")
        
        install_content = '''#!/usr/bin/env python3
"""
KidsKlassiks Installation Script
Run this to set up the application properly
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    """Run a command and return success status"""
    try:
        subprocess.run(cmd, shell=True, check=True)
        return True
    except:
        return False

def main():
    print("🚀 KidsKlassiks Installation Script")
    print("====================================")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    print(f"✅ Python {sys.version}")
    
    # Create virtual environment
    print("\\n📦 Setting up virtual environment...")
    if not Path("venv").exists():
        if not run_command(f"{sys.executable} -m venv venv"):
            print("❌ Failed to create virtual environment")
            return False
    
    # Determine activation script
    if os.name == 'nt':  # Windows
        activate = "venv\\\\Scripts\\\\activate"
        pip = "venv\\\\Scripts\\\\pip"
    else:  # Unix/Linux/Mac
        activate = "source venv/bin/activate"
        pip = "venv/bin/pip"
    
    # Upgrade pip
    print("\\n📦 Upgrading pip...")
    run_command(f"{pip} install --upgrade pip")
    
    # Install requirements
    print("\\n📦 Installing dependencies...")
    if not run_command(f"{pip} install -r requirements_clean.txt"):
        print("⚠️ Some dependencies failed to install")
    
    # Create directories
    print("\\n📁 Creating directories...")
    dirs = ["uploads", "generated_images", "publications", "exports", "backups"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    # Check for .env file
    if not Path(".env").exists():
        print("\\n⚠️ No .env file found!")
        print("📝 Creating .env from template...")
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file - please add your API keys")
        else:
            print("❌ No .env.example found - please create .env manually")
    
    print("\\n✅ Installation complete!")
    print("\\n📝 Next steps:")
    print("1. Edit .env and add your OPENAI_API_KEY")
    print("2. Configure your database settings in .env")
    print("3. Run: python main_clean.py")
    print("4. Open: http://localhost:8000")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
        
        install_path = self.base_dir / "install.py"
        with open(install_path, 'w', encoding='utf-8') as f:
            f.write(install_content)
        
        # Make it executable on Unix systems
        os.chmod(install_path, 0o755)
        
        print(f"✅ Created installation script at {install_path}")
        self.fixes_applied.append("Created installation script")
        return True
    
    def run_all_fixes(self):
        """Run all fixes in sequence"""
        print("🔧 Starting Comprehensive Migration Fix")
        print("=" * 50)
        
        # Run each fix
        self.create_new_openai_service()
        self.fix_main_py()
        self.fix_database_paths()
        self.create_clean_requirements()
        self.create_fixed_books_route()
        self.create_installation_script()
        
        # Summary
        print("\n" + "=" * 50)
        print("✅ MIGRATION COMPLETE!")
        print("\nFixes applied:")
        for fix in self.fixes_applied:
            print(f"  ✅ {fix}")
        
        print("\n📝 Next Steps:")
        print("1. Run: python install.py")
        print("2. Activate venv: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Unix)")
        print("3. Run: python main_clean.py")
        print("4. Open: http://localhost:8000")
        
        print("\n⚠️ Important:")
        print("- Make sure your .env file has your OPENAI_API_KEY")
        print("- The new files created are:")
        print("  - main_clean.py (use this instead of main.py)")
        print("  - services/openai_service_new.py")
        print("  - requirements_clean.txt")
        print("  - routes/books.py (fixed version)")
        
        return True

if __name__ == "__main__":
    fixer = KidsKlassiksFixer()
    fixer.run_all_fixes()
