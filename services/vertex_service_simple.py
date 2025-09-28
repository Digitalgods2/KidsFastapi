"""
Simplified Vertex AI Service for KidsKlassiks
No Google Cloud dependencies required - graceful fallback
"""

import os
from typing import Optional, Dict, Any, Tuple
import asyncio

class VertexService:
    """Simplified service for Google Vertex AI image generation"""
    
    def __init__(self):
        self.available = False
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        
        # Always disabled in this simplified version
        from services.logger import get_logger
        get_logger("services.vertex_service_simple").info("vertex_simple_in_use", extra={"component":"services.vertex_service_simple","message":"Using simplified Vertex AI service (Google Cloud features disabled)"})
    
    async def generate_image(
        self, 
        prompt: str, 
        model: str = "imagen-children",
        size: str = "1024x1024",
        **kwargs
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an image using Vertex AI Imagen (placeholder)
        """
        await asyncio.sleep(0.1)  # Simulate async operation
        return None, "Vertex AI not available in simplified version. Use OpenAI DALL-E instead."
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available Vertex AI models"""
        return {
            "available": False,
            "reason": "Simplified version - Google Cloud dependencies not required",
            "models": []
        }
    
    def is_available(self) -> bool:
        """Check if Vertex AI is available"""
        return False
    
    async def validate_configuration(self) -> Tuple[bool, str]:
        """Validate Vertex AI configuration"""
        return False, "Vertex AI disabled in simplified version"

# Utility functions
def validate_vertex_ai_config() -> bool:
    """Check if Vertex AI is properly configured"""
    return False

def get_vertex_ai_status() -> Dict[str, Any]:
    """Get detailed Vertex AI status information"""
    return {
        "package_available": False,
        "project_configured": False,
        "credentials_configured": False,
        "overall_status": False,
        "note": "Simplified version - Google Cloud features disabled"
    }
