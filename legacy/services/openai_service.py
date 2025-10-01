"""
OpenAI service for KidsKlassiks FastAPI application
Handles GPT text transformation and DALL-E image generation
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
import config
from models import AgeGroup, TransformationStyle, ImageModel

class OpenAIService:
    """Service class for OpenAI API operations"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = None
        if config.OPENAI_API_KEY and config.OPENAI_API_KEY.startswith('sk-'):
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        else:
            print("⚠️  OpenAI API key not configured - AI features disabled")
    
    # ==================== CHARACTER ANALYSIS ====================
    
    async def analyze_story_characters(self, story_content: str, book_title: str = "Unknown Book") -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Analyze a story using GPT to extract detailed character descriptions
        and create comprehensive JSON reference for consistent illustrations
        """
        if not self.client:
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
                    "distinctive_features": "scars, birthmarks, etc"
                  }},
                  "clothing": {{
                    "typical_outfit": "detailed description",
                    "colors": "primary colors worn",
                    "style": "fashion style, era, formality",
                    "accessories": "jewelry, weapons, tools, etc"
                  }},
                  "personality": {{
                    "traits": ["list", "of", "key", "traits"],
                    "typical_expressions": "happy, sad, determined, etc",
                    "mannerisms": "gestures, habits"
                  }},
                  "special_attributes": {{
                    "magical_abilities": "if any",
                    "special_items": "owned objects",
                    "unique_features": "anything supernatural"
                  }}
                }}
              }},
              "settings_reference": {{
                "LocationName": {{
                  "description": "detailed description",
                  "atmosphere": "mood, feeling",
                  "key_features": ["notable", "elements"],
                  "lighting": "typical lighting conditions",
                  "colors": "dominant color palette"
                }}
              }},
              "story_metadata": {{
                "genre": "fantasy/adventure/etc",
                "time_period": "historical period or era",
                "overall_tone": "whimsical/dark/heroic/etc",
                "art_style_suggestions": "recommended visual style"
              }}
            }}
            
            Focus on visual details. Include 5-10 most important characters and 3-5 key settings.
            
            Story text:
            {story_content[:8000]}...
            """
            
            response = self.client.chat.completions.create(
                model=config.get_optimal_gpt_model('character_analysis', 'high'),
                messages=[
                    {"role": "system", "content": "You are an expert character analyst and visual description specialist for children's book illustrations."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=config.GPT_MAX_TOKENS,
                temperature=config.GPT_TEMPERATURE
            )
            
            character_json_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_start = character_json_text.find('{')
            json_end = character_json_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                character_json_text = character_json_text[json_start:json_end]
            
            character_reference = json.loads(character_json_text)
            return character_reference, None
            
        except json.JSONDecodeError as e:
            return None, f"Failed to parse character analysis JSON: {e}"
        except Exception as e:
            return None, f"Error analyzing characters: {e}"
    
    # ==================== TEXT TRANSFORMATION ====================
    
    async def transform_chapter(
        self, 
        chapter_text: str, 
        chapter_number: int, 
        adaptation: Dict[str, Any]
    ) -> str:
        """Transform a chapter text for the target age group and style"""
        if not self.client:
            return f"[OpenAI unavailable] {chapter_text}"
        try:
            age_group = adaptation['target_age_group']
            style = adaptation['transformation_style']
            theme = adaptation.get('overall_theme_tone', '')
            characters = adaptation.get('key_characters_to_preserve', '')
            
            # Create age-appropriate transformation prompt
            transformation_prompt = f"""
            Transform this chapter from a classic story into a children's book suitable for ages {age_group}.
            
            Transformation Guidelines:
            - Style: {style}
            - Theme/Tone: {theme}
            - Key Characters to Preserve: {characters}
            - Chapter Number: {chapter_number}
            
            Age-Specific Requirements for {age_group}:
            {self._get_age_specific_guidelines(age_group)}
            
            Original Chapter Text:
            {chapter_text}
            
            Please transform this chapter while:
            1. Maintaining the core story elements
            2. Using age-appropriate language and concepts
            3. Keeping the specified style and tone
            4. Preserving important character details
            5. Making it engaging for the target age group
            
            Return only the transformed text, no additional commentary.
            """
            
            response = self.client.chat.completions.create(
                model=config.get_optimal_gpt_model('scene_generation', 'medium'),
                messages=[
                    {"role": "system", "content": f"You are an expert children's book author specializing in adapting classic literature for young readers. Transform text to be appropriate for ages {age_group} with a {style} style."},
                    {"role": "user", "content": transformation_prompt}
                ],
                max_tokens=config.GPT_MAX_TOKENS,
                temperature=config.GPT_TEMPERATURE
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error transforming chapter: {e}"
    
    def _get_age_specific_guidelines(self, age_group: str) -> str:
        """Get age-specific transformation guidelines"""
        guidelines = {
            "3-5": """
            - Use very simple sentences (5-10 words max)
            - Focus on basic emotions and actions
            - Include repetitive phrases for engagement
            - Avoid complex concepts or scary elements
            - Use concrete, familiar objects and situations
            - Include sound effects and interactive elements
            """,
            "6-8": """
            - Use simple to moderate sentence structure
            - Introduce basic problem-solving concepts
            - Include dialogue and character interactions
            - Mild adventure elements are acceptable
            - Explain new concepts in simple terms
            - Include moral lessons naturally
            """,
            "9-12": """
            - More complex sentence structures allowed
            - Can include adventure and mild conflict
            - Character development and relationships
            - Introduction of more sophisticated themes
            - Can handle some suspense and mystery
            - Include educational elements naturally
            """
        }
        return guidelines.get(age_group, guidelines["6-8"])
    
    # ==================== IMAGE PROMPT GENERATION ====================
    
    async def generate_cover_prompt(
        self, 
        book: Dict[str, Any], 
        adaptation: Dict[str, Any]
    ) -> str:
        """Generate cover image prompt for a book adaptation"""
        try:
            prompt_generation = f"""
            Create a detailed image prompt for a children's book cover based on this adaptation:
            
            Book: "{book['title']}" by {book.get('author', 'Unknown')}
            Target Age: {adaptation['target_age_group']}
            Style: {adaptation['transformation_style']}
            Theme: {adaptation.get('overall_theme_tone', '')}
            
            Create a cover prompt that:
            1. Captures the essence of the story
            2. Appeals to the target age group
            3. Matches the transformation style
            4. Includes the main characters if specified
            5. Is suitable for children's book illustration
            
            Return only the image prompt, no additional text.
            """
            
            response = self.client.chat.completions.create(
                model=config.get_optimal_gpt_model('quick_suggestions', 'low'),
                messages=[
                    {"role": "system", "content": "You are an expert at creating image prompts for children's book covers."},
                    {"role": "user", "content": prompt_generation}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"A colorful children's book cover for {book['title']}, {adaptation['transformation_style'].lower()} style"
    
    async def generate_chapter_image_prompt(
        self, 
        transformed_text: str, 
        chapter_number: int, 
        adaptation: Dict[str, Any],
        character_reference: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate image prompt for a chapter"""
        try:
            if character_reference:
                # Use character reference for consistent imagery
                return await self._generate_prompt_with_character_reference(
                    transformed_text, chapter_number, adaptation, character_reference
                )
            else:
                # Generate basic prompt without character reference
                return await self._generate_basic_chapter_prompt(
                    transformed_text, chapter_number, adaptation
                )
                
        except Exception as e:
            return f"Children's book illustration for chapter {chapter_number}, {adaptation['transformation_style'].lower()} style"
    
    async def _generate_prompt_with_character_reference(
        self, 
        chapter_text: str, 
        chapter_number: int, 
        adaptation: Dict[str, Any],
        character_reference: Dict[str, Any]
    ) -> str:
        """Generate prompt using character reference for consistency"""
        try:
            char_ref_str = json.dumps(character_reference, indent=2)
            
            prompt_generation = f"""
            Using the character reference, create a detailed image prompt for Chapter {chapter_number}.
            
            CHARACTER REFERENCE:
            {char_ref_str}
            
            CHAPTER TEXT:
            {chapter_text}
            
            ADAPTATION STYLE: {adaptation['transformation_style']}
            TARGET AGE: {adaptation['target_age_group']}
            
            Create an image prompt that:
            1. Uses the character descriptions from the reference
            2. Captures the key scene from this chapter
            3. Maintains visual consistency with other chapters
            4. Appeals to the target age group
            5. Matches the transformation style
            
            Return only the image prompt, no additional text.
            """
            
            response = self.client.chat.completions.create(
                model=config.get_optimal_gpt_model('scene_generation', 'medium'),
                messages=[
                    {"role": "system", "content": "You are an expert at creating consistent image prompts for children's book illustrations using character references."},
                    {"role": "user", "content": prompt_generation}
                ],
                max_tokens=1000,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return await self._generate_basic_chapter_prompt(chapter_text, chapter_number, adaptation)
    
    async def _generate_basic_chapter_prompt(
        self, 
        chapter_text: str, 
        chapter_number: int, 
        adaptation: Dict[str, Any]
    ) -> str:
        """Generate basic chapter prompt without character reference"""
        try:
            prompt_generation = f"""
            Create a detailed image prompt for this chapter from a children's book:
            
            Chapter {chapter_number}:
            {chapter_text[:1000]}...
            
            Style: {adaptation['transformation_style']}
            Target Age: {adaptation['target_age_group']}
            
            Create an image prompt that captures the main scene and is appropriate for children.
            Return only the image prompt, no additional text.
            """
            
            response = self.client.chat.completions.create(
                model=config.get_optimal_gpt_model('quick_suggestions', 'low'),
                messages=[
                    {"role": "system", "content": "You are an expert at creating image prompts for children's book illustrations."},
                    {"role": "user", "content": prompt_generation}
                ],
                max_tokens=500,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Children's book illustration for chapter {chapter_number}, showing the main characters in a {adaptation['transformation_style'].lower()} style"
    
    # ==================== IMAGE GENERATION ====================
    
    async def generate_image(
        self,
        prompt: str,
        model: ImageModel | str = ImageModel.DALLE_3,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate image using OpenAI Images API. Returns (image_url, error)."""
        if not self.client:
            return None, "OpenAI API not configured"
        try:
            # Normalize model input to string name and enum for logic
            model_enum = None
            model_name = None
            if isinstance(model, ImageModel):
                model_enum = model
                model_name = model.value
            elif isinstance(model, str):
                model_name = model
                # Try to coerce to enum if possible
                try:
                    model_enum = ImageModel(model)
                except Exception:
                    model_enum = None
            else:
                model_name = "dall-e-3"
                model_enum = ImageModel.DALLE_3

            # Optimize prompt for model (pass enum if available)
            optimized_prompt = self._optimize_prompt_for_model(prompt, model_enum or ImageModel.DALLE_3)

            # Supported models here: DALL-E 2, DALL-E 3, GPT-Image-1
            if model_name in (ImageModel.DALLE_2.value, ImageModel.DALLE_3.value, ImageModel.GPT_IMAGE_1.value):
                kwargs = {
                    "model": model_name,
                    "prompt": optimized_prompt,
                    "size": size,
                    "n": 1,
                }
                if model_name == ImageModel.DALLE_3.value:
                    kwargs["quality"] = quality
                response = self.client.images.generate(**kwargs)
                return response.data[0].url, None

            return None, f"Model {model_name} not supported by OpenAI service"

        except Exception as e:
            return None, f"Error generating image: {e}"
    
    def _optimize_prompt_for_model(self, prompt: str, model: ImageModel) -> str:
        """Optimize prompt for specific model limitations"""
        limit = config.MODEL_LIMITS.get(model.value, 4000)
        
        if len(prompt) <= limit:
            return prompt
        
        # Truncate while preserving important parts
        if model == ImageModel.DALLE_2:
            # DALL-E 2 has stricter limits, keep only essential elements
            words = prompt.split()
            truncated = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > limit:
                    break
                truncated.append(word)
                current_length += len(word) + 1
            
            return " ".join(truncated)
        else:
            # For other models, simple truncation
            return prompt[:limit]
    
    # ==================== UTILITY METHODS ====================
    
    async def validate_content_appropriateness(
        self, 
        content: str, 
        age_group: AgeGroup
    ) -> Tuple[bool, Optional[str]]:
        """Validate if content is appropriate for target age group"""
        try:
            validation_prompt = f"""
            Evaluate if this content is appropriate for children aged {age_group.value}:
            
            {content[:1000]}...
            
            Consider:
            1. Language complexity
            2. Themes and concepts
            3. Emotional content
            4. Scary or inappropriate elements
            
            Respond with only "APPROPRIATE" or "INAPPROPRIATE" followed by a brief reason.
            """
            
            response = self.client.chat.completions.create(
                model=config.get_optimal_gpt_model('validation', 'low'),
                messages=[
                    {"role": "system", "content": "You are an expert in child development and age-appropriate content."},
                    {"role": "user", "content": validation_prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            result = response.choices[0].message.content.strip()
            is_appropriate = result.startswith("APPROPRIATE")
            reason = result.split(" ", 1)[1] if " " in result else None
            
            return is_appropriate, reason
            
        except Exception as e:
            return True, f"Validation error: {e}"  # Default to appropriate if validation fails

# ==================== Consolidation Alias ====================
# The modern implementation lives in services/openai_service_new.py.
# We expose it here so existing imports (`from services.openai_service import ...`)
# continue to work without changes.

try:
    from services.openai_service_new import OpenAIService as _ModernOpenAIService  # type: ignore

    class OpenAIService(_ModernOpenAIService):  # noqa: D401,E501
        """Backward-compatibility alias to modern OpenAIService implementation."""
        pass

    def get_openai_service():
        """Factory helper kept for legacy code paths."""
        return OpenAIService()
except ImportError:  # pragma: no cover
    # If the modern module is missing, keep the original class definition above.
    import warnings
    warnings.warn(
        "services.openai_service_new could not be imported; falling back to legacy implementation.",
        RuntimeWarning,
    )

