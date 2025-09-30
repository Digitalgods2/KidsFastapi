# Character Preservation Analysis - KidsKlassiks

## Summary
**Current Status**: ⚠️ **Partially Implemented** - Character preservation data is collected but **NOT consistently used in image generation prompts**

---

## How Character Preservation Currently Works

### 1. **Data Collection Phase**

#### A. User Input (`key_characters_to_preserve`)
- **Location**: `adaptations` table in database
- **Field**: `key_characters_to_preserve` (TEXT)
- **Storage Format**: Comma-separated character names (e.g., "Alice, White Rabbit, Mad Hatter")
- **Input Source**: User manually enters character names when creating an adaptation

#### B. AI Character Analysis (`character_reference`)
- **Location**: `books` table in database
- **Field**: `character_reference` (TEXT/JSON)
- **Service**: `services/character_analyzer.py` - `CharacterAnalyzer` class
- **Method**: `analyze_characters_with_ai()` - Uses GPT-4 to extract:
  - Character names
  - Roles (protagonist/antagonist/companion/etc.)
  - Physical descriptions
  - Personality traits
  - Special abilities/items
  - Importance (major/minor)

**Example Character Reference JSON Structure**:
```json
{
  "characters_reference": {
    "Alice": {
      "role": "protagonist",
      "importance": "major",
      "physical_appearance": {
        "description": "young girl with blonde hair, wearing a blue dress with white apron"
      },
      "personality_traits": ["curious", "brave", "imaginative"],
      "special_attributes": {
        "abilities_or_items": "grows and shrinks with potions"
      }
    },
    "White Rabbit": {
      "role": "companion",
      "importance": "major",
      "physical_appearance": {
        "description": "white rabbit wearing a waistcoat, carrying a pocket watch"
      },
      "personality_traits": ["anxious", "punctual", "hurried"],
      "special_attributes": {
        "abilities_or_items": "pocket watch"
      }
    }
  }
}
```

#### C. Character Name Curation
- **Service**: `services/character_analyzer.py`
- **Method**: `curate_names()` - Normalizes and ranks characters by:
  - Frequency of mentions in text
  - Alphabetical order
  - Caps list to top 25 characters (configurable via settings)

---

### 2. **Where Character Data SHOULD Be Used (But Isn't Fully)**

#### A. Cover Image Generation

**File**: `services/chat_helper.py`
**Function**: `build_cover_prompt_template()`

```python
def build_cover_prompt_template(book: Dict[str, Any], adaptation: Dict[str, Any]) -> List[Dict[str, str]]:
    # ...
    characters = (adaptation.get('key_characters_to_preserve') or '').strip()
    # ...
    user = f"""
    Create a detailed DALL-E image prompt for a children's book cover.
    
    Book: "{title}" by {author}
    Target Age: {age_group}
    Style: {style}
    Theme/Tone: {theme}
    Key Characters (if any): {characters or 'N/A'}  # ✅ USED HERE
    
    Guidelines:
    - Describe characters (appearance, expressions), setting, mood, color palette, composition
    """
```

**Status**: ✅ **Implemented** - `key_characters_to_preserve` from adaptation IS included in cover prompts

---

#### B. Chapter Image Generation

**File**: `services/chat_helper.py`
**Function**: `build_chapter_prompt_template()`

```python
def build_chapter_prompt_template(
    chapter_text: str,
    chapter_number: int,
    adaptation: Dict[str, Any],
    character_reference: Optional[Dict[str, Any]] = None,  # ⚠️ PARAMETER EXISTS
) -> List[Dict[str, str]]:
    age_group = adaptation.get('target_age_group', '6-8')
    style = adaptation.get('transformation_style', 'Simple & Direct')
    
    system = "You are an expert prompt engineer..."
    
    # ⚠️ Character reference is OPTIONALLY included
    char_ref = f"\nCharacter Reference (JSON excerpt):\n{str(character_reference)[:1500]}\n" if character_reference else ""
    
    user = f"""
    Create a detailed DALL-E image prompt for Chapter {chapter_number}.
    
    Target Age: {age_group}
    Style: {style}
    {char_ref}  # ⚠️ ONLY INCLUDED IF PASSED
    Chapter Excerpt (trimmed):
    {(chapter_text or '')[:2500]}
    
    Guidelines:
    - Consistent character depiction (names, looks) across chapters
    - Describe characters (appearance, pose, expression), setting, mood, palette, composition
    """
```

**Status**: ⚠️ **PARTIALLY IMPLEMENTED** - The function accepts `character_reference` parameter, but...

---

### 3. **THE CRITICAL PROBLEM** ❌

#### In `services/image_generation_service.py`

**Function**: `generate_image_prompt()`

