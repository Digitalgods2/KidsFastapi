"""
Project Gutenberg Text Cleaner
Removes legal boilerplate from the beginning and end of Project Gutenberg texts
"""

import re
from typing import Tuple
from services.logger import get_logger

logger = get_logger("services.gutenberg_cleaner")


def clean_gutenberg_text(text: str) -> Tuple[str, bool]:
    """
    Remove Project Gutenberg legal boilerplate from beginning and end of text.
    
    Project Gutenberg books typically have:
    - START: Legal notice ending with "*** START OF THE PROJECT GUTENBERG EBOOK [TITLE] ***"
    - END: Legal notice starting with "*** END OF THE PROJECT GUTENBERG EBOOK [TITLE] ***"
    
    Args:
        text: The raw text from Project Gutenberg
        
    Returns:
        Tuple of (cleaned_text, was_gutenberg_text)
        - cleaned_text: Text with legal boilerplate removed
        - was_gutenberg_text: True if Project Gutenberg markers were found
    """
    
    if not text or len(text) < 500:
        return text, False
    
    original_length = len(text)
    was_gutenberg = False
    
    # Common Project Gutenberg start markers (case-insensitive, flexible spacing)
    start_patterns = [
        r'\*\*\*\s*START\s+OF\s+(?:THIS|THE)\s+PROJECT\s+GUTENBERG\s+EBOOK\s+[^\*]+\*\*\*',
        r'\*\*\*\s*START\s+OF\s+THE\s+PROJECT\s+GUTENBERG\s+EBOOK[^\*]*\*\*\*',
        r'START\s+OF\s+(?:THIS|THE)\s+PROJECT\s+GUTENBERG\s+EBOOK',
    ]
    
    # Common Project Gutenberg end markers
    end_patterns = [
        r'\*\*\*\s*END\s+OF\s+(?:THIS|THE)\s+PROJECT\s+GUTENBERG\s+EBOOK\s+[^\*]+\*\*\*',
        r'\*\*\*\s*END\s+OF\s+THE\s+PROJECT\s+GUTENBERG\s+EBOOK[^\*]*\*\*\*',
        r'END\s+OF\s+(?:THIS|THE)\s+PROJECT\s+GUTENBERG\s+EBOOK',
    ]
    
    cleaned_text = text
    
    # Find and remove beginning boilerplate
    start_pos = None
    for pattern in start_patterns:
        match = re.search(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Find the end of the line after the marker
            line_end = cleaned_text.find('\n', match.end())
            if line_end != -1:
                start_pos = line_end + 1
                was_gutenberg = True
                logger.info("gutenberg_start_marker_found", extra={
                    "component": "services.gutenberg_cleaner",
                    "pattern": pattern[:50],
                    "removed_chars": start_pos
                })
                break
    
    if start_pos:
        cleaned_text = cleaned_text[start_pos:].lstrip()
    
    # Find and remove ending boilerplate
    end_pos = None
    for pattern in end_patterns:
        # Search from the last 50KB of text (boilerplate is usually at the very end)
        search_start = max(0, len(cleaned_text) - 50000)
        search_text = cleaned_text[search_start:]
        
        match = re.search(pattern, search_text, re.IGNORECASE | re.MULTILINE)
        if match:
            # Find the beginning of the line with the marker
            line_start = search_text.rfind('\n', 0, match.start())
            if line_start != -1:
                end_pos = search_start + line_start
            else:
                end_pos = search_start + match.start()
            was_gutenberg = True
            logger.info("gutenberg_end_marker_found", extra={
                "component": "services.gutenberg_cleaner",
                "pattern": pattern[:50],
                "removed_chars": len(cleaned_text) - end_pos
            })
            break
    
    if end_pos:
        cleaned_text = cleaned_text[:end_pos].rstrip()
    
    # Additional cleanup: Remove any remaining "Transcriber's Note" sections
    # These often appear at the beginning after the legal notice
    transcriber_patterns = [
        r'(?:^|\n)\s*(?:Transcriber\'?s?\s+Note|TRANSCRIBER\'?S?\s+NOTE)[^\n]*\n(?:[^\n]+\n){0,20}?\n',
        r'(?:^|\n)\s*\[Transcriber\'?s?\s+Note:?[^\]]*\][^\n]*\n',
    ]
    
    for pattern in transcriber_patterns:
        match = re.search(pattern, cleaned_text[:5000], re.IGNORECASE | re.MULTILINE)
        if match:
            # Only remove if it's in the first 5000 characters
            cleaned_text = cleaned_text[:match.start()] + cleaned_text[match.end():]
            logger.info("transcriber_note_removed", extra={
                "component": "services.gutenberg_cleaner",
                "removed_chars": match.end() - match.start()
            })
            break
    
    # Final cleanup: remove excessive blank lines at start/end
    cleaned_text = cleaned_text.strip()
    
    # Remove multiple consecutive blank lines (more than 2)
    cleaned_text = re.sub(r'\n{4,}', '\n\n\n', cleaned_text)
    
    if was_gutenberg:
        removed_chars = original_length - len(cleaned_text)
        removed_percent = (removed_chars / original_length) * 100
        logger.info("gutenberg_cleaning_complete", extra={
            "component": "services.gutenberg_cleaner",
            "original_length": original_length,
            "cleaned_length": len(cleaned_text),
            "removed_chars": removed_chars,
            "removed_percent": f"{removed_percent:.1f}%"
        })
    
    return cleaned_text, was_gutenberg


def is_gutenberg_url(url: str) -> bool:
    """
    Check if a URL is from Project Gutenberg.
    
    Args:
        url: URL string to check
        
    Returns:
        True if the URL is from Project Gutenberg
    """
    gutenberg_domains = [
        'gutenberg.org',
        'gutenberg.net',
        'gutenberg.ca',
        'gutenbergproject.org',
    ]
    
    url_lower = url.lower()
    return any(domain in url_lower for domain in gutenberg_domains)


def is_likely_gutenberg_text(text: str) -> bool:
    """
    Check if text appears to be from Project Gutenberg based on content.
    
    Args:
        text: Text content to check
        
    Returns:
        True if the text likely contains Project Gutenberg boilerplate
    """
    if not text or len(text) < 100:
        return False
    
    # Check first 10KB for Gutenberg markers
    sample = text[:10000].lower()
    
    gutenberg_markers = [
        'project gutenberg',
        'gutenberg ebook',
        'gutenberg-tm',
        'gutenberg literary archive foundation',
    ]
    
    return any(marker in sample for marker in gutenberg_markers)
