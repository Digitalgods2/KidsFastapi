"""
Chapter Structure Analysis Service for KidsKlassiks
Based on the working Streamlit implementation
"""

import re
from typing import List, Dict, Optional, Tuple

class ChapterAnalyzer:
    def __init__(self):
        """Initialize the chapter analyzer"""
        pass
    
    def detect_original_chapters(self, text: str) -> Optional[List[str]]:
        """
        Detect original chapter divisions using TOC-based approach with fallbacks.
        Returns a list of chapter texts if chapters are found, None otherwise.
        """
        chapters = self.detect_chapters_in_text(text)
        if chapters:
            return [chapter['content'] for chapter in chapters]
        return None
    
    def detect_chapters_in_text(self, text: str) -> List[Dict]:
        """
        Detect chapters using table of contents approach with fallbacks.
        
        This is the most robust method that:
        1. First tries to parse the table of contents to understand chapter structure
        2. Uses TOC information to locate actual chapters in the text
        3. Falls back to direct pattern matching if TOC approach fails
        
        Args:
            text (str): The full text of the book
            
        Returns:
            List[Dict]: List of chapter dictionaries with keys:
                - 'number': Chapter number (1, 2, 3, etc.)
                - 'roman': Roman numeral (I, II, III, etc.) or None if regular numbers
                - 'title': Chapter title from TOC
                - 'start_pos': Starting position in text
                - 'content': Chapter content
                - 'format': 'roman' or 'numeric'
        """
        # Primary method: TOC-based detection
        toc_chapters = self.parse_table_of_contents(text)
        
        if toc_chapters:
            located_chapters = self.locate_chapters_from_toc(text, toc_chapters)
            if located_chapters:
                return located_chapters
        
        # Fallback 1: Enhanced direct pattern matching
        direct_chapters = self.detect_chapters_direct_pattern(text)
        if direct_chapters:
            return direct_chapters
        
        # If all methods fail, return empty list
        return []
    
    def parse_table_of_contents(self, text: str) -> List[Dict]:
        """Parse table of contents to extract chapter information."""
        
        lines = text.split('\n')
        toc_start = self.find_toc_start(lines)
        
        if toc_start == -1:
            return []
        
        chapters = []
        toc_end = min(toc_start + 50, len(lines))
        
        for i in range(toc_start, toc_end):
            if i >= len(lines):
                break
                
            line = lines[i].strip()
            if not line:
                continue
            
            # Try to match chapter patterns in TOC
            chapter_match = self.match_toc_chapter_pattern(line)
            if chapter_match:
                chapters.append(chapter_match)
        
        return chapters
    
    def find_toc_start(self, lines: List[str]) -> int:
        """Find the start of table of contents"""
        toc_indicators = [
            'table of contents', 'contents', 'chapter', 'chapters'
        ]
        
        for i, line in enumerate(lines[:200]):  # Check first 200 lines
            line_lower = line.lower().strip()
            if any(indicator in line_lower for indicator in toc_indicators):
                if 'chapter' in line_lower or len(line_lower) < 30:
                    return i
        
        return -1
    
    def match_toc_chapter_pattern(self, line: str) -> Optional[Dict]:
        """Match various chapter patterns in table of contents"""
        
        # Roman numeral patterns
        roman_patterns = [
            r'^(I{1,3}|IV|V|VI{0,3}|IX|X{1,3}|XL|L|LX{0,3}|XC|C{1,3})\.\s*(.+)',
            r'^Chapter\s+(I{1,3}|IV|V|VI{0,3}|IX|X{1,3}|XL|L|LX{0,3}|XC|C{1,3})\s*[.\-:]\s*(.+)',
            r'^(I{1,3}|IV|V|VI{0,3}|IX|X{1,3}|XL|L|LX{0,3}|XC|C{1,3})\s+(.+)'
        ]
        
        for pattern in roman_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return {
                    'format': 'roman',
                    'roman': match.group(1),
                    'number': self.roman_to_int(match.group(1)),
                    'title': match.group(2).strip(),
                    'original_line': line
                }
        
        # Numeric patterns
        numeric_patterns = [
            r'^(\d+)\.\s*(.+)',
            r'^Chapter\s+(\d+)\s*[.\-:]\s*(.+)',
            r'^(\d+)\s+(.+)'
        ]
        
        for pattern in numeric_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return {
                    'format': 'numeric',
                    'roman': None,
                    'number': int(match.group(1)),
                    'title': match.group(2).strip(),
                    'original_line': line
                }
        
        return None
    
    def roman_to_int(self, roman: str) -> int:
        """Convert roman numeral to integer"""
        roman_values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000
        }
        
        total = 0
        prev_value = 0
        
        for char in reversed(roman.upper()):
            value = roman_values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        
        return total
    
    def locate_chapters_from_toc(self, text: str, toc_chapters: List[Dict]) -> List[Dict]:
        """Locate actual chapters in text based on TOC information"""
        
        lines = text.split('\n')
        located_chapters = []
        
        for chapter in toc_chapters:
            location = self.find_chapter_location(lines, chapter)
            if location is not None:
                chapter['start_pos'] = location
                located_chapters.append(chapter)
        
        # Add content to chapters
        if located_chapters:
            return self.add_content_to_chapters(located_chapters, lines)
        
        return []
    
    def find_chapter_location(self, lines: List[str], toc_chapter: Dict) -> Optional[int]:
        """Find the location of a chapter in the text"""
        
        chapter_num = toc_chapter['number']
        chapter_format = toc_chapter['format']
        
        # Create search patterns
        if chapter_format == 'roman':
            roman = toc_chapter['roman']
            patterns = [
                rf'^Chapter\s+{roman}\b',
                rf'^{roman}\.\s',
                rf'^{roman}\s+[A-Z]'
            ]
        else:
            patterns = [
                rf'^Chapter\s+{chapter_num}\b',
                rf'^{chapter_num}\.\s',
                rf'^{chapter_num}\s+[A-Z]'
            ]
        
        # Search for chapter in text
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            for pattern in patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    return i
        
        return None
    
    def add_content_to_chapters(self, chapters: List[Dict], lines: List[str]) -> List[Dict]:
        """Add content to located chapters"""
        
        for i, chapter in enumerate(chapters):
            start_line = chapter['start_pos']
            
            # Find end of chapter (start of next chapter or end of text)
            if i + 1 < len(chapters):
                end_line = chapters[i + 1]['start_pos']
            else:
                end_line = len(lines)
            
            # Extract chapter content
            chapter_lines = lines[start_line:end_line]
            chapter['content'] = '\n'.join(chapter_lines).strip()
        
        return chapters
    
    def detect_chapters_direct_pattern(self, text: str) -> List[Dict]:
        """Direct pattern matching for chapter detection"""
        
        # Try roman numerals first
        roman_chapters = self.detect_roman_chapters(text)
        if roman_chapters:
            return roman_chapters
        
        # Try numeric chapters
        numeric_chapters = self.detect_numeric_chapters(text)
        if numeric_chapters:
            return numeric_chapters
        
        return []
    
    def detect_roman_chapters(self, text: str) -> List[Dict]:
        """Detect chapters with roman numerals"""
        
        lines = text.split('\n')
        chapters = []
        
        # Roman numeral pattern
        pattern = r'^(Chapter\s+)?(I{1,3}|IV|V|VI{0,3}|IX|X{1,3}|XL|L|LX{0,3}|XC|C{1,3})(\.|:|\s|$)'
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            match = re.match(pattern, line_stripped, re.IGNORECASE)
            if match:
                roman = match.group(2)
                chapters.append({
                    'format': 'roman',
                    'roman': roman,
                    'number': self.roman_to_int(roman),
                    'title': f"Chapter {roman}",
                    'start_pos': i,
                    'original_line': line_stripped
                })
        
        # Add content if chapters found
        if chapters:
            return self.add_content_to_chapters(chapters, lines)
        
        return []
    
    def detect_numeric_chapters(self, text: str) -> List[Dict]:
        """Detect chapters with numeric patterns"""
        
        lines = text.split('\n')
        chapters = []
        
        # Numeric pattern
        pattern = r'^(Chapter\s+)?(\d+)(\.|:|\s|$)'
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            match = re.match(pattern, line_stripped, re.IGNORECASE)
            if match:
                number = int(match.group(2))
                chapters.append({
                    'format': 'numeric',
                    'roman': None,
                    'number': number,
                    'title': f"Chapter {number}",
                    'start_pos': i,
                    'original_line': line_stripped
                })
        
        # Add content if chapters found
        if chapters:
            return self.add_content_to_chapters(chapters, lines)
        
        return []
    
    def segment_text_into_chapters(self, full_text: str, words_per_chapter_approx: int = 2000) -> List[str]:
        """
        Segment text into age-appropriate chapters by word count
        
        Args:
            full_text: The complete book text
            words_per_chapter_approx: Target words per chapter
            
        Returns:
            List of chapter content strings
        """
        if not full_text or not isinstance(full_text, str):
            return []
        
        words = full_text.split()
        if not words:
            return []
        
        # Calculate number of chapters
        num_chapters = max(1, len(words) // words_per_chapter_approx)
        
        # Add extra chapter if remainder is significant
        if len(words) % words_per_chapter_approx > words_per_chapter_approx / 2 and num_chapters > 0:
            num_chapters += 1
        
        num_chapters = max(1, num_chapters)
        words_in_each_chapter = len(words) // num_chapters
        
        chapters = []
        start_index = 0
        
        for i in range(num_chapters):
            # Last chapter gets all remaining words
            end_index = len(words) if i == num_chapters - 1 else start_index + words_in_each_chapter
            
            chapter_content = " ".join(words[start_index:end_index])
            chapters.append(chapter_content)
            start_index = end_index
        
        # Ensure we have at least one chapter
        if not chapters and words:
            chapters.append(" ".join(words))
        
        return chapters
    
    def analyze_chapter_structure(self, text: str) -> Dict:
        """
        Analyze the chapter structure of a text and provide recommendations
        
        Args:
            text: The book text to analyze
            
        Returns:
            Dictionary with analysis results and recommendations
        """
        detected_chapters = self.detect_chapters_in_text(text)
        
        analysis = {
            'has_original_chapters': len(detected_chapters) > 0,
            'chapter_count': len(detected_chapters),
            'chapter_format': None,
            'average_chapter_length': 0,
            'recommendation': 'auto_segment',
            'detected_chapters': detected_chapters
        }
        
        if detected_chapters:
            # Determine format
            formats = [ch.get('format', 'unknown') for ch in detected_chapters]
            analysis['chapter_format'] = max(set(formats), key=formats.count)
            
            # Calculate average length
            chapter_lengths = [len(ch.get('content', '').split()) for ch in detected_chapters]
            if chapter_lengths:
                analysis['average_chapter_length'] = sum(chapter_lengths) / len(chapter_lengths)
            
            # Make recommendation
            if analysis['chapter_count'] >= 3 and analysis['average_chapter_length'] > 500:
                analysis['recommendation'] = 'keep_original'
            else:
                analysis['recommendation'] = 'auto_segment'
        
        return analysis
