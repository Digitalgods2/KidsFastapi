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

# No longer using cached client - create fresh clients with current API key

async def get_client() -> OpenAI:
    """Get OpenAI client with API key from database settings (preferred) or environment"""
    api_key = None
    
    # Try to get API key from database settings first
    try:
        import database_fixed as database
        api_key = await database.get_setting("openai_api_key", None)
    except Exception:
        pass
    
    # Fallback to config/environment if not in database
    if not api_key:
        api_key = getattr(config, 'OPENAI_API_KEY', None)
    
    if not api_key:
        raise ValueError("OpenAI API key not found in environment variables")
        
    return OpenAI(api_key=api_key)

async def generate_chat_text(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Tuple[Optional[str], Optional[str]]:
    """Generic chat generation that returns (text, error)."""
    try:
        client = await get_client()
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
    
    # Build character descriptions based on well-known stories
    character_descriptions = ""
    book_id = book.get('book_id')
    char_ref = None  # TODO: Fetch character reference if needed
    
    if char_ref:
            # Check for enhanced character descriptions
            if 'characters_with_descriptions' in char_ref:
                # We have detailed descriptions!
                character_descriptions = f"\n\nCHARACTER DESCRIPTIONS from '{title}':\n"
                char_list = char_ref['characters_with_descriptions']
                
                # Match characters mentioned in adaptation with detailed descriptions
                for char_data in char_list:
                    char_name = char_data.get('name', '')
                    if any(name in characters for name in char_name.split()):
                        desc = char_data.get('description', '')
                        role = char_data.get('role', '')
                        if desc:
                            character_descriptions += f"- {char_name} ({role}): {desc}\n"
                
                if character_descriptions.endswith(":\n"):
                    # No descriptions found, use fallback
                    character_descriptions = ""
            
            # Fallback to generic descriptions for well-known stories
            if not character_descriptions and characters:
                character_descriptions = f"\n\nIMPORTANT CHARACTER CONTEXT from '{title}':\n"
                character_descriptions += f"The following characters appear in this story: {characters}\n"
                character_descriptions += f"Please research the original story '{title}' by {author} to accurately depict these characters with their traditional appearances.\n"
                
                # Add specific guidance for well-known characters
                if "Christmas Carol" in title:
                    if "Scrooge" in characters or "Ebenezer" in characters:
                        character_descriptions += "- Ebenezer Scrooge: An elderly man with gray/white hair, often in Victorian-era dark coat and top hat\n"
                    if "Tiny Tim" in characters:
                        character_descriptions += "- Tiny Tim: A young boy with a crutch, Bob Cratchit's youngest son, cheerful despite his disability\n"
                    if "Cratchit" in characters:
                        character_descriptions += "- Bob Cratchit: A humble clerk, middle-aged man in modest Victorian clothing\n"
                elif "Wizard of Oz" in title:
                    if "Dorothy" in characters:
                        character_descriptions += "- Dorothy: A young girl with brown hair in pigtails, blue gingham dress, and ruby/silver slippers\n"
                    if "Scarecrow" in characters:
                        character_descriptions += "- Scarecrow: Made of straw, wearing old clothes, floppy hat\n"
                    if "Tin Man" in characters or "Woodman" in characters:
                        character_descriptions += "- Tin Man: Made entirely of tin/silver metal, holding an axe\n"
                    if "Lion" in characters:
                        character_descriptions += "- Cowardly Lion: Large lion with a big mane, expressive face\n"

    system = (
        "You are an expert prompt engineer and children's book illustrator with deep knowledge of classic literature. "
        "Create visually rich, child-friendly prompts that accurately depict characters from well-known stories. "
        "When creating prompts for classic tales, ensure character appearances match their traditional depictions."
    )
    user = f"""
Create a detailed image generation prompt for a children's book cover.

Book: "{title}" by {author}
Target Age: {age_group}
Style: {style}
Theme/Tone: {theme}
Key Characters: {characters or 'N/A'}
{character_descriptions}

Guidelines:
- One single, engaging scene suitable for a cover featuring the key characters
- IF this is a well-known story (like A Christmas Carol, The Wizard of Oz, etc.), ensure characters match their traditional appearances
- Friendly, whimsical tone; bright colors; clear focal point
- Include the book title "{title}" and author name "{author}" as clear, legible text prominently displayed on the cover
- Position the title at the top or center, and author name at the bottom
- Use child-friendly, easy-to-read fonts for the text
- Avoid violence or scary elements; suitable for children
- Describe characters with specific physical details (hair color, clothing, age, distinctive features)
- Include setting, mood, color palette, composition
- Keep under 200 words; no extra commentary
- IMPORTANT: Return ONLY the image description, do NOT add any prefix like '**Prompt for...**' or headers
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
    formatted_char_ref: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Build chapter image prompt with optional character consistency reference
    
    Args:
        chapter_text: The chapter text excerpt
        chapter_number: Chapter number
        adaptation: Adaptation details
        character_reference: Raw character reference dict (legacy support)
        formatted_char_ref: Pre-formatted character reference string (preferred)
    """
    age_group = adaptation.get('target_age_group', '6-8')
    style = adaptation.get('transformation_style', 'Simple & Direct')

    system = (
        "You are an expert prompt engineer and children's book illustrator. "
        "Create visually rich, child-friendly prompts that produce a single cohesive illustration. "
        "When character consistency guides are provided, you MUST include the COMPLETE physical description "
        "for any character mentioned - do NOT summarize or paraphrase character appearances."
    )
    
    # Use formatted reference if provided (preferred), otherwise fallback to raw dict
    char_ref = ""
    if formatted_char_ref:
        char_ref = f"\n{formatted_char_ref}\n"
    elif character_reference:
        # Legacy fallback: format the raw dict
        char_ref = f"\nCharacter Reference (JSON excerpt):\n{str(character_reference)[:1500]}\n"
    
    user = f"""
Create a detailed image generation prompt for Chapter {chapter_number}.

Target Age: {age_group}
Style: {style}
{char_ref}
Chapter Excerpt (trimmed):
{(chapter_text or '')[:2500]}

Guidelines:
- One single, engaging scene from this chapter
- Friendly, whimsical tone; bright colors; clear subject and background
- CRITICAL CHARACTER RULE: When mentioning ANY character from the CHARACTER CONSISTENCY GUIDE above, 
  you MUST include their COMPLETE physical description from the guide. Do NOT abbreviate or summarize.
  Example: If guide says "Toto is a small black dog with long silky hair and small black eyes", 
  your prompt must say "Toto, a small black dog with long silky hair and small black eyes" - 
  NOT just "a small dog, Toto" or "Toto, a dog".
- Describe characters (appearance, pose, expression), setting, mood, palette, composition
- Avoid text in the image; avoid violence/scary content
- Keep under 200 words; no extra commentary
- IMPORTANT: Return ONLY the image description, do NOT add any prefix like '**Prompt for...**' or headers
"""
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

# ---------- Text transformation ----------

def build_text_transformation_template(
    original_text: str,
    adaptation: Dict[str, Any],
    book: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Build prompt for transforming original text to age-appropriate version"""
    age_group = adaptation.get('target_age_group', '6-8')
    style = adaptation.get('transformation_style', 'Simple & Direct')
    theme = adaptation.get('overall_theme_tone', '')
    title = book.get('title', 'Unknown')
    
    # Age-specific guidelines
    age_guidelines = {
        '3-5': {
            'vocabulary': 'very simple words (1-2 syllables)',
            'sentence_length': 'very short sentences (3-5 words)',
            'concepts': 'concrete, familiar concepts only',
            'length': 'significantly shorter - aim for 30-40% of original'
        },
        '6-8': {
            'vocabulary': 'simple, everyday words',
            'sentence_length': 'short sentences (5-10 words)',
            'concepts': 'simple concepts with clear explanations',
            'length': 'moderately shorter - aim for 50-60% of original'
        },
        '9-12': {
            'vocabulary': 'age-appropriate vocabulary with some challenging words',
            'sentence_length': 'varied sentence length (10-15 words average)',
            'concepts': 'more complex ideas with context',
            'length': 'similar length to original, 70-80%'
        }
    }
    
    guidelines = age_guidelines.get(age_group, age_guidelines['6-8'])
    
    system = (
        f"You are an expert children's book adapter specializing in rewriting classic literature "
        f"for ages {age_group}. You maintain the story's essence while making it accessible and engaging "
        f"for young readers."
    )
    
    user = f"""
Rewrite this excerpt from "{title}" for children ages {age_group}.

TARGET AGE GROUP: {age_group}
STYLE: {style}
THEME/TONE: {theme or 'Maintain the original story\'s mood'}

AGE-APPROPRIATE GUIDELINES:
- Vocabulary: {guidelines['vocabulary']}
- Sentence Length: {guidelines['sentence_length']}
- Concepts: {guidelines['concepts']}
- Target Length: {guidelines['length']}

CRITICAL RULES:
1. Preserve the core story events and plot
2. Keep character names and main actions
3. Simplify complex vocabulary and sentence structures
4. Replace archaic or difficult words with modern equivalents
5. Break long paragraphs into shorter ones
6. Maintain the emotional tone appropriate for the age group
7. Remove or simplify overly complex descriptions
8. Use active voice and direct language
9. Keep dialogue but simplify the language
10. Make it engaging and readable for the target age

ORIGINAL TEXT:
{original_text}

REWRITTEN TEXT (for ages {age_group}):"""
    
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

async def transform_chapter_text(
    original_text: str,
    adaptation: Dict[str, Any],
    book: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Transform original chapter text to age-appropriate version
    
    Args:
        original_text: Original chapter text
        adaptation: Adaptation details (target_age_group, style, etc.)
        book: Book details (title, author)
        
    Returns:
        Tuple of (transformed_text, error_message)
    """
    if not original_text or not original_text.strip():
        return None, "No text provided for transformation"
    
    messages = build_text_transformation_template(original_text, adaptation, book)
    
    # Use higher max_tokens for text transformation (can be long)
    # Calculate based on original length
    original_tokens = len(original_text.split()) * 1.3  # Rough token estimate
    max_tokens = min(16000, int(original_tokens * 0.8))  # 80% of original as max
    max_tokens = max(4000, max_tokens)  # At least 4000 tokens
    
    return await generate_chat_text(
        messages, 
        model='gpt-4o-mini',  # Fast and cost-effective for text transformation
        temperature=0.7,
        max_tokens=max_tokens
    )

# ---------- High-level helpers ----------

async def analyze_book_for_cover_prompt(
    book_content: str,
    book: Dict[str, Any],
    adaptation: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Analyze entire book content to generate an AI-powered cover prompt
    
    Args:
        book_content: Full text content of the book
        book: Book details (title, author)
        adaptation: Adaptation details (target_age_group, style, etc.)
        
    Returns:
        Tuple of (cover_prompt, error_message)
    """
    if not book_content or not book_content.strip():
        return None, "No book content provided for analysis"
    
    title = book.get('title', 'Unknown Title')
    author = book.get('author', 'Unknown Author')
    age_group = adaptation.get('target_age_group', '6-8')
    style = adaptation.get('transformation_style', 'Simple & Direct')
    theme = adaptation.get('overall_theme_tone', '')
    
    # Get character consistency reference
    formatted_char_ref = ""
    try:
        from services.character_helper import get_formatted_character_reference
        formatted_char_ref = await get_formatted_character_reference(
            adaptation.get("adaptation_id"),
            chapter_number=1,  # Cover is like chapter 1
            total_chapters=1
        )
    except Exception as e:
        logger.warning(f"Could not load character reference for cover: {e}")
    
    # Truncate book content if too long (keep first ~10,000 words for analysis)
    words = book_content.split()
    if len(words) > 10000:
        book_excerpt = ' '.join(words[:10000]) + "\n\n[Book continues...]"
    else:
        book_excerpt = book_content
    
    system = (
        "You are an expert at creating concise, effective image generation prompts for AI art tools like DALL-E and Midjourney. "
        "You write clear visual descriptions that produce beautiful children's book covers."
    )
    
    # Build character section
    char_section = ""
    if formatted_char_ref:
        char_section = f"\n\n{formatted_char_ref}\n\nWhen characters appear in your prompt, use their exact physical descriptions from above.\n"
    
    user = f"""
Create a detailed IMAGE GENERATION PROMPT for a children's book cover of "{title}" by {author}.

Your output will be sent to an AI image generator (DALL-E/Stable Diffusion/Midjourney).
Write a visual description an AI can use to generate the cover image.

Story context (for inspiration):
{book_excerpt[:3000]}

Cover requirements:
- Target audience: Children ages {age_group}
- Art style: Whimsical, colorful, imaginative children's book illustration
- Mood: Capture the emotional heart of the story (joyful, magical, mysterious, etc.)
- Composition: Symbolic and evocative, not a literal scene
- Text on cover: Title "{title}" and "Written by {author}"
{char_section}
FORMAT YOUR RESPONSE AS:
A single paragraph describing the cover image in vivid visual detail. Include:
- Main visual elements (characters, objects, setting)
- Character descriptions (if featured) using exact details from guide above
- Color palette and lighting
- Mood and atmosphere  
- Art style (e.g., "whimsical children's book illustration style")
- Text placement: "{title}" at top, "Written by {author}" at bottom

Keep it under 150 words. Write ONLY the image prompt, no explanations or meta-commentary.

IMAGE PROMPT:"""
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    
    # Use higher max_tokens for book analysis
    return await generate_chat_text(messages, temperature=0.7, max_tokens=800)

async def generate_cover_prompt(book: Dict[str, Any], adaptation: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    messages = build_cover_prompt_template(book, adaptation)
    return await generate_chat_text(messages, temperature=0.6, max_tokens=500)

async def generate_chapter_image_prompt(
    transformed_text: str,
    chapter_number: int,
    adaptation: Dict[str, Any],
    character_reference: Optional[Dict[str, Any]] = None,
    formatted_char_ref: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate chapter image prompt with optional character consistency
    
    Args:
        transformed_text: Chapter text
        chapter_number: Chapter number
        adaptation: Adaptation details
        character_reference: Raw character dict (legacy)
        formatted_char_ref: Pre-formatted character reference (preferred)
    """
    messages = build_chapter_prompt_template(
        transformed_text, 
        chapter_number, 
        adaptation, 
        character_reference,
        formatted_char_ref
    )
    return await generate_chat_text(messages, temperature=0.7, max_tokens=500)

async def transform_chapter_text(
    original_text: str,
    age_group: str,
    book_title: str = "Unknown",
    chapter_number: int = 1,
    preserve_names: str = ""
) -> Tuple[Optional[str], Optional[str]]:
    """
    Transform chapter text to age-appropriate version (simplified interface)
    
    Args:
        original_text: Original chapter text
        age_group: Target age group (e.g., "3-5", "6-8", "9-12")
        book_title: Title of the book
        chapter_number: Chapter number
        preserve_names: Comma-separated character names to preserve
        
    Returns:
        Tuple of (transformed_text, error_message)
    """
    if not original_text or not original_text.strip():
        return None, "No text provided for transformation"
    
    # Create minimal adaptation dict for compatibility
    adaptation = {
        "target_age_group": age_group,
        "transformation_style": "Simple & Direct",
        "key_characters_to_preserve": preserve_names
    }
    
    book = {
        "title": book_title,
        "author": ""
    }
    
    messages = build_text_transformation_template(original_text, adaptation, book)
    
    # Calculate appropriate max_tokens
    original_tokens = len(original_text.split()) * 1.3  # Rough token estimate
    max_tokens = min(16000, int(original_tokens * 0.8))  # 80% of original as max
    max_tokens = max(4000, max_tokens)  # At least 4000 tokens
    
    return await generate_chat_text(
        messages, 
        model='gpt-4o-mini',  # Fast and cost-effective
        temperature=0.7,
        max_tokens=max_tokens
    )

async def generate_image_prompt_for_chapter(
    chapter_text: str,
    chapter_number: int,
    adaptation: Dict[str, Any],
    include_character_consistency: bool = True
) -> Optional[str]:
    """
    Generate an image prompt for a chapter
    
    Args:
        chapter_text: Chapter text (transformed or original)
        chapter_number: Chapter number
        adaptation: Adaptation details
        include_character_consistency: Whether to include character consistency
        
    Returns:
        Generated prompt or None if error
    """
    formatted_char_ref = None
    
    if include_character_consistency:
        try:
            from services.character_helper import get_formatted_character_reference
            formatted_char_ref = await get_formatted_character_reference(
                adaptation.get("adaptation_id"),
                chapter_number
            )
        except Exception:
            pass  # Character consistency optional
    
    prompt, error = await generate_chapter_image_prompt(
        transformed_text=chapter_text,
        chapter_number=chapter_number,
        adaptation=adaptation,
        formatted_char_ref=formatted_char_ref
    )
    
    return prompt if not error else None
