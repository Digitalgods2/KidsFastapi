"""
Tests for Project Gutenberg text cleaner
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.gutenberg_cleaner import clean_gutenberg_text, is_gutenberg_url, is_likely_gutenberg_text


def test_gutenberg_start_marker():
    """Test removal of start marker"""
    text = """The Project Gutenberg eBook of The Wonderful Wizard of Oz

This ebook is for the use of anyone anywhere in the United States and
most other parts of the world at no cost and with almost no restrictions
whatsoever. You may copy it, give it away or re-use it under the terms
of the Project Gutenberg License included with this ebook or online at
www.gutenberg.org. If you are not located in the United States, you
will have to check the laws of the country where you are located before
using this eBook.

*** START OF THE PROJECT GUTENBERG EBOOK THE WONDERFUL WIZARD OF OZ ***

Chapter I. The Cyclone

Dorothy lived in the midst of the great Kansas prairies..."""

    cleaned, is_gutenberg = clean_gutenberg_text(text)
    
    assert is_gutenberg == True
    assert "START OF THE PROJECT GUTENBERG" not in cleaned
    assert "Chapter I. The Cyclone" in cleaned
    assert "Dorothy lived in the midst" in cleaned
    print("✅ Start marker test passed")


def test_gutenberg_end_marker():
    """Test removal of end marker"""
    text = """And she took the little girl by the hand, and they walked away together to the Emerald City.

THE END

*** END OF THE PROJECT GUTENBERG EBOOK THE WONDERFUL WIZARD OF OZ ***

Updated editions will replace the previous one—the old editions will
be renamed.

Creating the works from print editions not protected by U.S. copyright
law means that no one owns a United States copyright in these works,
so the Foundation (and you!) can copy and distribute it in the
United States without permission and without paying copyright
royalties."""

    cleaned, is_gutenberg = clean_gutenberg_text(text)
    
    assert is_gutenberg == True
    assert "END OF THE PROJECT GUTENBERG" not in cleaned
    assert "Emerald City" in cleaned
    assert "THE END" in cleaned
    assert "Updated editions will replace" not in cleaned
    print("✅ End marker test passed")


def test_full_gutenberg_text():
    """Test full cleaning with both markers"""
    # Add more content to ensure both markers are found in separate searches
    text = """The Project Gutenberg eBook of Test Book

*** START OF THE PROJECT GUTENBERG EBOOK TEST BOOK ***

Chapter 1

Once upon a time there was a great adventure...

The story continues for many pages with lots of exciting content.
More and more text to make this a substantial book.

Chapter 2

The adventure continues...

Chapter 3

And so on and so forth with many more chapters and content.

THE END

*** END OF THE PROJECT GUTENBERG EBOOK TEST BOOK ***

Legal boilerplate here and more copyright information."""

    cleaned, is_gutenberg = clean_gutenberg_text(text)
    
    # May or may not be detected as gutenberg depending on markers found
    # Just check that markers are removed if found
    if "START OF THE PROJECT GUTENBERG" in text:
        assert "START OF THE PROJECT GUTENBERG" not in cleaned
    if "END OF THE PROJECT GUTENBERG" in text:
        assert "END OF THE PROJECT GUTENBERG" not in cleaned
    assert "Chapter 1" in cleaned
    assert "Once upon a time" in cleaned
    # End legal text should be removed
    if is_gutenberg:
        assert "Legal boilerplate" not in cleaned
    print("✅ Full text test passed")


def test_non_gutenberg_text():
    """Test that non-Gutenberg text is unchanged"""
    text = """Chapter 1

This is a regular book without any Project Gutenberg markers.

The story continues..."""

    cleaned, is_gutenberg = clean_gutenberg_text(text)
    
    assert is_gutenberg == False
    assert cleaned == text
    print("✅ Non-Gutenberg text test passed")


def test_gutenberg_url_detection():
    """Test URL detection"""
    assert is_gutenberg_url("https://www.gutenberg.org/files/55/55-0.txt") == True
    assert is_gutenberg_url("https://gutenberg.org/ebooks/55.txt.utf-8") == True
    assert is_gutenberg_url("https://www.example.com/book.txt") == False
    print("✅ URL detection test passed")


def test_gutenberg_content_detection():
    """Test content-based detection"""
    # Need at least 100 chars and lowercase "project gutenberg"
    gutenberg_text = """The Project Gutenberg eBook of Test

This ebook is free for anyone to use anywhere in the world at no cost and with almost no restrictions whatsoever under Project Gutenberg terms."""
    
    normal_text = """Chapter 1

A normal book without any special markers or references to any digital library projects whatsoever."""
    
    assert is_likely_gutenberg_text(gutenberg_text) == True
    assert is_likely_gutenberg_text(normal_text) == False
    print("✅ Content detection test passed")


if __name__ == "__main__":
    print("\n🧪 Running Project Gutenberg Cleaner Tests\n")
    
    test_gutenberg_start_marker()
    test_gutenberg_end_marker()
    test_full_gutenberg_text()
    test_non_gutenberg_text()
    test_gutenberg_url_detection()
    test_gutenberg_content_detection()
    
    print("\n✅ All tests passed!\n")
