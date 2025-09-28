"""
Legacy OpenAI Service for KidsKlassiks FastAPI application
Uses OpenAI library version 0.28.1 with the old API style
"""

import openai
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
import config

# Set up OpenAI with legacy API style
openai.api_key = config.OPENAI_API_KEY

class LegacyOpenAIService:
    """Service class for OpenAI API operations using legacy API"""
    
    def __init__(self):
        """Initialize legacy OpenAI service"""
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        
        # Set the API key globally for legacy API
        openai.api_key = config.OPENAI_API_KEY
        print(f"✅ Legacy OpenAI service initialized with API key: {config.OPENAI_API_KEY[:10]}...")
    
    # ==================== CHARACTER ANALYSIS ====================
    
    async def analyze_characters_from_text(self, text: str, book_title: str) -> List[str]:
        """
        Analyze text to extract character names using legacy API
        """
        try:
            # Process in chunks for better results
            chunk_size = 8000
            chunks = []
            
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                chunks.append(chunk)
            
            print(f"📄 Processing {len(chunks)} chunks for character analysis")
            
            all_characters = set()
            
            for idx, chunk in enumerate(chunks):
                print(f"🔍 Analyzing chunk {idx + 1}/{len(chunks)}...")
                
                if len(chunk.strip()) < 100:
                    continue
                
                prompt = f"""Extract character names from this section of "{book_title}".
Find ALL characters mentioned: main characters, minor characters, named people, animals with names.
Only return actual character names, not descriptions or titles alone.

Text section:
{chunk[:4000]}

Return ONLY comma-separated character names. If no characters found, return "None"."""
                
                try:
                    # Use legacy ChatCompletion API
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an expert at identifying character names in literature. Extract only actual names of characters."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=300
                    )
                    
                    chunk_characters = response.choices[0].message.content.strip()
                    
                    if chunk_characters and chunk_characters.lower() != "none":
                        characters_in_chunk = [c.strip() for c in chunk_characters.split(',') if c.strip() and len(c.strip()) > 1]
                        all_characters.update(characters_in_chunk)
                        print(f"✅ Chunk {idx + 1}: Found {len(characters_in_chunk)} characters")
                    else:
                        print(f"⚪ Chunk {idx + 1}: No characters found")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️ Error in chunk {idx + 1}: {str(e)}")
                    continue
            
            # Clean and deduplicate characters
            unique_characters = []
            seen_lower = set()
            
            for char in sorted(all_characters):
                if char and len(char) > 1 and len(char) < 50:  # Reasonable name length
                    char_clean = char.strip().strip('"').strip("'")
                    char_lower = char_clean.lower()
                    
                    # Skip common non-character words
                    skip_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'chapter', 'book', 'story', 'tale'}
                    if char_lower not in skip_words and char_lower not in seen_lower:
                        seen_lower.add(char_lower)
                        unique_characters.append(char_clean)
            
            print(f"✅ Found {len(unique_characters)} unique characters")
            return unique_characters
            
        except Exception as e:
            print(f"❌ Character analysis failed: {e}")
            return []
    
    # ==================== TEXT TRANSFORMATION ====================
    
    async def transform_chapter(
        self, 
        chapter_text: str, 
        chapter_number: int, 
        adaptation: Dict[str, Any]
    ) -> str:
        """Transform a chapter text for the target age group and style"""
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
            
            # Use legacy ChatCompletion API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an expert children's book author specializing in adapting classic literature for young readers. Transform text to be appropriate for ages {age_group} with a {style} style."},
                    {"role": "user", "content": transformation_prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Chapter transformation failed: {e}")
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
    
    async def generate_chapter_image_prompt(
        self, 
        transformed_text: str, 
        chapter_number: int, 
        adaptation: Dict[str, Any]
    ) -> str:
        """Generate image prompt for a chapter"""
        try:
            prompt_generation = f"""
            Create a detailed image prompt for this chapter from a children's book:
            
            Chapter {chapter_number}:
            {transformed_text[:1000]}...
            
            Style: {adaptation['transformation_style']}
            Target Age: {adaptation['target_age_group']}
            
            Create an image prompt that captures the main scene and is appropriate for children.
            Return only the image prompt, no additional text.
            """
            
            # Use legacy ChatCompletion API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating image prompts for children's book illustrations."},
                    {"role": "user", "content": prompt_generation}
                ],
                max_tokens=500,
                temperature=0.6
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Image prompt generation failed: {e}")
            return f"Children's book illustration for chapter {chapter_number}, showing the main characters in a {adaptation['transformation_style'].lower()} style"
    
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
            
            # Use legacy ChatCompletion API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at creating image prompts for children's book covers."},
                    {"role": "user", "content": prompt_generation}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Cover prompt generation failed: {e}")
            return f"A colorful children's book cover for {book['title']}, {adaptation['transformation_style'].lower()} style"
    
    # ==================== IMAGE GENERATION ====================
    
    async def generate_image(
        self, 
        prompt: str, 
        model: str = "dall-e-3",
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate image using DALL-E with legacy API"""
        try:
            # Use legacy Image API
            response = openai.Image.create(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality if model == "dall-e-3" else "standard",
                n=1
            )
            
            return response.data[0].url, None
            
        except Exception as e:
            print(f"❌ Image generation failed: {e}")
            return None, f"Error generating image: {e}"
    
    # ==================== UTILITY METHODS ====================
    
    async def test_connection(self) -> bool:
        """Test the OpenAI API connection"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'connection test successful'"}
                ],
                max_tokens=10,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            print(f"✅ OpenAI connection test: {result}")
            return True
            
        except Exception as e:
            print(f"❌ OpenAI connection test failed: {e}")
            return False

# Global service instance
_legacy_service = None

def get_legacy_openai_service() -> LegacyOpenAIService:
    """Get or create the legacy OpenAI service instance"""
    global _legacy_service
    if _legacy_service is None:
        _legacy_service = LegacyOpenAIService()
    return _legacy_service
