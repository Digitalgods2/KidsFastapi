#!/usr/bin/env python3
"""
Debug script for character analysis issues
Tests the OpenAI API connection and character analysis functionality
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
import openai
import database

async def test_openai_connection():
    """Test basic OpenAI API connection"""
    print("🔍 Testing OpenAI API Connection...")
    print(f"API Key configured: {bool(config.OPENAI_API_KEY)}")
    
    if not config.OPENAI_API_KEY:
        print("❌ No OpenAI API key found in environment variables")
        return False
    
    if config.OPENAI_API_KEY == "YOUR_KEY_HERE":
        print("❌ OpenAI API key is placeholder value")
        return False
    
    print(f"API Key starts with: {config.OPENAI_API_KEY[:10]}...")
    
    try:
        # Use compatible client initialization
        try:
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        except TypeError as e:
            if 'proxies' in str(e):
                # Fallback for version compatibility
                client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'API connection successful'"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI API Response: {result}")
        return True
        
    except openai.AuthenticationError as e:
        print(f"❌ Authentication Error: {e}")
        print("Check your OpenAI API key")
        return False
    except openai.RateLimitError as e:
        print(f"❌ Rate Limit Error: {e}")
        return False
    except openai.APIError as e:
        print(f"❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False

async def test_character_analysis():
    """Test character analysis with sample text"""
    print("\n🎭 Testing Character Analysis...")
    
    sample_text = """
    Peter Pan was a boy who never grew up. He lived in Neverland with the Lost Boys.
    One night, he flew into the nursery of the Darling family in London.
    There he met Wendy, John, and Michael Darling.
    Captain Hook was the pirate captain who was Peter's greatest enemy.
    Tinker Bell was Peter's fairy companion who was very jealous of Wendy.
    Mr. and Mrs. Darling were the children's parents who worried when they disappeared.
    """
    
    try:
        # Use compatible client initialization
        try:
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        except TypeError as e:
            if 'proxies' in str(e):
                # Fallback for version compatibility
                client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        prompt = f"""Extract character names from this text from "Peter Pan".
Find ALL: main characters, minor characters, named animals, groups, titled beings.

Text:
{sample_text}

Return ONLY comma-separated character names."""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Extract all character names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        characters_text = response.choices[0].message.content.strip()
        characters = [c.strip() for c in characters_text.split(',') if c.strip()]
        
        print(f"✅ Characters found: {characters}")
        print(f"✅ Character count: {len(characters)}")
        return characters
        
    except Exception as e:
        print(f"❌ Character analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return []

async def test_database_connection():
    """Test database connection and book retrieval"""
    print("\n🗄️ Testing Database Connection...")
    
    try:
        # Test basic connection
        conn = database.get_db_connection()
        if conn:
            print("✅ Database connection successful")
            conn.close()
        else:
            print("❌ Database connection failed")
            return False
        
        # Test getting books
        books = await database.get_all_books()
        print(f"✅ Found {len(books)} books in database")
        
        if books:
            book = books[0]
            print(f"✅ Sample book: {book.get('title', 'Unknown')} by {book.get('author', 'Unknown')}")
            return book['book_id']
        else:
            print("⚠️ No books found in database")
            return None
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_full_character_analysis(book_id):
    """Test the full character analysis workflow"""
    print(f"\n🔬 Testing Full Character Analysis for Book ID: {book_id}...")
    
    try:
        # Get book details
        book = await database.get_book_details(book_id)
        if not book:
            print("❌ Book not found")
            return False
        
        print(f"✅ Book found: {book['title']}")
        print(f"✅ Book path: {book.get('path', 'No path')}")
        
        # Check if file exists
        if 'path' not in book or not os.path.exists(book['path']):
            print("❌ Book file not found")
            return False
        
        # Read content
        with open(book['path'], 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"✅ Content loaded: {len(content):,} characters")
        
        # Test character analysis on first chunk
        chunk_size = 5000
        sample_chunk = content[:chunk_size]
        
        # Use compatible client initialization
        try:
            client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        except TypeError as e:
            if 'proxies' in str(e):
                # Fallback for version compatibility
                client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        
        prompt = f"""Extract character names from this section of "{book['title']}".
Find ALL: main characters, minor characters, named animals, groups, titled beings.

Text section:
{sample_chunk}

Return ONLY comma-separated character names."""
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Extract all character names."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        characters_text = response.choices[0].message.content.strip()
        characters = [c.strip() for c in characters_text.split(',') if c.strip()]
        
        print(f"✅ Characters from sample: {characters}")
        return True
        
    except Exception as e:
        print(f"❌ Full analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all diagnostic tests"""
    print("🚀 KidsKlassiks Character Analysis Diagnostics")
    print("=" * 50)
    
    # Test 1: OpenAI Connection
    openai_ok = await test_openai_connection()
    
    if not openai_ok:
        print("\n❌ OpenAI connection failed. Fix API key before proceeding.")
        return
    
    # Test 2: Character Analysis
    characters = await test_character_analysis()
    
    if not characters:
        print("\n❌ Character analysis failed. Check OpenAI API configuration.")
        return
    
    # Test 3: Database Connection
    book_id = await test_database_connection()
    
    if not book_id:
        print("\n❌ Database connection failed or no books available.")
        return
    
    # Test 4: Full Workflow
    full_test_ok = await test_full_character_analysis(book_id)
    
    if full_test_ok:
        print("\n✅ All tests passed! Character analysis should work.")
    else:
        print("\n❌ Full workflow test failed. Check logs above.")
    
    print("\n" + "=" * 50)
    print("🏁 Diagnostics complete")

if __name__ == "__main__":
    asyncio.run(main())
