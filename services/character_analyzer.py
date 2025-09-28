"""
Character Analysis Service for KidsKlassiks
Based on the working Streamlit implementation
"""

import json
import re
from collections import Counter
from typing import Dict, List, Optional
from services import chat_helper
import os

def _normalize_name(name: str) -> str:
    # Preserve identity-bearing titles like 'Lady' and 'Sir', but remove Mr./Mrs./Ms./Dr.
    # Unicode-safe: keep letters, spaces, apostrophes (ASCII ' and U+2019 ’), and hyphens.
    # Strategy: strip disallowed punctuation by iterating characters.
    # Then collapse spaces and Title Case.
    try:
        name = re.sub(r"\b(Mr\.|Mrs\.|Ms\.|Dr\.)\b\s*", "", name, flags=re.IGNORECASE)
    except Exception:
        pass
    cleaned = []
    for ch in str(name):
        if ch.isalpha() or ch in " -'’":
            cleaned.append(ch)
    name = "".join(cleaned)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()


# Common words to exclude from character name suggestions
COMMON_EXCLUDE = {
    "The", "And", "But", "For", "Not", "With", "From", "They", "This", "That", "Have", "Been", "Were", "Said", "Each", "Which", "Their", "Time", "Will", "About", "Would", "There", "Could", "Other", "After", "First", "Well", "Many", "Some", "What", "Know", "Way", "She", "May", "Say", "He", "My", "One", "All", "Would", "Her", "So", "An", "When", "Much", "How", "Then", "Them", "These", "So", "Him", "Has"
}

