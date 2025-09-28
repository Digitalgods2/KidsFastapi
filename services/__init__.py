"""
Services package for KidsKlassiks FastAPI application
Contains AI operations, text processing, and other business logic
"""

# Use legacy OpenAI service (quarantined under legacy/) only where still needed (e.g., images)
try:
    from legacy.services.openai_service_legacy_complete import get_legacy_openai_service
    OpenAIService = get_legacy_openai_service
except Exception:
    # Keep optional; most chat calls route through services.chat_helper now
    OpenAIService = None
from .text_processing import TextProcessor
from .pdf_generator import PDFGenerator

# Use simplified vertex service to avoid Google Cloud dependencies
try:
    from .vertex_service import VertexService
except ImportError:
    from .vertex_service_simple import VertexService
    from .logger import get_logger
    get_logger("services").info("vertex_service_simplified", extra={"component":"services","note":"Using simplified Vertex AI service (Google Cloud dependencies not available)"})

__all__ = [
    'OpenAIService',
    'VertexService', 
    'TextProcessor',
    'PDFGenerator'
]
