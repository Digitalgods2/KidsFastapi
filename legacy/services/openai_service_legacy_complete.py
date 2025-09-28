"""
Legacy OpenAI Service for KidsKlassiks
Uses OpenAI 0.28.1 API that works without the 'proxies' parameter issue
Includes all prompt generation methods from the original Streamlit app
"""

import openai
import os
import asyncio
from typing import Optional, Tuple, Dict, Any
import config

def get_legacy_openai_service():
    """Get configured legacy OpenAI service instance"""
    return LegacyOpenAIService()

import sys

# Helper to detect OpenAI major version once
_MAJOR_VERSION = 0
try:
    _MAJOR_VERSION = int(openai.__version__.split(".")[0])
except Exception:
    _MAJOR_VERSION = 1  # assume new
class LegacyOpenAIService:
    def __init__(self):
        """Initialize service and set API key"""
        openai.api_key = config.OPENAI_API_KEY

    # Internal helper for ChatCompletion compatible with both 0.x and 1.x
    async def _chat_completion(self, messages, model="gpt-3.5-turbo", **kwargs):
        """Wrapper that calls the appropriate OpenAI chat completion endpoint and returns content string."""
        if _MAJOR_VERSION >= 1 and hasattr(openai, "chat"):
            response = openai.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                **kwargs
            )
        # Extract assistant content
        try:
            return response.choices[0].message.content.strip()
        except AttributeError:
            return response["choices"][0]["message"]["content"].strip()
        """Initialize legacy OpenAI service"""
        openai.api_key = config.OPENAI_API_KEY
        
    async def generate_cover_prompt(self, book: Dict[str, Any], adaptation: Dict[str, Any]) -> str:
        """Generate cover image prompt based on book and adaptation details (SDK-version agnostic)."""
        try:
            prompt_body = f"""
            Create a richly detailed (at least 60-word) image prompt for a children's book cover based on this information:
            
            Book Title: {book.get('title', 'Unknown')}
            Author: {book.get('author', 'Unknown')}
            Target Age Group: {adaptation.get('target_age_group', '6-8')}
            Transformation Style: {adaptation.get('transformation_style', 'Simple & Direct')}
            Theme/Tone: {adaptation.get('overall_theme_tone', 'Adventure and friendship')}
            Key Characters: {adaptation.get('key_characters_to_preserve', 'Main characters')}
            
            The prompt must describe:
            1. Main characters (appearance & expression) in a child-friendly style
            2. Setting and atmosphere
            3. Color palette and visual motifs suitable for the age group
            4. Mood that matches the theme ({adaptation.get('overall_theme_tone', 'Adventure and friendship')})
            
            Write one sentence that begins exactly with: "A colorful children's book cover illustration showing..."
            """

            messages = [
                {"role": "system", "content": "You are an expert at creating long, vivid, specific prompts for AI image generation."},
                {"role": "user", "content": prompt_body}
            ]

            generated_prompt = await self._chat_completion(messages, model="gpt-3.5-turbo-0125", max_tokens=600, temperature=0.85)

            if not generated_prompt.startswith("A colorful children's book cover"):
                generated_prompt = f"A colorful children's book cover illustration showing {generated_prompt}"

            return generated_prompt
            
        except Exception as e:
            print(f"❌ Error generating cover prompt: {e}")
            return f"A colorful children's book cover illustration for '{book.get('title', 'Unknown')}' showing the main characters in a magical adventure, designed for {adaptation.get('target_age_group', '6-8')} year olds with bright colors and friendly cartoon style."
    
    async def generate_chapter_image_prompt(self, transformed_text: str, chapter_number: int, adaptation: Dict[str, Any]) -> str:
        """Generate image prompt for a specific chapter"""
        try:
            # Truncate text if too long
            text_preview = transformed_text[:1500] if len(transformed_text) > 1500 else transformed_text
            
            prompt = f"""
            Create an engaging, richly detailed image prompt for Chapter {chapter_number} of a children's adaptation.
            
            Use this transformed chapter excerpt:
            {text_preview}
            
            Include in the prompt explicitly:
            - Scene description (time of day, lighting, weather, atmosphere)
            - Setting and key background elements
            - Main characters with specific, visual details (faces, hair, clothing, posture, expressions)
            - Composition guidance (foreground/midground/background) and focal point
            - Color palette suitable for ages {adaptation.get('target_age_group', '6-8')}
            - Art style guidance (whimsical children's-book illustration)
            - Small whimsical details to delight children
            - Avoid violence or scary imagery; ensure positivity and warmth
            
            Start the output with exactly: "A whimsical children's book illustration showing"
            Output only the image prompt text, 120–220 words.
            """
            
            generated = await self._chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert in crafting vivid, production-ready prompts for children's book illustrations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            generated_prompt = generated
            if not generated_prompt.startswith("A whimsical children's book illustration"):
                generated_prompt = f"A whimsical children's book illustration showing {generated_prompt}"
            return generated_prompt
            
        except Exception as e:
            print(f"❌ Error generating chapter prompt: {e}")
            return f"A whimsical children's book illustration showing the events of chapter {chapter_number}, with colorful characters in a magical setting, designed for {adaptation.get('target_age_group', '6-8')} year olds."
    
    async def generate_image(self, prompt: str, model: str = "dall-e-3", size: str = "1024x1024", quality: str = "standard") -> Tuple[Optional[str], Optional[str]]:
        """Generate an image using either the new or legacy OpenAI API, depending on installed version"""
        try:
            print("🎨 Generating image via OpenAI API ...")
            print(f"📝 Prompt preview: {prompt[:80]}...")
            print(f"🔧 Model: {model}  Size: {size}  Quality: {quality}")

            # Detect library major version (1.x uses the new images.generate endpoint)
            try:
                major_version = int(openai.__version__.split(".")[0])
            except Exception:
                major_version = 1  # assume new api if unsure

            if major_version >= 1 and hasattr(openai, "images"):
                # New >=1.0 interface -----------------------------------------
                response = openai.images.generate(
                    model=model,
                    prompt=prompt,
                    size=size,
                    n=1,
                    **({"quality": quality} if model == "dall-e-3" else {})
                )
            else:
                # Legacy <1.0 interface --------------------------------------
                response = openai.Image.create(
                    model=model,
                    prompt=prompt,
                    size=size if model == "dall-e-3" else "1024x1024",
                    **({"quality": quality} if model == "dall-e-3" else {}),
                    n=1
                )

            # Extract URL ------------------------------------------------------
            image_url = None
            if response is not None:
                # Both APIs return an object with .data list of objects each having .url
                data_list = getattr(response, "data", None) or response.get("data") if isinstance(response, dict) else None
                if data_list and len(data_list) > 0:
                    image_url = data_list[0].url if hasattr(data_list[0], "url") else data_list[0].get("url")

            if image_url:
                print(f"✅ Image generated successfully: {image_url}")
                return image_url, None
            else:
                error_msg = "No image URL returned from OpenAI API"
                print(f"❌ {error_msg}")
                return None, error_msg

        except Exception as e:
            error_msg = f"Error generating image: {str(e)}"
            print(f"❌ {error_msg}")
            return None, error_msg
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Test OpenAI API connection"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10
            )
            
            if response and response.choices:
                return True, "OpenAI API connection successful"
            else:
                return False, "No response from OpenAI API"
                
        except Exception as e:
            return False, f"OpenAI API connection failed: {str(e)}"
    
    async def analyze_characters(self, book_content: str, book_title: str) -> Tuple[Optional[str], Optional[str]]:
        """Analyze characters in the book content using legacy OpenAI API"""
        try:
            print(f"🎭 Starting legacy character analysis for book: {book_title}")
            
            # Truncate content if too long
            content_preview = book_content[:8000] if len(book_content) > 8000 else book_content
            
            prompt = f"""
            Analyze this book text and extract all the main and important minor characters.
            
            Book Title: {book_title}
            
            Text to analyze:
            {content_preview}
            
            Please provide a comma-separated list of character names only. Include:
            - Main protagonists and antagonists
            - Important supporting characters
            - Characters that appear multiple times
            - Characters essential to the plot
            
            Format: Character Name 1, Character Name 2, Character Name 3, etc.
            
            Do not include generic terms like "narrator" or "townspeople". Only specific named characters.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert literary analyst. Extract character names accurately and concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            if response and response.choices:
                characters_text = response.choices[0].message.content.strip()
                print(f"✅ Legacy character analysis complete: {characters_text[:100]}...")
                return characters_text, None
            else:
                error_msg = "No response from OpenAI for character analysis"
                print(f"❌ {error_msg}")
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Error in character analysis: {str(e)}"
            print(f"❌ {error_msg}")
            return None, error_msg
