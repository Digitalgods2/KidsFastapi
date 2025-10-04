"""
Modern OpenAI service for KidsKlassiks FastAPI application
Uses database-aware API key management for all OpenAI operations
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # type: ignore
import config
from models import AgeGroup, TransformationStyle, ImageModel

class OpenAIService:
    """Service class for OpenAI API operations with database-aware API key management"""
    
    def __init__(self):
        """Initialize OpenAI service - client created dynamically per request"""
        # No static client - we create it dynamically with current API key
        pass
    
    async def get_client(self) -> Optional[Any]:
        """Get OpenAI client with API key from database settings (preferred) or environment"""
        # If openai SDK is not available, skip client creation
        if OpenAI is None:
            return None
        try:
            # Try to get API key from database settings first
            import database_fixed as database
            api_key = await database.get_setting("openai_api_key", None)
            
            # Fallback to config/environment if not in database
            if not api_key:
                api_key = getattr(config, 'OPENAI_API_KEY', None)
            
            if not api_key or not api_key.startswith('sk-'):
                return None
                
            return OpenAI(api_key=api_key)
        except Exception:
            # Fallback to config if database access fails
            if hasattr(config, 'OPENAI_API_KEY') and getattr(config, 'OPENAI_API_KEY', None) and str(getattr(config, 'OPENAI_API_KEY')).startswith('sk-') and OpenAI is not None:
                return OpenAI(api_key=config.OPENAI_API_KEY)
            return None
    
    # ==================== CHARACTER ANALYSIS ====================
    
    async def analyze_story_characters(self, story_content: str, book_title: str = "Unknown Book") -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Analyze a story using GPT to extract detailed character descriptions
        and create comprehensive JSON reference for consistent illustrations
        """
        client = await self.get_client()
        if not client:
            return None, "OpenAI API not configured"
            
        try:
            analysis_prompt = f"""
            Analyze the story "{book_title}" and create a comprehensive character reference JSON.
            
            For each significant character, provide detailed visual descriptions for consistent illustrations:
            
            {{
              "characters_reference": {{
                "CharacterName": {{
                  "role": "protagonist/antagonist/supporting",
                  "age": "age description",
                  "physical_appearance": {{
                    "height": "description",
                    "build": "description", 
                    "face": "detailed facial description",
                    "hair": "color, style, length, texture",
                    "eyes": "color, shape, expression",
                    "skin": "color, texture, distinctive marks",
                    "clothing": "typical outfit colors, style, accessories",
                    "distinctive_features": "scars, jewelry, unique traits"
                  }},
                  "personality_traits": ["trait1", "trait2", "trait3"],
                  "role_in_story": "detailed role description"
                }}
              }}
            }}
            
            Focus on: Main characters, supporting characters, memorable minor characters.
            Be specific about colors, styles, and visual details for illustration consistency.
            Limit to 10 most important characters.
            
            Story text:
            {story_content[:12000]}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a literary analyst specializing in character identification and visual consistency for children's book illustrations. Return only valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            result_text = response.choices[0].message.content
            
            # Clean up response - remove markdown code blocks if present
            if result_text.startswith("```"):
                lines = result_text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                result_text = '\n'.join(lines)
            
            try:
                characters_data = json.loads(result_text)
                return characters_data, None
            except json.JSONDecodeError as e:
                return None, f"Failed to parse character analysis JSON: {e}"
                
        except Exception as e:
            return None, f"Character analysis failed: {e}"
    
    # ==================== IMAGE GENERATION ====================
    
    async def generate_image(
        self,
        prompt: str,
        model: str = "gpt-image-1",
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        aspect_ratio: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an image using OpenAI models
        
        Args:
            prompt: Image generation prompt
            model: Model name as string ("gpt-image-1" or "dall-e-3")
            size: Image size (e.g., "1024x1024") - will be determined by aspect_ratio if provided
            quality: Image quality ("standard" or "hd")
            style: Image style ("vivid" or "natural")
            aspect_ratio: Optional aspect ratio (e.g., "4:3", "16:9")
            
        Returns:
            Tuple of (image_url, error_message)
        """
        client = await self.get_client()
        if not client:
            return None, "OpenAI API not configured"
            
        try:
            # Handle aspect ratio to size conversion
            if aspect_ratio:
                from services.backends import get_aspect_ratio_size
                size = get_aspect_ratio_size(model, aspect_ratio)
            
            # Map model names to OpenAI API model strings
            # GPT-Image-1 is a distinct, newer image model with tighter GPT/multimodal integration
            # It has enhancements over previous models (not just DALL-E 3 with HD enabled)
            if model == "gpt-image-1":
                # GPT-Image-1 is its own model - call the actual API model
                api_model = "gpt-image-1"
                # Default to HD quality for optimal results
                if not quality:
                    quality = "hd"
                # Default to vivid style for better text rendering and more vibrant colors
                if not style:
                    style = "vivid"
            elif model == "dall-e-3":
                api_model = "dall-e-3"
            else:
                # Fallback, though DALL-E 2 is deprecated
                return None, f"Unsupported model: {model}"
            
            response = client.images.generate(
                model=api_model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0].url, None
            else:
                return None, "No image generated"
                
        except Exception as e:
            return None, f"Image generation failed: {e}"
    
    # ==================== TEXT TRANSFORMATION ====================
    
    async def transform_text(
        self,
        original_text: str,
        age_group: AgeGroup,
        transformation_style: TransformationStyle = TransformationStyle.SIMPLE_DIRECT,
        book_title: str = "",
        additional_context: str = ""
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Transform text for specific age group using GPT
        
        Args:
            original_text: Original text to transform
            age_group: Target age group
            transformation_style: Style of transformation
            book_title: Title of the book for context
            additional_context: Additional context or instructions
            
        Returns:
            Tuple of (transformed_text, error_message)
        """
        client = await self.get_client()
        if not client:
            return None, "OpenAI API not configured"
            
        try:
            # Age-specific guidelines
            age_guidelines = {
                AgeGroup.AGES_3_5: {
                    'vocabulary': 'very simple words (1-2 syllables)',
                    'sentence_length': 'very short sentences (3-5 words)',
                    'concepts': 'concrete, familiar concepts only',
                    'length_target': '30-40% of original length'
                },
                AgeGroup.AGES_6_8: {
                    'vocabulary': 'simple, everyday words',
                    'sentence_length': 'short sentences (5-10 words)',
                    'concepts': 'simple concepts with clear explanations',
                    'length_target': '50-60% of original length'
                },
                AgeGroup.AGES_9_12: {
                    'vocabulary': 'age-appropriate vocabulary with some challenging words',
                    'sentence_length': 'varied sentence length (10-15 words average)',
                    'concepts': 'more complex ideas with context',
                    'length_target': '70-80% of original length'
                }
            }
            
            guidelines = age_guidelines.get(age_group, age_guidelines[AgeGroup.AGES_6_8])
            
            transform_prompt = f"""
            Transform this text from "{book_title}" for children ages {age_group.value}.
            
            GUIDELINES:
            - Vocabulary: {guidelines['vocabulary']}
            - Sentence Length: {guidelines['sentence_length']}
            - Concepts: {guidelines['concepts']}
            - Target Length: {guidelines['length_target']}
            
            STYLE: {transformation_style.value}
            
            ADDITIONAL CONTEXT: {additional_context}
            
            RULES:
            1. Preserve core story events and character names
            2. Simplify complex vocabulary and sentence structures
            3. Replace archaic words with modern equivalents
            4. Break long paragraphs into shorter ones
            5. Maintain emotional tone appropriate for age group
            6. Use active voice and direct language
            7. Keep it engaging for the target age
            
            ORIGINAL TEXT:
            {original_text}
            
            TRANSFORMED TEXT:"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Fast and cost-effective for text transformation
                messages=[
                    {"role": "system", "content": f"You are an expert children's book adapter specializing in rewriting classic literature for ages {age_group.value}. Maintain the story's essence while making it accessible and engaging."},
                    {"role": "user", "content": transform_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            transformed_text = response.choices[0].message.content
            
            if transformed_text:
                return transformed_text.strip(), None
            else:
                return None, "No transformed text received"
                
        except Exception as e:
            return None, f"Text transformation failed: {e}"
    
    # ==================== PROMPT GENERATION ====================
    
    async def generate_image_prompt(
        self,
        chapter_text: str,
        chapter_number: int,
        book_context: str = "",
        age_group: AgeGroup = AgeGroup.AGES_6_8,
        character_descriptions: Optional[Dict] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Generate an image prompt for a chapter
        
        Args:
            chapter_text: The chapter text
            chapter_number: Chapter number
            book_context: Context about the book
            age_group: Target age group
            character_descriptions: Character descriptions for consistency
            
        Returns:
            Tuple of (prompt, error_message)
        """
        client = await self.get_client()
        if not client:
            return None, "OpenAI API not configured"
            
        try:
            character_context = ""
            if character_descriptions:
                char_list = []
                for name, details in character_descriptions.items():
                    if isinstance(details, dict):
                        appearance = details.get('physical_appearance', {})
                        if isinstance(appearance, dict):
                            desc_parts = []
                            for key, value in appearance.items():
                                if value:
                                    desc_parts.append(f"{key}: {value}")
                            char_desc = f"{name} - {'; '.join(desc_parts)}"
                        else:
                            char_desc = f"{name} - {appearance}"
                        char_list.append(char_desc)
                
                if char_list:
                    character_context = f"\n\nCHARACTER DESCRIPTIONS FOR CONSISTENCY:\n{chr(10).join(char_list)}\n"
            
            prompt_request = f"""
            Create a detailed image generation prompt for Chapter {chapter_number}.
            
            BOOK CONTEXT: {book_context}
            TARGET AGE: {age_group.value}
            {character_context}
            
            CHAPTER TEXT:
            {chapter_text[:2000]}
            
            Create a single, engaging scene from this chapter that:
            - Is appropriate for children ages {age_group.value}
            - Uses bright, friendly colors and whimsical style
            - Shows clear characters and setting from the text
            - Avoids scary or violent elements
            - Includes specific character appearances if mentioned above
            - Has a clear focal point and good composition
            
            Return only the image prompt (under 200 words), no extra commentary.
            IMPORTANT: Do NOT add any prefix like '**Prompt for...**' or '**Image Prompt:**' - just return the description itself.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at creating detailed, child-friendly image prompts for AI image generation. Focus on vivid descriptions that will create engaging illustrations for children's books."},
                    {"role": "user", "content": prompt_request}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            prompt = response.choices[0].message.content
            
            if prompt:
                return prompt.strip(), None
            else:
                return None, "No prompt generated"
                
        except Exception as e:
            return None, f"Prompt generation failed: {e}"
    
    # ==================== CONTENT VALIDATION ====================
    
    async def validate_child_appropriate_content(self, text: str) -> Tuple[bool, str]:
        """
        Validate that content is appropriate for children
        
        Args:
            text: Text to validate
            
        Returns:
            Tuple of (is_appropriate, reason)
        """
        client = await self.get_client()
        if not client:
            return True, "Validation unavailable - OpenAI API not configured"
            
        try:
            validation_prompt = f"""
            Analyze this text for child-appropriate content:
            
            {text[:2000]}
            
            Check for:
            - Violence or scary content
            - Inappropriate language
            - Adult themes
            - Disturbing imagery
            
            Respond with ONLY:
            "APPROPRIATE" or "INAPPROPRIATE: [brief reason]"
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a content moderator specialized in children's literature. Be strict about child safety while allowing age-appropriate adventure and mild conflict."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            if result == "APPROPRIATE":
                return True, "Content is appropriate"
            elif result.startswith("INAPPROPRIATE:"):
                reason = result.replace("INAPPROPRIATE:", "").strip()
                return False, reason
            else:
                return True, "Content validation completed"
                
        except Exception as e:
            return True, f"Validation error: {e}"  # Default to appropriate if validation fails