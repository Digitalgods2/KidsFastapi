"""
Vertex AI service for KidsKlassiks FastAPI application
Handles Google's Imagen image generation with proper imports
"""

import base64
import asyncio
import os
from typing import Dict, Any, Optional, Tuple

try:
    from google.cloud import aiplatform
    from google.cloud.aiplatform import gapic
    from google.protobuf import struct_pb2
    from google.protobuf.struct_pb2 import Value
    VERTEX_AVAILABLE = True
except ImportError as e:
    from services.logger import get_logger
    get_logger("services.vertex_service_fixed").warning("vertex_import_failed", extra={"component":"services.vertex_service_fixed","error":str(e)})
    get_logger("services.vertex_service_fixed").info("vertex_install_hint", extra={"component":"services.vertex_service_fixed","hint":"pip install google-cloud-aiplatform"})
    VERTEX_AVAILABLE = False

import config
from models import ImageModel

class VertexService:
    """Service class for Google Vertex AI operations"""
    
    def __init__(self):
        """Initialize Vertex AI client"""
        self.available = VERTEX_AVAILABLE
        
        if not self.available:
            from services.logger import get_logger
            get_logger("services.vertex_service_fixed").warning("vertex_unavailable", extra={"component":"services.vertex_service_fixed","reason":"google cloud packages not installed"})
            return
            
        if not config.validate_vertex_ai_config():
            from services.logger import get_logger
            get_logger("services.vertex_service_fixed").warning("vertex_not_configured", extra={"component":"services.vertex_service_fixed","reason":"missing credentials or project"})
            self.available = False
            return
        
        try:
            self.project_id = config.GOOGLE_CLOUD_PROJECT
            self.location = getattr(config, 'VERTEX_LOCATION', 'us-central1')
            
            # Initialize AI Platform
            aiplatform.init(
                project=self.project_id,
                location=self.location
            )
            
            # Create prediction client
            api_endpoint = f"{self.location}-aiplatform.googleapis.com"
            client_options = {"api_endpoint": api_endpoint}
            self.client = gapic.PredictionServiceClient(client_options=client_options)
            
            from services.logger import get_logger
            get_logger("services.vertex_service_fixed").info("vertex_initialized", extra={"component":"services.vertex_service_fixed","project_id":self.project_id})
            
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.vertex_service_fixed").error("vertex_init_failed", extra={"component":"services.vertex_service_fixed","error":str(e)})
            self.available = False
    
    def is_available(self) -> bool:
        """Check if Vertex AI is available and configured"""
        return self.available
    
    async def generate_image(
        self, 
        prompt: str, 
        model: str = "imagen-children",
        size: str = "1024x1024",
        **kwargs
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an image using Vertex AI Imagen
        
        Args:
            prompt: Text description for image generation
            model: Model to use (imagen-children, imagen-artistic, etc.)
            size: Image size (1024x1024, 512x512, etc.)
            
        Returns:
            Tuple of (image_url, error_message)
        """
        if not self.available:
            return None, "Vertex AI not available. Please install google-cloud-aiplatform and configure credentials."
        
        try:
            # Map model names to Vertex AI endpoints
            model_mapping = {
                "imagen-children": "imagegeneration",
                "imagen-artistic": "imagegeneration", 
                "imagen-text": "imagegeneration"
            }
            
            endpoint_name = model_mapping.get(model, "imagegeneration")
            
            # Construct the full model path
            model_path = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{endpoint_name}"
            
            # Prepare the request parameters
            parameters = {
                "sampleCount": 1,
                "aspectRatio": "1:1" if size == "1024x1024" else "16:9",
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_adult"
            }
            
            # Create the instance
            instance = {
                "prompt": prompt
            }
            
            # Convert to protobuf format
            instance_pb = struct_pb2.Value()
            instance_pb.struct_value.update(instance)
            
            parameters_pb = struct_pb2.Value()
            parameters_pb.struct_value.update(parameters)
            
            # Make the prediction request
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.predict(
                    endpoint=model_path,
                    instances=[instance_pb],
                    parameters=parameters_pb
                )
            )
            
            # Extract the generated image
            if response.predictions:
                prediction = response.predictions[0]
                
                # Get the base64 encoded image
                if hasattr(prediction, 'struct_value') and 'bytesBase64Encoded' in prediction.struct_value:
                    image_data = prediction.struct_value['bytesBase64Encoded'].string_value
                    
                    # Save the image to a file
                    import uuid
                    filename = f"vertex_image_{uuid.uuid4().hex[:8]}.png"
                    filepath = os.path.join("generated_images", filename)
                    
                    # Decode and save
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(image_data))
                    
                    return filepath, None
                else:
                    return None, "No image data in response"
            else:
                return None, "No predictions in response"
                
        except Exception as e:
            error_msg = f"Vertex AI image generation failed: {str(e)}"
            from services.logger import get_logger
            get_logger("services.vertex_service_fixed").error("vertex_generate_image_failed", extra={"component":"services.vertex_service_fixed","error":str(e)})
            return None, error_msg
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available Vertex AI models"""
        if not self.available:
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
                    "id": "imagen-children",
                    "name": "Imagen for Children",
                    "description": "Child-friendly image generation"
                },
                {
                    "id": "imagen-artistic", 
                    "name": "Imagen Artistic",
                    "description": "Artistic style image generation"
                },
                {
                    "id": "imagen-text",
                    "name": "Imagen Text",
                    "description": "Text-focused image generation"
                }
            ]
        }
    
    async def validate_configuration(self) -> Tuple[bool, str]:
        """Validate Vertex AI configuration"""
        if not VERTEX_AVAILABLE:
            return False, "Google Cloud AI Platform package not installed. Run: pip install google-cloud-aiplatform"
        
        if not config.GOOGLE_CLOUD_PROJECT:
            return False, "GOOGLE_CLOUD_PROJECT environment variable not set"
        
        credentials_path = config.GOOGLE_APPLICATION_CREDENTIALS
        if not credentials_path or not os.path.exists(credentials_path):
            return False, "GOOGLE_APPLICATION_CREDENTIALS not set or file not found"
        
        try:
            if self.available:
                return True, "Vertex AI configured successfully"
            else:
                return False, "Vertex AI client initialization failed"
                
        except Exception as e:
            return False, f"Vertex AI validation failed: {str(e)}"

# Utility functions for configuration
def validate_vertex_ai_config() -> bool:
    """Check if Vertex AI is properly configured"""
    if not VERTEX_AVAILABLE:
        return False
    
    project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    return bool(project_id and credentials_path and os.path.exists(credentials_path))

def get_vertex_ai_status() -> Dict[str, Any]:
    """Get detailed Vertex AI status information"""
    return {
        "package_available": VERTEX_AVAILABLE,
        "project_configured": bool(os.getenv('GOOGLE_CLOUD_PROJECT')),
        "credentials_configured": bool(
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and 
            os.path.exists(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', ''))
        ),
        "overall_status": validate_vertex_ai_config()
    }
