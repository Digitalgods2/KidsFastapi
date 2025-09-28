import re

def roman_to_int(s):
    """Convert Roman numeral to integer"""
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i in range(len(s)):
        if i > 0 and roman_map[s[i]] > roman_map[s[i - 1]]:
            result += roman_map[s[i]] - 2 * roman_map[s[i - 1]]
        else:
            result += roman_map[s[i]]
    return result

class TransformationService:
    def detect_chapters_in_text(self, text):
        """
        Detect chapters using table of contents approach with fallbacks.
        """
        # Primary method: TOC-based detection
        toc_chapters = self.parse_table_of_contents_for_app(text)

        if toc_chapters:
            located_chapters = self.locate_chapters_from_toc_for_app(text, toc_chapters)
            if located_chapters:
                # expose for logging who called us last
                self.last_method = 'toc'
                return located_chapters

        # Fallback 1: Enhanced direct pattern matching
        direct_chapters = self.detect_chapters_direct_pattern_for_app(text)
        if direct_chapters:
            self.last_method = 'regex'
            return direct_chapters

        # If all methods fail, return empty list
        self.last_method = None
        return []

    def parse_table_of_contents_for_app(self, text):
        """Parse table of contents to extract chapter information."""
        lines = text.split('\n')
        toc_start = self.find_toc_start_for_app(lines)

        if toc_start == -1:
            return []

        chapters = []
        toc_end = min(toc_start + 50, len(lines))

        for i in range(toc_start, toc_end):
            if i >= len(lines):
                break

            line = lines[i].strip()

            if not line or len(line) < 5:
                continue

            toc_patterns = [
                (r'^\s*Chapter\s+([IVXLCDM]+)\.?\s+(.+)$', 'roman'),
                (r'^\s*Chapter\s+(\d+)\.?\s+(.+)$', 'numeric'),
                (r'^\s+Chapter\s+([IVXLCDM]+)\.?\s+(.+)$', 'roman'),
                (r'^\s+Chapter\s+(\d+)\.?\s+(.+)$', 'numeric')
            ]

            for pattern, format_type in toc_patterns:
                match = re.match(pattern, line, re.IGNORECASE)

                if match:
                    identifier = match.group(1)
                    title = match.group(2).strip()

                    title = self.clean_toc_title_for_app(title)

                    if format_type == 'roman' and self.is_valid_roman_numeral_for_app(identifier):
                        chapter_number = roman_to_int(identifier)
                        chapters.append({
                            'number': chapter_number,
                            'roman': identifier,
                            'title': title,
                            'format': 'roman'
                        })
                        break
                    elif format_type == 'numeric':
                        chapter_number = int(identifier)
                        chapters.append({
                            'number': chapter_number,
                            'roman': None,
                            'title': title,
                            'format': 'numeric'
                        })
                        break

        chapters = sorted(chapters, key=lambda x: x['number'])
        return chapters

    def find_toc_start_for_app(self, lines):
        """Find the start of the table of contents."""
        toc_indicators = [
            r'^\s*Contents?\s*$',
            r'^\s*Table\s+of\s+Contents?\s*$',
            r'^\s*INDEX\s*$'
        ]

        for i in range(min(300, len(lines))):
            line = lines[i].strip()

            for indicator in toc_indicators:
                if re.match(indicator, line, re.IGNORECASE):
                    return i + 1

        return -1

    def clean_toc_title_for_app(self, title):
        """Clean up TOC title by removing page numbers and formatting."""
        title = re.sub(r'\s+\d+\s*$', '', title)
        title = re.sub(r'\s+\.\s*\d+\s*$', '', title)
        title = re.sub(r'\s+\.+\s*\d*\s*$', '', title)
        title = re.sub(r'\.+$', '', title)
        return title.strip()

    def is_valid_roman_numeral_for_app(self, s):
        """Check if string is a valid Roman numeral."""
        pattern = r'^[IVXLCDM]+$'
        return bool(re.match(pattern, s.upper()))

    def locate_chapters_from_toc_for_app(self, text, toc_chapters):
        """Locate actual chapters in text using TOC information."""
        lines = text.split('\n')
        located_chapters = []

        for toc_chapter in toc_chapters:
            chapter_start = self.find_chapter_location_for_app(lines, toc_chapter)

            if chapter_start != -1:
                chapter_info = toc_chapter.copy()
                chapter_info['line_start'] = chapter_start
                located_chapters.append(chapter_info)

        if located_chapters:
            self.add_content_to_toc_chapters_for_app(located_chapters, lines)

        return located_chapters

    def find_chapter_location_for_app(self, lines, toc_chapter):
        """Find where the chapter actually starts in the text."""
        start_search = 50

        if toc_chapter['format'] == 'roman':
            patterns = [
                '^Chapter\\s+{}$'.format(toc_chapter['roman']),
                '^\\s*Chapter\\s+{}.*$'.format(toc_chapter['roman'])
            ]
        else:
            patterns = [
                '^Chapter\\s+{}$'.format(toc_chapter['number']),
                '^\\s*Chapter\\s+{}.*$'.format(toc_chapter['number'])
            ]

        for i in range(start_search, len(lines)):
            line = lines[i].strip()

            for pattern in patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    return i

        title = toc_chapter['title']
        for i in range(start_search, len(lines)):
            line = lines[i].strip()

            if self.title_similarity_for_app(line, title) > 0.8:
                return i

        return -1

    def title_similarity_for_app(self, line, title):
        """Calculate similarity between line and title."""
        line_clean = re.sub(r'[^\w\s]', '', line.lower())
        title_clean = re.sub(r'[^\w\s]', '', title.lower())

        line_words = set(line_clean.split())
        title_words = set(title_clean.split())

        if not title_words:
            return 0.0

        intersection = line_words.intersection(title_words)
        union = line_words.union(title_words)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def add_content_to_toc_chapters_for_app(self, chapters, lines):
        """Add content to TOC-located chapters."""
        for i, chapter in enumerate(chapters):
            chapter_start = chapter['line_start']

            content_start = chapter_start + 1
            while content_start < len(lines):
                line = lines[content_start].strip()

                if not line:
                    content_start += 1
                    continue

                if self.title_similarity_for_app(line, chapter['title']) > 0.7:
                    content_start += 1
                    continue

                if re.match(r'^Chapter\s+[IVXLCDM\d]+', line, re.IGNORECASE):
                    content_start += 1
                    continue

                break

            if i < len(chapters) - 1:
                content_end = chapters[i + 1]['line_start']
            else:
                content_end = self.find_last_chapter_end_for_app(lines, chapter_start)

            content_lines = lines[content_start:content_end]

            while content_lines and not content_lines[0].strip():
                content_lines.pop(0)
            while content_lines and not content_lines[-1].strip():
                content_lines.pop()

            content = '\n'.join(content_lines)

            chapter['content'] = content
            chapter['start_pos'] = sum(len(lines[j]) + 1 for j in range(content_start))

            if 'line_start' in chapter:
                del chapter['line_start']

    def find_last_chapter_end_for_app(self, lines, chapter_start):
        """Find the proper ending point for the last chapter, excluding appendices and metadata."""
        search_start = chapter_start + 10
        max_search = min(len(lines), chapter_start + 2000)

        ending_indicators = [
            r'^\s*THE\s+END\s*$',
            r'^\s*End of the Project Gutenberg EBook',
            r'^\s*\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK'
        ]

        for i in range(search_start, len(lines)):
            line = lines[i].strip()
            for indicator in ending_indicators:
                if re.match(indicator, line, re.IGNORECASE):
                    return i

        return len(lines)

    def detect_chapters_direct_pattern_for_app(self, text):
        """Fallback to direct pattern matching if TOC fails."""
        lines = text.split('\n')
        chapters = []
        chapter_starts = []

        chapter_patterns = [
            r'^\s*Chapter\s+([IVXLCDM]+)',
            r'^\s*Chapter\s+(\d+)',
            r'^\s*CHAPTER\s+([IVXLCDM]+)',
            r'^\s*CHAPTER\s+(\d+)',
        ]

        for i, line in enumerate(lines):
            for pattern in chapter_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    chapter_starts.append(i)
                    break

        if not chapter_starts:
            return []

        for j in range(len(chapter_starts)):
            start = chapter_starts[j]
            end = chapter_starts[j + 1] if j < len(chapter_starts) - 1 else len(lines)
            content = '\n'.join(lines[start:end])
            chapters.append({'number': j + 1, 'content': content, 'title': f'Chapter {j+1}'})

        return chapters

