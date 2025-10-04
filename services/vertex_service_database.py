"""
Database-aware Vertex AI service for KidsKlassiks
Uses database settings for configuration like the OpenAI service
"""

import base64
import asyncio
import os
import json
import tempfile
from typing import Dict, Any, Optional, Tuple, Any

try:
    from google.cloud import aiplatform_v1
    from google.protobuf import struct_pb2
    from google.auth import default
    from google.oauth2 import service_account
    VERTEX_AVAILABLE = True
except ImportError as e:
    VERTEX_AVAILABLE = False

from models import ImageModel

class VertexService:
    """Database-aware service class for Google Vertex AI operations"""
    
    def __init__(self):
        """Initialize Vertex AI service - configuration loaded dynamically"""
        self.available = VERTEX_AVAILABLE
        self.client = None
        self.project_id = None
        self.location = None
        
        if not self.available:
            from services.logger import get_logger
            get_logger("services.vertex_database").warning("vertex_packages_missing", extra={
                "component": "services.vertex_database",
                "hint": "Install with: pip install google-cloud-aiplatform"
            })
    
    async def get_client(self) -> Optional[Any]:
        """Get Vertex AI client with credentials from database settings"""
        if not self.available:
            return None
        try:
            # Get configuration from database settings
            import database_fixed as database
            
            project_id = await database.get_setting("vertex_project_id", None)
            location = await database.get_setting("vertex_location", "us-central1")
            credentials_json = await database.get_setting("vertex_credentials", None)
            
            if not project_id:
                from services.logger import get_logger
                get_logger("services.vertex_database").warning("vertex_no_project", extra={
                    "component": "services.vertex_database",
                    "info": "vertex_project_id not configured in database"
                })
                return None
            
            # Set up credentials
            credentials = None
            if credentials_json:
                try:
                    # Parse JSON credentials from database
                    creds_data = json.loads(credentials_json)
                    credentials = service_account.Credentials.from_service_account_info(creds_data)
                except Exception as e:
                    from services.logger import get_logger
                    get_logger("services.vertex_database").error("vertex_credentials_parse_failed", extra={
                        "component": "services.vertex_database",
                        "error": str(e)
                    })
                    return None
            else:
                # Try to use default credentials (if running on Google Cloud)
                try:
                    credentials, _ = default()
                except Exception:
                    from services.logger import get_logger
                    get_logger("services.vertex_database").warning("vertex_no_credentials", extra={
                        "component": "services.vertex_database", 
                        "info": "No credentials configured in database and no default credentials available"
                    })
                    return None
            
            # Store configuration
            self.project_id = project_id
            self.location = location
            
            # Create client
            api_endpoint = f"{location}-aiplatform.googleapis.com"
            client_options = {"api_endpoint": api_endpoint}
            
            if credentials:
                self.client = aiplatform_v1.PredictionServiceClient(
                    credentials=credentials,
                    client_options=client_options
                )
            else:
                self.client = aiplatform_v1.PredictionServiceClient(
                    client_options=client_options
                )
            
            return self.client
            
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.vertex_database").error("vertex_client_creation_failed", extra={
                "component": "services.vertex_database",
                "error": str(e)
            })
            return None
    
    def is_available(self) -> bool:
        """Check if Vertex AI is available and configured"""
        return self.available
    
    async def generate_image(
        self, 
        prompt: str, 
        model: ImageModel = ImageModel.VERTEX_IMAGEN,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "children_illustration",
        **kwargs
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an image using Vertex AI Imagen
        
        Args:
            prompt: Text description for image generation
            model: Image model to use
            size: Image size (1024x1024, 512x512, etc.)
            quality: Image quality (not used in Vertex AI, for compatibility)
            style: Image style (children_illustration, artistic, etc.)
            
        Returns:
            Tuple of (image_url, error_message)
        """
        client = await self.get_client()
        if not client:
            return None, "Vertex AI not configured. Please set vertex_project_id and vertex_credentials in database settings."
        
        try:
            # Enhance prompt based on style
            enhanced_prompt = self._enhance_prompt_for_children(prompt, style)
            
            # Convert size to aspect ratio
            aspect_ratio = self._size_to_aspect_ratio(size)
            
            # Construct the model endpoint
            model_endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/imagegeneration"
            
            # Prepare the request parameters
            parameters_dict = {
                "sampleCount": 1,
                "aspectRatio": aspect_ratio,
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_adult"
            }
            
            # Create the instance
            instance_dict = {
                "prompt": enhanced_prompt
            }
            
            # Convert to protobuf format
            instance_pb = struct_pb2.Value()
            instance_pb.struct_value.update(instance_dict)
            
            parameters_pb = struct_pb2.Value()  
            parameters_pb.struct_value.update(parameters_dict)
            
            # Make the prediction request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.predict(
                    endpoint=model_endpoint,
                    instances=[instance_pb],
                    parameters=parameters_pb
                )
            )
            
            # Extract the generated image
            if response.predictions:
                prediction = response.predictions[0]
                
                # Get the base64 encoded image data
                image_data = None
                
                # Handle MapComposite response format (current Google AI Platform)
                if hasattr(prediction, 'keys') and 'bytesBase64Encoded' in prediction:
                    image_data = prediction['bytesBase64Encoded']
                # Fallback for older struct_value format
                elif hasattr(prediction, 'struct_value'):
                    struct_data = prediction.struct_value
                    if 'bytesBase64Encoded' in struct_data:
                        image_data = struct_data['bytesBase64Encoded'].string_value
                
                if image_data:
                    # Save the image to a file
                    import uuid
                    filename = f"vertex_image_{uuid.uuid4().hex[:8]}.png"
                    os.makedirs("generated_images", exist_ok=True)
                    filepath = os.path.join("generated_images", filename)
                    
                    # Decode and save
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(image_data))
                    
                    # Return as URL path that FastAPI can serve
                    return f"/generated_images/{filename}", None
                else:
                    return None, "No image data found in response"
            else:
                return None, "No predictions in response"
                
        except Exception as e:
            error_msg = f"Vertex AI image generation failed: {str(e)}"
            from services.logger import get_logger
            get_logger("services.vertex_database").error("vertex_generate_failed", extra={
                "component": "services.vertex_database",
                "error": str(e),
                "prompt": prompt[:100]
            })
            return None, error_msg
    
    def _enhance_prompt_for_children(self, prompt: str, style: str = "children_illustration") -> str:
        """Enhance prompt for child-friendly content"""
        style_prefixes = {
            "children_illustration": "A whimsical and colorful children's book illustration of ",
            "artistic": "A masterpiece painting of ",
            "simple": "A simple, clean illustration of "
        }
        
        style_suffixes = {
            "children_illustration": ", in a friendly cartoon style with bright colors and simple shapes suitable for children",
            "artistic": ", with artistic brushstrokes and rich colors",
            "simple": ", with clean lines and minimal detail"
        }
        
        prefix = style_prefixes.get(style, style_prefixes["children_illustration"])
        suffix = style_suffixes.get(style, style_suffixes["children_illustration"])
        
        return f"{prefix}{prompt}{suffix}"
    
    def _size_to_aspect_ratio(self, size: str) -> str:
        """Convert image size to Vertex AI aspect ratio"""
        size_mapping = {
            "1024x1024": "1:1",
            "1024x576": "16:9", 
            "576x1024": "9:16",
            "1152x896": "4:3",
            "896x1152": "3:4"
        }
        return size_mapping.get(size, "1:1")
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available Vertex AI models"""
        client = await self.get_client()
        if not client:
            return {
                "available": False,
                "reason": "Vertex AI not configured or packages not installed",
                "models": []
            }
        
        return {
            "available": True,
            "project_id": self.project_id,
            "location": self.location,
            "models": [
                {
                    "id": "vertex-imagen",
                    "name": "Vertex AI Imagen",
                    "description": "Google's advanced image generation model"
                },
                {
                    "id": "imagen-children",
                    "name": "Imagen for Children",
                    "description": "Child-friendly image generation optimized for storybooks"
                }
            ]
        }
    
    async def validate_configuration(self) -> Tuple[bool, str]:
        """Validate Vertex AI configuration"""
        if not self.available:
            return False, "Google Cloud AI Platform package not installed. Run: pip install google-cloud-aiplatform"
        
        client = await self.get_client()
        if client:
            return True, f"Vertex AI configured successfully for project {self.project_id}"
        else:
            return False, "Vertex AI configuration invalid. Check project_id and credentials in database settings."

# Utility functions
async def get_vertex_ai_status() -> Dict[str, Any]:
    """Get detailed Vertex AI status information"""
    service = VertexService()
    is_configured, message = await service.validate_configuration()
    
    import database_fixed as database
    project_id = await database.get_setting("vertex_project_id", None)
    credentials = await database.get_setting("vertex_credentials", None)
    
    return {
        "package_available": VERTEX_AVAILABLE,
        "project_configured": bool(project_id),
        "credentials_configured": bool(credentials),
        "overall_status": is_configured,
        "message": message,
        "project_id": project_id
    }