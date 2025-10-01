"""
Vertex AI service for KidsKlassiks FastAPI application
Handles Google's Imagen image generation
"""

import base64
import asyncio
from typing import Dict, Any, Optional, Tuple
from google.cloud import aiplatform_v1
from google.protobuf import struct_pb2
import config
from models import ImageModel

class VertexService:
    """Service class for Google Vertex AI operations"""
    
    def __init__(self):
        """Initialize Vertex AI client"""
        if not config.validate_vertex_ai_config():
            raise ValueError("Vertex AI not properly configured")
        
        self.project_id = config.VERTEX_PROJECT_ID
        self.location = config.VERTEX_LOCATION
        self.model_id = config.VERTEX_MODEL_ID
        self.publisher = config.VERTEX_PUBLISHER
        
        # Initialize the client
        self.client = aiplatform_v1.PredictionServiceClient(
            client_options={"api_endpoint": f"{self.location}-aiplatform.googleapis.com"}
        )
        
        self.endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/{self.publisher}/models/{self.model_id}"
    
    # ==================== IMAGE GENERATION ====================
    
    async def generate_image(
        self, 
        prompt: str, 
        model: ImageModel = ImageModel.VERTEX_IMAGEN,
        mode: str = "children_illustration",
        **kwargs
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate image using Vertex AI Imagen"""
        try:
            # Enhance prompt based on mode
            enhanced_prompt = self._enhance_prompt_with_mode(prompt, mode, **kwargs)
            
            # Extract aspect_ratio from kwargs if provided
            aspect_ratio = kwargs.get('aspect_ratio', None)
            
            # Prepare the request
            instance = self._create_imagen_instance(enhanced_prompt, mode, aspect_ratio)
            instances = [instance]
            
            # Make the prediction request
            print(f"🔧 DEBUG: Making prediction request to endpoint: {self.endpoint}")
            print(f"🔧 DEBUG: Instance fields: {[(k, str(v)[:100]) for k, v in instance.fields.items()]}")
            
            # Also try passing parameters separately (Imagen 4 format)
            parameters = struct_pb2.Struct()
            if aspect_ratio:
                parameters.fields['aspectRatio'].string_value = aspect_ratio
                parameters.fields['aspect_ratio'].string_value = aspect_ratio
            parameters.fields['sampleCount'].number_value = 1
            
            print(f"🔧 DEBUG: Parameters: {[(k, str(v)[:100]) for k, v in parameters.fields.items()]}")
            
            response = self.client.predict(
                endpoint=self.endpoint,
                instances=instances,
                parameters=parameters
            )
            
            print(f"🔧 DEBUG: Response received, predictions count: {len(response.predictions) if response.predictions else 0}")
            
            # Process the response
            if response.predictions:
                prediction = response.predictions[0]
                
                # Extract image data
                if 'bytesBase64Encoded' in prediction:
                    image_data = prediction['bytesBase64Encoded']
                    # Save image and return URL
                    image_url = await self._save_base64_image(image_data)
                    return image_url, None
                else:
                    return None, "No image data in response"
            else:
                return None, "No predictions in response"
                
        except Exception as e:
            return None, f"Error generating image with Vertex AI: {e}"
    
    def _enhance_prompt_with_mode(self, prompt: str, mode: str, **kwargs) -> str:
        """Enhance prompt based on the selected Imagen mode"""
        if mode not in config.IMAGEN_MODES:
            return prompt
        
        mode_config = config.IMAGEN_MODES[mode]
        
        # Apply prefix and suffix
        enhanced_prompt = prompt
        
        if mode_config.get('prompt_prefix'):
            prefix = mode_config['prompt_prefix']
            
            # Handle special placeholders
            if '{artist}' in prefix and 'artist' in kwargs:
                prefix = prefix.format(artist=kwargs['artist'])
            elif '{text}' in prefix and 'text' in kwargs:
                prefix = prefix.format(text=kwargs['text'])
            
            enhanced_prompt = prefix + enhanced_prompt
        
        if mode_config.get('prompt_suffix'):
            enhanced_prompt += mode_config['prompt_suffix']
        
        # Optimize for Vertex AI character limits
        limit = config.MODEL_LIMITS.get('vertex-imagen', 3200)
        if len(enhanced_prompt) > limit:
            enhanced_prompt = enhanced_prompt[:limit]
        
        return enhanced_prompt
    
    def _create_imagen_instance(self, prompt: str, mode: str, aspect_ratio: str = None) -> struct_pb2.Struct:
        """Create Imagen prediction instance"""
        instance = struct_pb2.Struct()
        
        # Basic parameters
        instance.fields['prompt'].string_value = prompt
        
        # Mode-specific configuration
        final_aspect_ratio = None
        if mode in config.IMAGEN_MODES:
            mode_config = config.IMAGEN_MODES[mode]
            vertex_config = mode_config.get('vertex_config', {})
            
            # Apply vertex-specific configuration
            for key, value in vertex_config.items():
                if key == 'aspectRatio':
                    # Override with provided aspect_ratio if available
                    final_aspect_ratio = aspect_ratio if aspect_ratio else value
                    # Try both aspectRatio and aspect_ratio field names
                    instance.fields['aspectRatio'].string_value = final_aspect_ratio
                    instance.fields['aspect_ratio'].string_value = final_aspect_ratio
                elif key == 'sampleCount':
                    instance.fields['sampleCount'].number_value = value
                elif key == 'seed':
                    instance.fields['seed'].number_value = value
                elif key == 'guidanceScale':
                    instance.fields['guidanceScale'].number_value = value
        else:
            # Default configuration
            final_aspect_ratio = aspect_ratio if aspect_ratio else '1:1'
            # Try both aspectRatio and aspect_ratio field names
            instance.fields['aspectRatio'].string_value = final_aspect_ratio
            instance.fields['aspect_ratio'].string_value = final_aspect_ratio
            instance.fields['sampleCount'].number_value = 1
        
        print(f"🔧 DEBUG: _create_imagen_instance called with aspect_ratio={aspect_ratio}, mode={mode}, final_aspect_ratio={final_aspect_ratio}")
        print(f"🔧 DEBUG: instance.fields['aspectRatio'] = {instance.fields.get('aspectRatio', 'NOT SET')}")
        
        return instance
    
    async def _save_base64_image(self, base64_data: str) -> str:
        """Save base64 image data to file and return URL"""
        try:
            import os
            import uuid
            from datetime import datetime
            
            # Decode base64 data
            image_data = base64.b64decode(base64_data)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"vertex_image_{timestamp}_{unique_id}.png"
            
            # Ensure directory exists
            os.makedirs("generated_images", exist_ok=True)
            
            # Save file
            file_path = os.path.join("generated_images", filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Return URL path
            return f"/generated_images/{filename}"
            
        except Exception as e:
            raise Exception(f"Failed to save image: {e}")
    
    # ==================== ENHANCED IMAGEN 4 MODES ====================
    
    async def generate_children_illustration(
        self, 
        prompt: str, 
        aspect_ratio: str = "4:3"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate children's book illustration using Imagen 4 children mode"""
        return await self.generate_image(
            prompt, 
            model=ImageModel.IMAGEN_CHILDREN,
            mode="children_illustration",
            aspect_ratio=aspect_ratio
        )
    
    async def generate_artistic_style(
        self, 
        prompt: str, 
        artist: str = "Van Gogh",
        aspect_ratio: str = "1:1"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate artistic style image using Imagen 4 artistic mode"""
        return await self.generate_image(
            prompt,
            model=ImageModel.IMAGEN_ARTISTIC,
            mode="artistic_style",
            artist=artist,
            aspect_ratio=aspect_ratio
        )
    
    async def generate_text_enhanced(
        self, 
        prompt: str, 
        text: str,
        aspect_ratio: str = "16:9"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate text-enhanced image using Imagen 4 text mode"""
        return await self.generate_image(
            prompt,
            model=ImageModel.IMAGEN_TEXT,
            mode="text_enhanced",
            text=text,
            aspect_ratio=aspect_ratio
        )
    
    # ==================== BATCH OPERATIONS ====================
    
    async def generate_multiple_images(
        self, 
        prompts: list, 
        mode: str = "children_illustration"
    ) -> list:
        """Generate multiple images in parallel"""
        tasks = []
        for prompt in prompts:
            task = self.generate_image(prompt, mode=mode)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append((None, str(result)))
            else:
                processed_results.append(result)
        
        return processed_results
    
    # ==================== UTILITY METHODS ====================
    
    def get_available_modes(self) -> Dict[str, str]:
        """Get available Imagen modes with descriptions"""
        return {
            mode: config['name'] + " - " + config['description']
            for mode, config in config.IMAGEN_MODES.items()
        }
    
    def validate_prompt_for_vertex(self, prompt: str) -> Tuple[bool, Optional[str]]:
        """Validate prompt for Vertex AI requirements"""
        limit = config.MODEL_LIMITS.get('vertex-imagen', 3200)
        
        if len(prompt) > limit:
            return False, f"Prompt too long: {len(prompt)}/{limit} characters"
        
        # Check for prohibited content (basic check)
        prohibited_terms = ['violence', 'explicit', 'inappropriate']
        for term in prohibited_terms:
            if term.lower() in prompt.lower():
                return False, f"Prompt contains prohibited term: {term}"
        
        return True, None
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current Vertex AI model"""
        return {
            "project_id": self.project_id,
            "location": self.location,
            "model_id": self.model_id,
            "publisher": self.publisher,
            "endpoint": self.endpoint,
            "available_modes": self.get_available_modes(),
            "character_limit": config.MODEL_LIMITS.get('vertex-imagen', 3200)
        }
    
    # ==================== ERROR HANDLING ====================
    
    def _handle_vertex_error(self, error: Exception) -> str:
        """Handle and format Vertex AI errors"""
        error_str = str(error)
        
        if "PERMISSION_DENIED" in error_str:
            return "Permission denied. Check your Google Cloud credentials and project permissions."
        elif "QUOTA_EXCEEDED" in error_str:
            return "Quota exceeded. Check your Vertex AI usage limits."
        elif "INVALID_ARGUMENT" in error_str:
            return "Invalid request parameters. Check your prompt and configuration."
        elif "NOT_FOUND" in error_str:
            return "Model or endpoint not found. Check your project and model configuration."
        else:
            return f"Vertex AI error: {error_str}"
