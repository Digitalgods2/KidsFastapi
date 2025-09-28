"""
Text processing service for KidsKlassiks FastAPI application
Handles chapter detection, text segmentation, and content processing
"""

import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
import requests
from urllib.parse import urlparse
from models import AgeGroup, ChapterStructure

class TextProcessor:
    """Service class for text processing operations"""
    
    def __init__(self):
        """Initialize text processor"""
        pass
    
    # ==================== CHAPTER DETECTION AND SEGMENTATION ====================
    
    def segment_text_into_chapters(
        self, 
        text: str, 
        target_age_group: AgeGroup,
        chapter_structure: ChapterStructure = ChapterStructure.AUTO
    ) -> List[str]:
        """
        Segment text into chapters based on the target age group and structure preference
        """
        if chapter_structure == ChapterStructure.ORIGINAL:
            return self._detect_original_chapters(text)
        elif chapter_structure == ChapterStructure.AUTO:
            return self._auto_segment_by_age(text, target_age_group)
        else:
            # Custom segmentation would be handled separately
            return self._auto_segment_by_age(text, target_age_group)
    
    def _detect_original_chapters(self, text: str) -> List[str]:
        """Detect original chapter breaks in the text"""
        # Common chapter patterns
        chapter_patterns = [
            r'\n\s*Chapter\s+\d+[^\n]*\n',
            r'\n\s*CHAPTER\s+\d+[^\n]*\n',
            r'\n\s*Chapter\s+[IVXLCDM]+[^\n]*\n',
            r'\n\s*CHAPTER\s+[IVXLCDM]+[^\n]*\n',
            r'\n\s*\d+\.\s*[^\n]*\n',
            r'\n\s*[IVXLCDM]+\.\s*[^\n]*\n'
        ]
        
        # Try each pattern
        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if len(matches) >= 2:  # Need at least 2 chapters
                chapters = []
                
                for i, match in enumerate(matches):
                    start = match.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    
                    chapter_text = text[start:end].strip()
                    if len(chapter_text) > 100:  # Minimum chapter length
                        chapters.append(chapter_text)
                
                if len(chapters) >= 2:
                    return chapters
        
        # If no clear chapters found, split by length
        return self._split_by_length(text, 2000)
    
    def _auto_segment_by_age(self, text: str, age_group: AgeGroup) -> List[str]:
        """Automatically segment text based on age-appropriate chapter lengths"""
        # Age-appropriate chapter lengths (in words)
        target_lengths = {
            AgeGroup.AGES_3_5: 150,   # Very short chapters
            AgeGroup.AGES_6_8: 400,   # Short chapters
            AgeGroup.AGES_9_12: 800   # Medium chapters
        }
        
        target_words = target_lengths.get(age_group, 400)
        
        # First try to detect natural breaks
        chapters = self._segment_by_natural_breaks(text, target_words)
        
        # If that doesn't work well, fall back to length-based splitting
        if len(chapters) < 2 or any(len(ch.split()) < target_words // 3 for ch in chapters):
            chapters = self._split_by_length(text, target_words * 6)  # Convert words to approximate characters
        
        return chapters
    
    def _segment_by_natural_breaks(self, text: str, target_words: int) -> List[str]:
        """Segment text by natural breaks (paragraphs, scenes)"""
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chapters = []
        current_chapter = []
        current_word_count = 0
        
        for paragraph in paragraphs:
            paragraph_words = len(paragraph.split())
            
            # If adding this paragraph would exceed target, start new chapter
            if current_word_count > 0 and current_word_count + paragraph_words > target_words * 1.5:
                if current_chapter:
                    chapters.append('\n\n'.join(current_chapter))
                    current_chapter = [paragraph]
                    current_word_count = paragraph_words
            else:
                current_chapter.append(paragraph)
                current_word_count += paragraph_words
        
        # Add the last chapter
        if current_chapter:
            chapters.append('\n\n'.join(current_chapter))
        
        return chapters
    
    def _split_by_length(self, text: str, target_length: int) -> List[str]:
        """Split text into chunks of approximately target length"""
        words = text.split()
        chapters = []
        current_chapter = []
        current_length = 0
        
        for word in words:
            current_chapter.append(word)
            current_length += len(word) + 1  # +1 for space
            
            if current_length >= target_length:
                chapters.append(' '.join(current_chapter))
                current_chapter = []
                current_length = 0
        
        # Add remaining words
        if current_chapter:
            chapters.append(' '.join(current_chapter))
        
        return chapters
    
    # ==================== CONTENT ANALYSIS ====================
    
    def analyze_text_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze text complexity metrics"""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Basic metrics
        word_count = len(words)
        sentence_count = len(sentences)
        avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
        
        # Syllable estimation (rough)
        syllable_count = sum(self._estimate_syllables(word) for word in words)
        avg_syllables_per_word = syllable_count / word_count if word_count > 0 else 0
        
        # Reading level estimation (Flesch-Kincaid approximation)
        if sentence_count > 0 and word_count > 0:
            flesch_kincaid = 0.39 * avg_words_per_sentence + 11.8 * avg_syllables_per_word - 15.59
        else:
            flesch_kincaid = 0
        
        return {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_words_per_sentence': round(avg_words_per_sentence, 2),
            'avg_syllables_per_word': round(avg_syllables_per_word, 2),
            'estimated_reading_level': max(1, round(flesch_kincaid, 1)),
            'complexity_score': self._calculate_complexity_score(avg_words_per_sentence, avg_syllables_per_word)
        }
    
    def _estimate_syllables(self, word: str) -> int:
        """Rough syllable estimation"""
        word = word.lower().strip('.,!?;:"')
        if not word:
            return 0
        
        # Count vowel groups
        vowels = 'aeiouy'
        syllable_count = 0
        prev_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel
        
        # Handle silent e
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1
        
        return max(1, syllable_count)
    
    def _calculate_complexity_score(self, avg_words_per_sentence: float, avg_syllables_per_word: float) -> str:
        """Calculate overall complexity score"""
        if avg_words_per_sentence < 8 and avg_syllables_per_word < 1.3:
            return "Very Simple"
        elif avg_words_per_sentence < 12 and avg_syllables_per_word < 1.5:
            return "Simple"
        elif avg_words_per_sentence < 16 and avg_syllables_per_word < 1.7:
            return "Moderate"
        elif avg_words_per_sentence < 20 and avg_syllables_per_word < 2.0:
            return "Complex"
        else:
            return "Very Complex"
    
    # ==================== CHARACTER EXTRACTION ====================
    
    def extract_character_names(self, text: str, min_mentions: int = 3) -> List[str]:
        """Extract character names from text based on frequency"""
        # Common patterns for names
        name_patterns = [
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',  # Capitalized words
            r'\b(?:Mr|Mrs|Miss|Dr|Professor|Captain|Sir|Lady)\s+[A-Z][a-z]+\b'  # Titles + names
        ]
        
        potential_names = []
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            potential_names.extend(matches)
        
        # Count occurrences
        name_counts = Counter(potential_names)
        
        # Filter out common words and keep only frequently mentioned names
        common_words = {
            'The', 'And', 'But', 'For', 'Not', 'With', 'This', 'That', 'They', 'Were', 'Been',
            'Have', 'Their', 'Said', 'Each', 'Which', 'She', 'Do', 'How', 'If', 'Will', 'Up',
            'Other', 'About', 'Out', 'Many', 'Then', 'Them', 'These', 'So', 'Some', 'Her',
            'Would', 'Make', 'Like', 'Into', 'Him', 'Has', 'Two', 'More', 'Very', 'What',
            'Know', 'Just', 'First', 'Get', 'Over', 'Think', 'Also', 'Your', 'Work', 'Life',
            'Only', 'New', 'Years', 'Way', 'May', 'Say', 'Come', 'Its', 'Now', 'Most', 'Such'
        }
        
        characters = []
        for name, count in name_counts.most_common():
            if count >= min_mentions and name not in common_words and len(name) > 2:
                characters.append(name)
        
        return characters[:10]  # Return top 10 characters
    
    # ==================== URL FETCHING ====================
    
    async def fetch_text_from_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetch text content from a URL"""
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None, "Invalid URL format"
            
            # Special handling for Project Gutenberg
            if 'gutenberg.org' in parsed.netloc:
                return await self._fetch_gutenberg_text(url)
            
            # General URL fetching
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Try to decode content
            content = response.text
            
            # Basic text extraction (you might want to use BeautifulSoup for HTML)
            if 'text/html' in response.headers.get('content-type', ''):
                content = self._extract_text_from_html(content)
            
            return content, None
            
        except requests.RequestException as e:
            return None, f"Error fetching URL: {e}"
        except Exception as e:
            return None, f"Error processing content: {e}"
    
    async def _fetch_gutenberg_text(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fetch text from Project Gutenberg with special handling"""
        try:
            # Convert to plain text URL if needed
            if '/ebooks/' in url and not url.endswith('.txt'):
                # Extract book ID and construct plain text URL
                book_id = re.search(r'/ebooks/(\d+)', url)
                if book_id:
                    plain_text_url = f"https://www.gutenberg.org/files/{book_id.group(1)}/{book_id.group(1)}-0.txt"
                    response = requests.get(plain_text_url, timeout=30)
                    if response.status_code == 200:
                        return self._clean_gutenberg_text(response.text), None
            
            # Fallback to original URL
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            content = response.text
            if 'text/html' in response.headers.get('content-type', ''):
                content = self._extract_text_from_html(content)
            
            return self._clean_gutenberg_text(content), None
            
        except Exception as e:
            return None, f"Error fetching Gutenberg text: {e}"
    
    def _clean_gutenberg_text(self, text: str) -> str:
        """Clean Project Gutenberg text by removing headers and footers"""
        lines = text.split('\n')
        
        # Find start of actual content
        start_idx = 0
        for i, line in enumerate(lines):
            if '*** START OF' in line.upper() or 'START OF THE PROJECT GUTENBERG' in line.upper():
                start_idx = i + 1
                break
        
        # Find end of actual content
        end_idx = len(lines)
        for i, line in enumerate(lines[start_idx:], start_idx):
            if '*** END OF' in line.upper() or 'END OF THE PROJECT GUTENBERG' in line.upper():
                end_idx = i
                break
        
        # Extract main content
        content_lines = lines[start_idx:end_idx]
        
        # Remove empty lines at start and end
        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        
        return '\n'.join(content_lines)
    
    def _extract_text_from_html(self, html: str) -> str:
        """Basic HTML text extraction"""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    # ==================== CONTENT VALIDATION ====================
    
    def validate_text_content(self, text: str) -> Tuple[bool, Optional[str]]:
        """Validate text content for processing"""
        if not text or not text.strip():
            return False, "Text is empty"
        
        word_count = len(text.split())
        if word_count < 100:
            return False, "Text is too short (minimum 100 words)"
        
        if word_count > 500000:
            return False, "Text is too long (maximum 500,000 words)"
        
        # Check for reasonable text structure
        sentence_count = len(re.split(r'[.!?]+', text))
        if sentence_count < 5:
            return False, "Text appears to lack proper sentence structure"
        
        return True, None
    
    def estimate_processing_time(self, text: str, target_age_group: AgeGroup) -> Dict[str, int]:
        """Estimate processing time for text transformation"""
        word_count = len(text.split())
        
        # Base processing times (in seconds)
        base_times = {
            'character_analysis': max(30, word_count // 1000 * 10),
            'segmentation': max(5, word_count // 5000),
            'transformation': max(60, word_count // 500 * 15),
            'image_generation': 0  # Will be calculated based on chapters
        }
        
        # Estimate chapters
        target_lengths = {
            AgeGroup.AGES_3_5: 150,
            AgeGroup.AGES_6_8: 400,
            AgeGroup.AGES_9_12: 800
        }
        
        target_words = target_lengths.get(target_age_group, 400)
        estimated_chapters = max(1, word_count // target_words)
        
        # Image generation time (30 seconds per image)
        base_times['image_generation'] = estimated_chapters * 30
        
        # Total time
        base_times['total'] = sum(base_times.values())
        base_times['estimated_chapters'] = estimated_chapters
        
        return base_times
