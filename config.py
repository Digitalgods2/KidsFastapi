"""
Configuration module for KidsKlassiks FastAPI application
Handles environment variables and application settings
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# ==================== API CONFIGURATION ====================

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        from services.logger import get_logger
        get_logger("config").warning(
            "missing_openai_api_key",
            extra={"component": "config"},
        )
    except Exception:
        pass

# ==================== DATABASE CONFIGURATION ====================

# Database Configuration
DB_HOST = os.getenv("DATABASE_HOST", os.getenv("DB_HOST", "localhost"))
DB_PORT = os.getenv("DATABASE_PORT", os.getenv("DB_PORT", "5432"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "kidsklassiks")
DB_USER = os.getenv("DATABASE_USER", os.getenv("DB_USER", "glen"))
DB_PASSWORD = os.getenv("DATABASE_PASSWORD", os.getenv("DB_PASSWORD"))

# Validate database configuration
if not DB_USER or not DB_PASSWORD:
    try:
        from services.logger import get_logger
        if not DB_USER:
            get_logger("config").warning(
                "missing_db_user", extra={"component": "config"}
            )
        if not DB_PASSWORD:
            get_logger("config").warning(
                "missing_db_password", extra={"component": "config"}
            )
    except Exception:
        pass

# ==================== VERTEX AI CONFIGURATION ====================

# Vertex AI Configuration
VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_MODEL_ID = "imagen-4.0-generate-preview-06-06"
VERTEX_PUBLISHER = "google"

# Google Cloud Credentials
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# ==================== GPT-5 MODEL CONFIGURATION ====================

# GPT-5 Model Configuration for different tasks
GPT5_MODELS = {
    'character_analysis': os.getenv('GPT5_CHARACTER_MODEL', 'gpt-4'),
    'scene_generation': os.getenv('GPT5_SCENE_MODEL', 'gpt-4'),
    'quick_suggestions': os.getenv('GPT5_QUICK_MODEL', 'gpt-4'),
    'validation': os.getenv('GPT5_VALIDATION_MODEL', 'gpt-4'),
    'conversation': os.getenv('GPT5_CONVERSATION_MODEL', 'gpt-4')
}

DEFAULT_GPT_MODEL = os.getenv('DEFAULT_GPT_MODEL', 'gpt-4')

# ==================== IMAGE GENERATION CONFIGURATION ====================

# Default image generation model
DEFAULT_IMAGE_MODEL = os.getenv('DEFAULT_IMAGE_MODEL', 'gpt-image-1')
DEFAULT_ASPECT_RATIO = os.getenv('DEFAULT_ASPECT_RATIO', '4:3')

# Model-specific character limits for prompt optimization
MODEL_LIMITS = {
    "gpt-image-1": 4000,  # NEW: GPT-Image-1 with superior capabilities
    "dall-e-3": 4000,
    "gpt-image-1": 4000,
    "vertex-imagen": 3200,
    "imagen-children": 3200,
    "imagen-artistic": 3200,
    "imagen-text": 3200
}

# Enhanced Imagen 4 Modes Configuration
IMAGEN_MODES = {
    'children_illustration': {
        'name': 'Children\'s Illustration',
        'description': 'Optimized for whimsical, colorful children\'s book illustrations',
        'prompt_prefix': 'A whimsical and colorful children\'s book illustration of ',
        'prompt_suffix': ', in a friendly cartoon style with bright colors and simple shapes',
        'vertex_config': {'aspectRatio': '4:3', 'sampleCount': 1},
        'openai_config': {'size': '1024x1024', 'quality': 'standard', 'style': 'vivid'}
    },
    'artistic_style': {
        'name': 'Artistic Style',
        'description': 'Generate images in the style of famous artists',
        'prompt_prefix': 'A masterpiece painting in the style of {artist} of ',
        'prompt_suffix': ', with artistic brushstrokes and rich colors',
        'vertex_config': {'aspectRatio': '1:1', 'sampleCount': 1},
        'openai_config': {'size': '1024x1024', 'quality': 'hd', 'style': 'natural'}
    },
    'text_enhanced': {
        'name': 'Text Enhanced',
        'description': 'Optimized for generating images with embedded text',
        'prompt_prefix': 'A high-resolution image with the text "{text}" clearly visible, featuring ',
        'prompt_suffix': ', with clear readable text and professional typography',
        'vertex_config': {'aspectRatio': '16:9', 'sampleCount': 1},
        'openai_config': {'size': '1792x1024', 'quality': 'hd', 'style': 'natural'}
    }
}

# ==================== APPLICATION CONFIGURATION ====================

# Application environment
APP_ENV = os.getenv('APP_ENV', 'development')
APP_DEBUG = os.getenv('APP_DEBUG', 'false').lower() == 'true'
APP_PORT = int(os.getenv('APP_PORT', '8000'))

# --- Chapter processing and runs ---
# Stale run timeout in seconds (default: 30 minutes)
STALE_RUN_TIMEOUT_SECONDS = int(os.getenv('STALE_RUN_TIMEOUT_SECONDS', str(30*60)))
CHAPMAP_MAX_OPS = int(os.getenv('CHAPMAP_MAX_OPS', '2000'))  # cap operations stored per run

# Per-adaptation cooldown after a run starts to prevent button spamming
REPROCESS_COOLDOWN_SECONDS = int(os.getenv('REPROCESS_COOLDOWN_SECONDS', '60'))

# ==================== FEATURE FLAGS ====================

# Feature flags for enabling/disabling functionality
ENABLE_CHARACTER_ANALYSIS = os.getenv('ENABLE_CHARACTER_ANALYSIS', 'true').lower() == 'true'
ENABLE_JSON_PROMPTS = os.getenv('ENABLE_JSON_PROMPTS', 'true').lower() == 'true'
ENABLE_AUTO_ANALYSIS = os.getenv('ENABLE_AUTO_ANALYSIS', 'true').lower() == 'true'
ENABLE_ENHANCED_MODES = os.getenv('ENABLE_ENHANCED_MODES', 'true').lower() == 'true'

# ==================== MODEL PARAMETERS ====================

# GPT model parameters
GPT_MAX_TOKENS = int(os.getenv('GPT_MAX_TOKENS', '4000'))
GPT_TEMPERATURE = float(os.getenv('GPT_TEMPERATURE', '0.3'))

# DALL-E parameters
DALLE3_SIZE = os.getenv('DALLE3_SIZE', '1024x1024')
DALLE3_QUALITY = os.getenv('DALLE3_QUALITY', 'standard')

# ==================== LOGGING CONFIGURATION ====================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE')

# ==================== UTILITY FUNCTIONS ====================

def get_image_api_options():
    """Return all available image generation models with descriptions"""
    return {
        # OpenAI Models
        "gpt-image-1": "GPT-Image-1 (DEFAULT) – Highest quality, best instruction following, superior text rendering",
        "dall-e-3": "DALL-E 3 – High quality generation with multiple size options",
        # Note: DALL-E 2 has been deprecated and removed
        "vertex-imagen": "Google Vertex Imagen – advanced image generation using Google's latest model",
        
        # New Enhanced Imagen 4 Models
        "imagen-children": "Imagen 4 Children's Mode – Optimized for whimsical, colorful children's book illustrations",
        "imagen-artistic": "Imagen 4 Artistic Mode – Generate images in the style of famous artists with enhanced controls",
        "imagen-text": "Imagen 4 Text Enhanced – Superior text rendering and typography for book covers and titles"
    }

def get_optimal_gpt_model(task_type: str, complexity: str = 'medium') -> str:
    """
    Get optimal GPT model for a specific task
    
    Args:
        task_type: Type of task (character_analysis, scene_generation, etc.)
        complexity: Task complexity (low, medium, high)
        
    Returns:
        Optimal model name for the task
    """
    if task_type in GPT5_MODELS:
        base_model = GPT5_MODELS[task_type]
        
        # Adjust based on complexity
        if complexity == 'low' and base_model == 'gpt-4':
            return 'gpt-3.5-turbo'  # Use cheaper model for simple tasks
        elif complexity == 'high' and base_model == 'gpt-3.5-turbo':
            return 'gpt-4'  # Use better model for complex tasks
        
        return base_model
    
    return DEFAULT_GPT_MODEL

def is_production() -> bool:
    """Check if running in production environment"""
    return APP_ENV.lower() == 'production'

def is_development() -> bool:
    """Check if running in development environment"""
    return APP_ENV.lower() == 'development'

def validate_vertex_ai_config() -> bool:
    """
    Validate Vertex AI configuration
    
    Returns:
        True if Vertex AI is properly configured
    """
    if not VERTEX_PROJECT_ID:
        return False
    
    if GOOGLE_APPLICATION_CREDENTIALS and not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        return False
    
    return True

def get_config_summary() -> dict:
    """
    Get configuration summary for debugging
    
    Returns:
        Dictionary with configuration summary (sensitive data masked)
    """
    return {
        'app_env': APP_ENV,
        'app_debug': APP_DEBUG,
        'app_port': APP_PORT,
        'openai_configured': bool(OPENAI_API_KEY),
        'vertex_configured': validate_vertex_ai_config(),
        'database_configured': bool(DB_USER and DB_PASSWORD),
        'default_gpt_model': DEFAULT_GPT_MODEL,
        'default_image_model': DEFAULT_IMAGE_MODEL,
        'features': {
            'character_analysis': ENABLE_CHARACTER_ANALYSIS,
            'json_prompts': ENABLE_JSON_PROMPTS,
            'auto_analysis': ENABLE_AUTO_ANALYSIS,
            'enhanced_modes': ENABLE_ENHANCED_MODES
        }
    }