class CharacterAnalyzer:
    def __init__(self):
        """Character analyzer using chat_helper (no direct client)"""
        pass
    
    def suggest_character_names(self, text: str, max_names: int = 15) -> str:
        """
        Suggest character names from text using simple pattern matching
        
        Args:
            text: The book text to analyze
            max_names: Maximum number of character names to return
            
        Returns:
            Comma-separated string of suggested character names
        """
        try:
            # Use first 50k characters for analysis
            sample = text[:50000]
            
            # Find capitalized words that could be names
            tokens = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*", sample)
            
            # Filter out common words and short tokens
            names = [t for t in tokens if t not in COMMON_EXCLUDE and len(t) > 2]
            
            # Count occurrences and return most common
            counts = Counter(names)
            return ", ".join([n for n, _ in counts.most_common(max_names)])
            
        except Exception as e:
            from services.logger import get_logger
            get_logger("services.character_analyzer").error("suggest_character_names_error", extra={"component":"services.character_analyzer","error":str(e)})
            return ""
    
    async def analyze_characters_with_ai(self, text: str, book_title: str = "", book_author: str = "") -> Dict:
        """
        Analyze characters using OpenAI GPT-4 for comprehensive character detection
        
        Args:
            text: The full book text to analyze
            book_title: Title of the book for context
            book_author: Author of the book for context
            
        Returns:
            Dictionary containing character analysis results
        """
        try:
            # Use a large portion of the text to catch characters throughout the story
            sample = text[:400000]
            context = f'"{book_title}" by {book_author}' if book_title and book_author else "this story"
            prompt = f"""You are analyzing {context}.

Your task is to find and analyze ALL major and minor characters that appear in the text.

For each character you find, provide:
1. Character name (use the most common name they're referred to by)
2. Role in story (protagonist/antagonist/companion/supporting/magical_being/family/authority_figure)
3. Importance (major/minor)
4. Brief physical description for image consistency
5. Key personality traits
6. Special abilities or items if any

Be thorough and include:
- Main characters (protagonists, antagonists)
- Supporting characters (family, friends, helpers)
- Minor but memorable characters
- Magical beings or creatures
- Authority figures
- Any character that appears multiple times or has dialogue

Return as JSON with this structure:
{{
  "characters_reference": {{
    "Character Name": {{
      "role": "role_here",
      "importance": "major/minor",
      "physical_appearance": {{
        "description": "detailed physical description for consistent image generation"
      }},
      "personality_traits": ["trait1", "trait2", "trait3"],
      "special_attributes": {{
        "abilities_or_items": "description of special abilities, magical items, or notable possessions"
      }}
    }}
  }}
}}

Text to analyze:
{sample}"""

            # Ask for JSON; parse if possible
            text_out, err = await chat_helper.generate_chat_text(
                messages=[
                    {"role": "system", "content": "You are a literary analyst specializing in character identification. You must be thorough and find ALL major and minor characters mentioned in the text. Focus on characters that have names, dialogue, or significant actions."},
                    {"role": "user", "content": prompt}
                ],
                model=getattr(__import__('config'), 'DEFAULT_GPT_MODEL', 'gpt-4o-mini'),
                temperature=0.1,
                max_tokens=4000,
            )
            if err:
                return {"error": err}
            try:
                character_analysis = json.loads(text_out or "{}")
            except json.JSONDecodeError as e:
                return {
                    "error": "Failed to parse character analysis JSON",
                    "details": str(e),
                    "raw_response": text_out,
                }

            char_count = len(character_analysis.get('characters_reference', {}))
            character_analysis['analysis_metadata'] = {
                'characters_found': char_count,
                'text_sample_length': len(sample),
                'success': True
            }
            return character_analysis
        except Exception as e:
            return {"error": f"Character analysis failed: {e}"}
    
    def format_characters_for_display(self, character_analysis: Dict) -> str:
        """
        Format character analysis results for display in the UI
        
        Args:
            character_analysis: Results from analyze_characters_with_ai
            
        Returns:
            Formatted string of character names for display
        """
        if "error" in character_analysis:
            return ""
        
        characters_ref = character_analysis.get('characters_reference', {})
        if not characters_ref:
            return ""
        
        # Sort characters by importance (major first) and then alphabetically
        sorted_chars = sorted(
            characters_ref.items(),
            key=lambda x: (x[1].get('importance', 'minor') != 'major', x[0])
        )
        
        return ", ".join([name for name, _ in sorted_chars])
    
    def get_character_descriptions_for_prompts(self, character_analysis: Dict) -> Dict[str, str]:
        """
        Extract character descriptions optimized for image generation prompts
        
        Args:
            character_analysis: Results from analyze_characters_with_ai
            
        Returns:
            Dictionary mapping character names to their descriptions
        """
        if "error" in character_analysis:
            return {}
        
        characters_ref = character_analysis.get('characters_reference', {})
        descriptions = {}
        
        for name, details in characters_ref.items():
            # Combine physical appearance and key traits for image generation
            physical = details.get('physical_appearance', {}).get('description', '')
            traits = details.get('personality_traits', [])
            special = details.get('special_attributes', {}).get('abilities_or_items', '')
            
            description_parts = []
            if physical:
                description_parts.append(physical)
            if traits:
                description_parts.append(f"personality: {', '.join(traits[:3])}")  # Limit to 3 traits
            if special:
                description_parts.append(special)
            descriptions[name] = "; ".join(description_parts)
        
        return descriptions

    @staticmethod
    def curate_names(raw_names: List[str], text_corpus: str, cap: int = 25) -> List[str]:
        """Normalize, frequency-rank, and cap character names.
        - Normalize honorifics and case.
        - Count frequency of occurrences in the provided corpus (case-insensitive).
        - Sort by frequency desc, then alpha.
        - Return top cap names.
        """
        if not raw_names:
            return []
        # Normalize and dedupe
        normalized = []
        seen = set()
        for n in raw_names:
            nn = _normalize_name(str(n))
            if nn and nn.lower() not in seen:
                seen.add(nn.lower())
                normalized.append(nn)
        if not text_corpus:
            # Just return capped normalized list
            return normalized[:cap]
        # Frequency count by whole-word-ish matches
        corpus = text_corpus.lower()
        freqs = []
        for name in normalized:
            # build regex for name as words
            parts = [re.escape(p) for p in name.split() if p]
            if not parts:
                count = 0
            else:
                pattern = r"\b" + r"\s+".join(parts) + r"\b"
                count = len(re.findall(pattern, corpus, flags=re.IGNORECASE))
            freqs.append((name, count))
        freqs.sort(key=lambda x: (-x[1], x[0]))
        return [n for n, _ in freqs[:cap]]

    @staticmethod
    async def curate_for_adaptation(adaptation: dict, chapters: List[dict], default_cap: int = 25) -> List[str]:
        """Curate character names for an adaptation using existing key_characters_to_preserve
        or book-level characters if available; otherwise infer from chapters.
        Returns the curated list (normalized, ranked, capped).
        """
        from services.logger import get_logger
        log = get_logger("services.character_analyzer")
        try:
            # Settings for cap
            from database import get_setting
            cap_str = await get_setting("character_cap", str(default_cap))
            try:
                cap = int(cap_str)
            except Exception:
                cap = default_cap

            # Source names from adaptation first
            raw = []
            adapt_chars = (adaptation.get('key_characters_to_preserve') or '').strip()
            if adapt_chars:
                raw = [c.strip() for c in adapt_chars.split(',') if c.strip()]

            # Build corpus from chapters original text
            corpus = "\n".join([c.get('original_chapter_text') or '' for c in chapters])

            # If no raw names, try to infer via simple extractor on corpus
            if not raw and corpus:
                # Use existing text_processing lightweight extraction as fallback
                try:
                    from services.text_processing import TextProcessor
                    tp = TextProcessor()
                    inferred = tp.extract_character_names(corpus, min_mentions=2)
                    raw = inferred or []
                except Exception:
                    raw = []

            curated = CharacterAnalyzer.curate_names(raw, corpus, cap=cap)
            log.info("curate_for_adaptation_done", extra={"component":"services.character_analyzer","cap":cap,"raw":len(raw),"curated":len(curated)})
            return curated
        except Exception as e:
            log.error("curate_for_adaptation_error", extra={"component":"services.character_analyzer","error":str(e)})
            return []