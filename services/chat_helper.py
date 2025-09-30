"""
Unified chat helper using openai-python >= 1.0
Provides rich prompt generators for cover and chapter image prompts
"""
from typing import Any, Dict, List, Optional, Tuple
import logging
import os

from openai import OpenAI
import config

logger = logging.getLogger(__name__)

# Initialize a single client instance
_client: Optional[OpenAI] = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not getattr(config, 'OPENAI_API_KEY', None):
            raise ValueError("OpenAI API key not configured")
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client

async def generate_chat_text(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Tuple[Optional[str], Optional[str]]:
    """Generic chat generation that returns (text, error)."""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model or getattr(config, 'DEFAULT_GPT_MODEL', 'gpt-4o-mini'),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        return text.strip(), None
    except Exception as e:
        logger.error(f"Chat generation error: {e}")
        return None, str(e)

# ---------- Rich prompt builders ----------

def build_cover_prompt_template(book: Dict[str, Any], adaptation: Dict[str, Any]) -> List[Dict[str, str]]:
    title = book.get('title', 'Unknown Title')
    author = book.get('author', 'Unknown Author')
    age_group = adaptation.get('target_age_group', '6-8')
    style = adaptation.get('transformation_style', 'Simple & Direct')
    theme = adaptation.get('overall_theme_tone', '')
    characters = (adaptation.get('key_characters_to_preserve') or '').strip()

    system = (
        "You are an expert prompt engineer and children's book illustrator. "
        "Create visually rich, child-friendly prompts that produce a single cohesive cover image."
    )
    user = f"""
Create a detailed DALL-E image prompt for a children's book cover.

Book: "{title}" by {author}
Target Age: {age_group}
Style: {style}
Theme/Tone: {theme}
Key Characters (if any): {characters or 'N/A'}

Guidelines:
- One single, engaging scene suitable for a cover
- Friendly, whimsical tone; bright colors; clear focal point
- Include the book title "{title}" and author name "{author}" as clear, legible text prominently displayed on the cover
- Position the title at the top or center, and author name at the bottom
- Use child-friendly, easy-to-read fonts for the text
- Avoid violence or scary elements; suitable for children
- Describe characters (appearance, expressions), setting, mood, color palette, composition
- Keep under 200 words; no extra commentary
"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

def build_chapter_prompt_template(
    chapter_text: str,
    chapter_number: int,
    adaptation: Dict[str, Any],
    character_reference: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    age_group = adaptation.get('target_age_group', '6-8')
    style = adaptation.get('transformation_style', 'Simple & Direct')

    system = (
        "You are an expert prompt engineer and children's book illustrator. "
        "Create visually rich, child-friendly prompts that produce a single cohesive illustration."
    )
    char_ref = f"\nCharacter Reference (JSON excerpt):\n{str(character_reference)[:1500]}\n" if character_reference else ""
    user = f"""
Create a detailed DALL-E image prompt for Chapter {chapter_number}.

Target Age: {age_group}
Style: {style}
{char_ref}
Chapter Excerpt (trimmed):
{(chapter_text or '')[:2500]}

Guidelines:
- One single, engaging scene from this chapter
- Friendly, whimsical tone; bright colors; clear subject and background
- Consistent character depiction (names, looks) across chapters
- Describe characters (appearance, pose, expression), setting, mood, palette, composition
- Avoid text in the image; avoid violence/scary content
- Keep under 180 words; no extra commentary
"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

# ---------- High-level helpers ----------

async def generate_cover_prompt(book: Dict[str, Any], adaptation: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    messages = build_cover_prompt_template(book, adaptation)
    return await generate_chat_text(messages, temperature=0.6, max_tokens=500)

async def generate_chapter_image_prompt(
    transformed_text: str,
    chapter_number: int,
    adaptation: Dict[str, Any],
    character_reference: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    messages = build_chapter_prompt_template(transformed_text, chapter_number, adaptation, character_reference)
    return await generate_chat_text(messages, temperature=0.7, max_tokens=500)
