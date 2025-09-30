"""
Character consistency helper for image generation
Provides concise character references without repetitive text in chapter content
"""
import json
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


async def get_character_reference_for_images(adaptation_id: int) -> Optional[Dict]:
    """
    Get character reference data for consistent image generation
    
    This retrieves detailed character descriptions from AI analysis and user input,
    formatted specifically for image prompt consistency (not chapter text).
    
    Args:
        adaptation_id: The adaptation ID
        
    Returns:
        Character reference dictionary with 'characters_reference' key,
        or None if no character data available
    """
    try:
        import database_fixed as database
        
        # Get adaptation and book details
        adaptation = await database.get_adaptation_details(adaptation_id)
        if not adaptation:
            logger.warning(f"No adaptation found for ID {adaptation_id}")
            return None
        
        book = await database.get_book_details(adaptation['book_id'])
        if not book:
            logger.warning(f"No book found for adaptation {adaptation_id}")
            return None
        
        # Try to get AI-analyzed character reference from book
        character_reference = None
        if book.get('character_reference'):
            try:
                character_reference = json.loads(book['character_reference'])
                logger.info(f"Loaded character reference for adaptation {adaptation_id}: {len(character_reference.get('characters_reference', {}))} characters")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse character_reference JSON: {e}")
        
        # Get user-specified key characters to preserve
        key_characters = []
        if adaptation.get('key_characters_to_preserve'):
            key_characters = [c.strip() for c in adaptation['key_characters_to_preserve'].split(',') if c.strip()]
            logger.info(f"Key characters to preserve: {key_characters}")
        
        # If we have detailed AI analysis, filter to key characters if specified
        if character_reference and 'characters_reference' in character_reference:
            chars = character_reference['characters_reference']
            
            # If user specified key characters, only include those
            # Otherwise include all characters from AI analysis
            if key_characters:
                filtered_chars = {}
                for name in key_characters:
                    # Case-insensitive matching
                    matched = False
                    for char_name, char_data in chars.items():
                        if char_name.lower() == name.lower():
                            filtered_chars[char_name] = char_data
                            matched = True
                            break
                    
                    # If no match in AI data, add basic entry
                    if not matched:
                        filtered_chars[name] = {
                            "role": "character",
                            "importance": "user_specified",
                            "physical_appearance": {"description": "character from the story"},
                            "personality_traits": [],
                            "special_attributes": {"abilities_or_items": ""}
                        }
                
                return {"characters_reference": filtered_chars} if filtered_chars else None
            else:
                # Return all AI-analyzed characters
                return character_reference
        
        # Fallback: Create basic character reference from key_characters_to_preserve
        elif key_characters:
            logger.info(f"Creating basic character reference from key_characters: {key_characters}")
            basic_ref = {
                "characters_reference": {
                    name: {
                        "role": "character",
                        "importance": "user_specified",
                        "physical_appearance": {"description": "character from the story"},
                        "personality_traits": [],
                        "special_attributes": {"abilities_or_items": ""}
                    }
                    for name in key_characters
                }
            }
            return basic_ref
        
        logger.info(f"No character reference data available for adaptation {adaptation_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error getting character reference: {e}", exc_info=True)
        return None


def format_character_reference_concise(characters: Dict) -> str:
    """
    Format character reference data into a concise reference guide for image prompts
    
    This creates a compact "character sheet" style reference that ensures visual
    consistency without adding verbose descriptions to each chapter.
    
    Args:
        characters: Character reference dictionary (with 'characters_reference' key)
        
    Returns:
        Formatted string for prompt inclusion, or empty string if no data
    """
    if not characters or 'characters_reference' not in characters:
        return ""
    
    chars = characters['characters_reference']
    if not chars:
        return ""
    
    descriptions = []
    
    for name, details in chars.items():
        # Build concise description
        parts = []
        
        # Physical appearance (most important for consistency)
        if 'physical_appearance' in details:
            phys = details['physical_appearance'].get('description', '').strip()
            if phys and phys != "character from the story":
                parts.append(phys)
        
        # Key personality traits (for expression/pose guidance)
        if 'personality_traits' in details and details['personality_traits']:
            traits = details['personality_traits'][:2]  # Limit to 2 most important
            if traits:
                parts.append(f"({', '.join(traits)})")
        
        # Special items/abilities (if visually relevant)
        if 'special_attributes' in details:
            special = details['special_attributes'].get('abilities_or_items', '').strip()
            if special and len(special) < 100:  # Only include if brief
                parts.append(f"[{special}]")
        
        # Only include character if we have meaningful description
        if parts:
            # Format: Name: description (traits) [items]
            char_desc = f"{name}: {'; '.join(parts)}"
            descriptions.append(char_desc)
    
    if not descriptions:
        return ""
    
    # Return as compact reference list
    return "CHARACTER CONSISTENCY GUIDE:\n" + "\n".join(f"• {desc}" for desc in descriptions)


def should_include_character_reference(chapter_number: int, total_chapters: int) -> bool:
    """
    Determine if character reference should be included for this chapter
    
    Currently always returns True for maximum consistency, but this function
    provides a hook for future optimization (e.g., only include in first few chapters)
    
    Args:
        chapter_number: Current chapter number
        total_chapters: Total number of chapters in adaptation
        
    Returns:
        True if character reference should be included
    """
    # Always include for maximum consistency across all chapters
    # Future: Could optimize to reduce token usage for books with many chapters
    return True


async def get_formatted_character_reference(
    adaptation_id: int,
    chapter_number: int = 1,
    total_chapters: int = 1
) -> str:
    """
    High-level helper: Get formatted character reference for a specific chapter
    
    This is the main entry point for including character consistency in image prompts.
    
    Args:
        adaptation_id: The adaptation ID
        chapter_number: Current chapter number (for future optimization)
        total_chapters: Total chapters (for future optimization)
        
    Returns:
        Formatted character reference string ready for prompt inclusion,
        or empty string if no character data available
    """
    # Check if we should include character reference
    if not should_include_character_reference(chapter_number, total_chapters):
        return ""
    
    # Get character data
    char_data = await get_character_reference_for_images(adaptation_id)
    if not char_data:
        return ""
    
    # Format concisely
    return format_character_reference_concise(char_data)
