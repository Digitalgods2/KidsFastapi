"""
Enhanced Character Extractor Service
Extracts character names AND their physical descriptions from book text
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from services.logger import get_logger
from services import chat_helper

logger = get_logger("services.character_extractor")

async def extract_characters_with_descriptions(
    content: str,
    book_title: str,
    book_author: str,
    chunk_size: int = 8000,
    max_characters: int = 10
) -> List[Dict[str, Any]]:
    """
    Extract characters with their physical descriptions from book content
    
    Returns:
        List of dicts with 'name', 'description', 'role' keys
    """
    
    # Split content into manageable chunks
    chunks = []
    for i in range(0, len(content), chunk_size):
        chunk = content[i:i + chunk_size]
        chunks.append(chunk)
    
    logger.info(f"Processing {len(chunks)} chunks for character extraction")
    
    # Process chunks to extract characters with descriptions
    all_characters = {}
    
    for idx, chunk in enumerate(chunks):
        if len(chunk.strip()) < 100:
            continue
            
        prompt = f"""Analyze this section from "{book_title}" by {book_author}.
Extract character information including:
1. Character name
2. Physical description (appearance, age, clothing, distinctive features)
3. Role (main character, supporting, villain, etc.)

Focus on ACTUAL characters, not metaphors or abstract concepts.

Text section:
{chunk[:6000]}

Return a JSON array with objects containing:
- "name": character name
- "description": physical description (be specific about appearance)
- "role": their role in the story

If no characters with descriptions found, return empty array []."""

        try:
            messages = [
                {"role": "system", "content": "You are an expert at analyzing literature and extracting detailed character information."},
                {"role": "user", "content": prompt}
            ]
            
            text, err = await chat_helper.generate_chat_text(
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            if err:
                logger.error(f"Error processing chunk {idx}: {err}")
                continue
                
            # Parse the JSON response
            try:
                # Clean up the response - sometimes GPT adds markdown
                if text:
                    text = text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    
                    characters_in_chunk = json.loads(text)
                    
                    # Merge character information
                    for char in characters_in_chunk:
                        name = char.get('name', '').strip()
                        if name:
                            if name not in all_characters:
                                all_characters[name] = {
                                    'name': name,
                                    'descriptions': [],
                                    'roles': []
                                }
                            
                            desc = char.get('description', '').strip()
                            if desc and desc not in all_characters[name]['descriptions']:
                                all_characters[name]['descriptions'].append(desc)
                            
                            role = char.get('role', '').strip()
                            if role and role not in all_characters[name]['roles']:
                                all_characters[name]['roles'].append(role)
                                
            except json.JSONDecodeError as je:
                logger.warning(f"Failed to parse JSON from chunk {idx}: {je}")
                continue
                
        except Exception as e:
            logger.error(f"Error processing chunk {idx}: {e}")
            continue
    
    # Consolidate character information
    final_characters = []
    for name, info in all_characters.items():
        # Combine descriptions
        combined_description = '; '.join(info['descriptions'][:3])  # Take top 3 descriptions
        combined_role = info['roles'][0] if info['roles'] else 'character'
        
        final_characters.append({
            'name': name,
            'description': combined_description or 'No physical description available',
            'role': combined_role
        })
    
    # Sort by importance (main characters first)
    def sort_key(char):
        role = char['role'].lower()
        if 'main' in role or 'protagonist' in role:
            return 0
        elif 'supporting' in role or 'secondary' in role:
            return 1
        elif 'villain' in role or 'antagonist' in role:
            return 2
        else:
            return 3
    
    final_characters.sort(key=sort_key)
    
    # Limit to max characters
    return final_characters[:max_characters]

async def update_book_character_descriptions(book_id: int) -> bool:
    """
    Update a book's character reference with detailed descriptions
    """
    from database_fixed import get_book_details, save_character_reference
    
    try:
        # Get book details
        book = await get_book_details(book_id)
        if not book:
            logger.error(f"Book {book_id} not found")
            return False
        
        # Read book content
        file_path = book.get('path') or book.get('original_content_path')
        if not file_path:
            logger.error(f"No file path for book {book_id}")
            return False
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract characters with descriptions
        characters = await extract_characters_with_descriptions(
            content,
            book.get('title', 'Unknown'),
            book.get('author', 'Unknown')
        )
        
        # Save to database
        character_data = {
            'characters_with_descriptions': characters,
            'extraction_version': '2.0',  # Mark this as enhanced extraction
            'character_count': len(characters)
        }
        
        # Also preserve any existing data
        existing = book.get('character_reference')
        if existing:
            try:
                existing_data = json.loads(existing) if isinstance(existing, str) else existing
                if 'word_count' in existing_data:
                    character_data['word_count'] = existing_data['word_count']
                if 'chapter_count' in existing_data:
                    character_data['chapter_count'] = existing_data['chapter_count']
            except:
                pass
        
        success = await save_character_reference(book_id, character_data)
        if success:
            logger.info(f"Updated character descriptions for book {book_id}: {len(characters)} characters")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to update character descriptions for book {book_id}: {e}")
        return False