```python
async def generate_image_prompt(self, chapter: Dict, adaptation_id: int) -> str:
    """
    Generate an AI-powered image prompt based on chapter content
    """
    try:
        # Get adaptation details for context
        import database_fixed as database
        adaptation = await database.get_adaptation_details(adaptation_id)
        
        chapter_text = chapter.get('original_chapter_text', '')[:2000]
        age_group = adaptation.get('target_age_group', 'Ages 6-8')
        style = adaptation.get('transformation_style', 'Simple & Direct')
        
        # ❌ PROBLEM: Uses a simple inline prompt instead of chat_helper!
        prompt_generation_text = f"""
        Create a detailed image prompt for a children's book illustration based on this chapter excerpt:
        
        Chapter Text: {chapter_text}
        
        Target Age Group: {age_group}
        Style: {style}
        
        Generate a prompt that describes a single, engaging scene...
        """
        
        # ❌ CALLS chat_helper but uses build_chapter_prompt_template
        from services import chat_helper
        messages = chat_helper.build_chapter_prompt_template(
            chapter_text,
            chapter.get('chapter_number', 1),
            adaptation,
            # ❌ CRITICAL ISSUE: character_reference parameter is NOT passed!
            # Should be: character_reference=character_data
        )
        text, err = await chat_helper.generate_chat_text(messages, temperature=0.7, max_tokens=500)
        if text:
            return text.strip()
        # Fallback to basic prompt
        return f"A children's book illustration showing characters from Chapter {chapter.get('chapter_number', 1)}, colorful and engaging for {age_group}"
```

**The Issue**:
1. ✅ Function calls `build_chapter_prompt_template()` which accepts `character_reference`
2. ❌ BUT it never passes `character_reference=...` as the 4th parameter
3. ❌ Result: The detailed character descriptions from AI analysis are **NEVER included in chapter image prompts**

---

## What IS Being Used vs What ISN'T

### ✅ Currently Used in Image Prompts:
1. **Adaptation Context**:
   - Target age group
   - Transformation style
   - Overall theme/tone
2. **Chapter Content**:
   - Original chapter text (first 2000 characters)
   - Chapter number
3. **Cover Images ONLY**:
   - `key_characters_to_preserve` (simple comma-separated names)

### ❌ NOT Currently Used in Chapter Image Prompts:
1. **Character Reference JSON** (from AI analysis):
   - Physical descriptions
   - Personality traits
   - Special abilities/items
   - Character roles
2. **key_characters_to_preserve** (user-provided character list)
3. **Detailed character appearance consistency guidelines**

---

## Impact on Image Quality

### Current Result:
- ❌ **No character consistency** across chapter images
- ❌ Each image prompt relies only on chapter text mentions
- ❌ AI has no "memory" of how characters should look
- ❌ Same character might appear with different:
  - Hair color
  - Clothing
  - Age appearance
  - Physical features

### Expected Result (If Fixed):
- ✅ **Consistent character depictions** across all chapters
- ✅ AI receives detailed physical descriptions for each generation
- ✅ Characters maintain same appearance throughout the book
- ✅ Personality traits influence pose/expression in images

---

## How to Fix This

### Option 1: Quick Fix (Use Existing Data)

**Modify**: `services/image_generation_service.py` - `generate_image_prompt()`

```python
async def generate_image_prompt(self, chapter: Dict, adaptation_id: int) -> str:
    """Generate an AI-powered image prompt based on chapter content"""
    try:
        import database_fixed as database
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        
        # ✅ FIX: Get book details to access character_reference
        book = await database.get_book_details(adaptation['book_id'])
        
        # ✅ FIX: Parse character reference JSON
        character_reference = None
        if book and book.get('character_reference'):
            try:
                import json
                character_reference = json.loads(book['character_reference'])
            except:
                character_reference = None
        
        # ✅ FIX: Pass character_reference to prompt template
        from services import chat_helper
        messages = chat_helper.build_chapter_prompt_template(
            chapter.get('original_chapter_text', '')[:2000],
            chapter.get('chapter_number', 1),
            adaptation,
            character_reference=character_reference  # ✅ NOW INCLUDED!
        )
        
        text, err = await chat_helper.generate_chat_text(messages, temperature=0.7, max_tokens=500)
        if text:
            return text.strip()
        
        # Fallback
        return f"A children's book illustration for Chapter {chapter.get('chapter_number', 1)}"
    except Exception as e:
        logger.error(f"Image prompt generation error: {e}")
        return f"A children's book illustration for Chapter {chapter.get('chapter_number', 1)}"
```

### Option 2: Enhanced Fix (Add Character Extraction Helper)

**Create**: `services/character_helper.py`

