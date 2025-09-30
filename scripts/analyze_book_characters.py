#!/usr/bin/env python3
"""
Analyze characters in a book and store detailed descriptions in database
This ensures consistent character appearances across all chapter images
"""
import asyncio
import sys
import json
sys.path.insert(0, '/home/user/webapp')

import database_fixed as database
from services.character_analyzer import CharacterAnalyzer


async def analyze_and_store_characters(book_id: int):
    """
    Analyze characters in a book and store detailed descriptions
    
    Args:
        book_id: The book ID to analyze
    """
    print(f"📚 Fetching book {book_id} from database...")
    
    # Get book details
    book = await database.get_book_details(book_id)
    if not book:
        print(f"❌ Book {book_id} not found")
        return False
    
    print(f"📖 Book: {book['title']} by {book.get('author', 'Unknown')}")
    
    # Read book text
    book_path = book.get('path')
    if not book_path:
        print(f"❌ No file path for book {book_id}")
        return False
    
    try:
        with open(book_path, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"✅ Loaded {len(text):,} characters from file")
    except Exception as e:
        print(f"❌ Failed to read book file: {e}")
        return False
    
    # Run character analysis with GPT-4o (large context)
    print(f"🤖 Analyzing characters with GPT-4o (this may take 30-60 seconds)...")
    analyzer = CharacterAnalyzer()
    
    result = await analyzer.analyze_characters_with_ai(
        text=text,
        book_title=book['title'],
        book_author=book.get('author', '')
    )
    
    if 'error' in result:
        print(f"❌ Character analysis failed: {result['error']}")
        if 'raw_response' in result:
            print(f"Response preview: {result['raw_response'][:500]}")
        return False
    
    if 'characters_reference' not in result:
        print(f"❌ No characters found in analysis")
        return False
    
    chars = result['characters_reference']
    print(f"✅ Found {len(chars)} characters with detailed descriptions")
    print()
    
    # Show sample characters
    print("=" * 70)
    print("CHARACTER DESCRIPTIONS (sample)")
    print("=" * 70)
    for i, (name, details) in enumerate(list(chars.items())[:5]):
        print(f"{i+1}. {name}")
        if 'physical_appearance' in details:
            desc = details['physical_appearance'].get('description', 'N/A')
            print(f"   Physical: {desc[:150]}{'...' if len(desc) > 150 else ''}")
        print()
    
    if len(chars) > 5:
        print(f"   ... and {len(chars) - 5} more characters")
        print()
    
    # Store in database
    print("💾 Storing character reference in database...")
    char_ref_json = json.dumps(result)
    
    success = await database.update_book_character_reference(book_id, char_ref_json)
    
    if success:
        print(f"✅ SUCCESS! Character reference stored for book {book_id}")
        print()
        print("=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("1. Character descriptions are now in the database")
        print("2. When you generate chapter images, these descriptions will be")
        print("   automatically included in every image prompt")
        print("3. Result: Consistent character appearances across all chapters!")
        print("=" * 70)
        return True
    else:
        print(f"❌ Failed to store character reference")
        return False


async def analyze_all_books():
    """Analyze characters for all books that don't have character_reference yet"""
    print("🔍 Finding books without character analysis...")
    
    # Get all books
    books = await database.get_all_books()
    
    books_needing_analysis = []
    for book in books:
        char_ref = book.get('character_reference')
        if not char_ref or char_ref.strip() == '':
            books_needing_analysis.append(book)
        else:
            # Check if it has the correct structure
            try:
                data = json.loads(char_ref)
                if 'characters_reference' not in data:
                    books_needing_analysis.append(book)
            except:
                books_needing_analysis.append(book)
    
    if not books_needing_analysis:
        print("✅ All books already have character analysis!")
        return
    
    print(f"📚 Found {len(books_needing_analysis)} books needing analysis:")
    for book in books_needing_analysis:
        print(f"  - Book {book['book_id']}: {book['title']}")
    print()
    
    # Analyze each book
    for i, book in enumerate(books_needing_analysis):
        print(f"\n{'=' * 70}")
        print(f"ANALYZING BOOK {i+1}/{len(books_needing_analysis)}")
        print(f"{'=' * 70}\n")
        
        success = await analyze_and_store_characters(book['book_id'])
        
        if not success:
            print(f"⚠️  Skipping book {book['book_id']} due to errors")
        
        print()
    
    print("\n" + "=" * 70)
    print("ALL BOOKS ANALYZED")
    print("=" * 70)
    print(f"✅ Successfully analyzed {len(books_needing_analysis)} books")
    print("Character consistency is now enabled for all image generation!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze book characters for image consistency')
    parser.add_argument('--book-id', type=int, help='Analyze specific book by ID')
    parser.add_argument('--all', action='store_true', help='Analyze all books without character data')
    
    args = parser.parse_args()
    
    if args.book_id:
        # Analyze specific book
        success = asyncio.run(analyze_and_store_characters(args.book_id))
        sys.exit(0 if success else 1)
    elif args.all:
        # Analyze all books
        asyncio.run(analyze_all_books())
    else:
        # Interactive mode
        print("=" * 70)
        print("CHARACTER ANALYSIS TOOL")
        print("=" * 70)
        print()
        print("Usage:")
        print("  python scripts/analyze_book_characters.py --book-id 9    # Analyze specific book")
        print("  python scripts/analyze_book_characters.py --all          # Analyze all books")
        print()
        print("This tool uses GPT-4o to analyze books and extract detailed character")
        print("descriptions for consistent image generation across all chapters.")
        print("=" * 70)
