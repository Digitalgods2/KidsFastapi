"""
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