```python
"""Character consistency helper for image generation"""
import json
from typing import Dict, Optional, List

async def get_character_descriptions_for_adaptation(adaptation_id: int) -> Optional[Dict]:
    """
    Get consolidated character descriptions for consistent image generation
    
    Returns:
        Dictionary with character names mapped to their detailed descriptions
    """
    import database_fixed as database
    
    # Get adaptation and book details
    adaptation = await database.get_adaptation_details(adaptation_id)
    if not adaptation:
        return None
    
    book = await database.get_book_details(adaptation['book_id'])
    if not book:
        return None
    
    # Start with AI-analyzed character reference
    character_reference = None
    if book.get('character_reference'):
        try:
            character_reference = json.loads(book['character_reference'])
        except:
            pass
    
    # Get user-specified key characters
    key_characters = []
    if adaptation.get('key_characters_to_preserve'):
        key_characters = [c.strip() for c in adaptation['key_characters_to_preserve'].split(',')]
    
    # Build consolidated description
    if character_reference and 'characters_reference' in character_reference:
        chars = character_reference['characters_reference']
        
        # Filter to only key characters if specified
        if key_characters:
            chars = {name: details for name, details in chars.items() if name in key_characters}
        
        return chars
    
    # Fallback: return simple list if no detailed reference
    if key_characters:
        return {name: {"role": "character", "importance": "mentioned"} for name in key_characters}
    
    return None

def format_character_descriptions_for_prompt(characters: Dict) -> str:
    """
    Format character descriptions for inclusion in image prompts
    
    Args:
        characters: Character reference dictionary
        
    Returns:
        Formatted string for prompt inclusion
    """
    if not characters:
        return ""
    
    descriptions = []
    for name, details in characters.items():
        parts = [f"**{name}**"]
        
        if 'physical_appearance' in details:
            phys = details['physical_appearance'].get('description', '')
            if phys:
                parts.append(f"- Appearance: {phys}")
        
        if 'personality_traits' in details and details['personality_traits']:
            traits = ", ".join(details['personality_traits'][:3])
            parts.append(f"- Traits: {traits}")
        
        if 'special_attributes' in details:
            special = details['special_attributes'].get('abilities_or_items', '')
            if special:
                parts.append(f"- Special: {special}")
        
        descriptions.append("\n".join(parts))
    
    return "\n\n".join(descriptions)
```

Then use it in `generate_image_prompt()`:

```python
from services.character_helper import get_character_descriptions_for_adaptation

async def generate_image_prompt(self, chapter: Dict, adaptation_id: int) -> str:
    """Generate an AI-powered image prompt with character consistency"""
    try:
        import database_fixed as database
        
        # Get character descriptions
        characters = await get_character_descriptions_for_adaptation(adaptation_id)
        
        # Get adaptation details
        adaptation = await database.get_adaptation_details(adaptation_id)
        
        # Generate prompt with character reference
        from services import chat_helper
        messages = chat_helper.build_chapter_prompt_template(
            chapter.get('original_chapter_text', '')[:2000],
            chapter.get('chapter_number', 1),
            adaptation,
            character_reference=characters  # ✅ Now includes detailed descriptions
        )
        
        # ... rest of the function
```

---

## Testing the Fix

### Before Fix - Check Current Behavior:
```bash
# Look at a chapter image prompt in the database
sqlite3 kidsklassiks.db "SELECT ai_prompt FROM chapters WHERE image_url IS NOT NULL LIMIT 1;"
# Should NOT contain detailed character descriptions
```

### After Fix - Verify Improvement:
```bash
# Regenerate an image and check the prompt
sqlite3 kidsklassiks.db "SELECT ai_prompt FROM chapters WHERE chapter_id = X;"
# Should contain:
# - Character Reference (JSON excerpt)
# - Physical descriptions
# - Personality traits
```

### Visual Test:
1. Generate images for Chapter 1-3 of a book
2. Check if the same character (e.g., "Alice") appears consistently:
   - Same hair color
   - Same clothing
   - Same approximate age
   - Similar facial features

---

## Additional Improvements to Consider

### 1. **Style Consistency Settings**
Add to `settings` table:
- `character_consistency_level`: "strict" | "moderate" | "loose"
- `character_description_detail`: "high" | "medium" | "low"

### 2. **Character Appearance Locking**
Allow users to "lock" character appearances after first generation:
- Save the actual prompt used for first appearance
- Reuse exact description in subsequent chapters

### 3. **Reference Image Support** (Advanced)
- Upload reference images for characters
- Use image-to-image generation for consistency
- Requires DALL-E 3 with image input or Stable Diffusion

### 4. **Character Gallery**
Create a UI page showing:
- All extracted characters
- Their descriptions
- First appearance image
- Edit capability for descriptions

---

## Conclusion

**Current State**: Character preservation is a **half-implemented feature**. The infrastructure exists but isn't properly wired up for chapter image generation.

**Impact**: Users get inconsistent character appearances across chapter images, reducing book quality.

**Fix Difficulty**: ⭐⭐☆☆☆ (Easy) - Just needs to pass one extra parameter and fetch one extra database field

**Recommended Action**: Implement **Option 1 (Quick Fix)** immediately to enable basic character consistency, then consider **Option 2** for enhanced control.

---

## Related Files

- `services/character_analyzer.py` - Character extraction and analysis
- `services/chat_helper.py` - Prompt building with character support
- `services/image_generation_service.py` - **NEEDS FIX** - Missing character_reference
- `database_fixed.py` - Database functions for characters
- `models.py` - Data model definitions
- `routes/images.py` - Image generation endpoints
