"""
Fixed character analysis endpoint with comprehensive error handling and debugging
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import asyncio
import os
import uuid
import re
import openai
import traceback

import database as database
from models import BookImportRequest, BookResponse
import config

@router.post("/analyze-characters")
async def analyze_characters_fixed(book_id: int = Form(...)):
    """
    Enhanced character analysis with comprehensive error handling and debugging
    """
    print(f"\n🎭 Starting character analysis for book ID: {book_id}")
    
    try:
        # Step 1: Validate OpenAI configuration
        print("🔍 Step 1: Validating OpenAI configuration...")
        
        if not config.OPENAI_API_KEY:
            error_msg = "OpenAI API key not found in environment variables"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "Configuration Error",
                "message": error_msg,
                "debug_info": "Check your .env file for OPENAI_API_KEY"
            })
        
        if config.OPENAI_API_KEY == "YOUR_KEY_HERE" or config.OPENAI_API_KEY.startswith("sk-") == False:
            error_msg = "OpenAI API key appears to be invalid format"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "Configuration Error",
                "message": error_msg,
                "debug_info": "API key should start with 'sk-'"
            })
        
        print(f"✅ OpenAI API key configured (starts with: {config.OPENAI_API_KEY[:10]}...)")
        
        # Step 2: Get book details
        print("📚 Step 2: Retrieving book details...")
        
        book = await database.get_book_details(book_id)
        if not book:
            error_msg = f"Book with ID {book_id} not found in database"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "Book Not Found",
                "message": error_msg
            })
        
        print(f"✅ Book found: '{book['title']}' by {book.get('author', 'Unknown')}")
        
        # Step 3: Validate file path and read content
        print("📖 Step 3: Reading book content...")
        
        if 'path' not in book or not book['path']:
            error_msg = "Book file path not found in database"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "File Path Error",
                "message": error_msg,
                "debug_info": f"Book record: {book}"
            })
        
        if not os.path.exists(book['path']):
            error_msg = f"Book file not found at path: {book['path']}"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "File Not Found",
                "message": error_msg,
                "debug_info": f"Expected path: {book['path']}"
            })
        
        try:
            with open(book['path'], 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(book['path'], 'r', encoding='latin-1') as f:
                    content = f.read()
                print("⚠️ Used latin-1 encoding fallback")
            except Exception as e:
                error_msg = f"Failed to read file with any encoding: {str(e)}"
                print(f"❌ {error_msg}")
                return JSONResponse({
                    "success": False, 
                    "error": "File Reading Error",
                    "message": error_msg
                })
        except Exception as e:
            error_msg = f"Failed to read book file: {str(e)}"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "File Reading Error",
                "message": error_msg
            })
        
        print(f"✅ Content loaded: {len(content):,} characters")
        
        # Step 4: Test OpenAI connection with simple request
        print("🤖 Step 4: Testing OpenAI API connection...")
        
        try:
            client = openai.Client(api_key=config.OPENAI_API_KEY)
            
            # Simple test request
            test_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Respond with exactly: 'API test successful'"}
                ],
                max_tokens=10,
                temperature=0
            )
            
            test_result = test_response.choices[0].message.content.strip()
            print(f"✅ OpenAI API test: {test_result}")
            
        except openai.AuthenticationError as e:
            error_msg = f"OpenAI authentication failed: {str(e)}"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "Authentication Error",
                "message": "Invalid OpenAI API key",
                "debug_info": str(e)
            })
        except openai.RateLimitError as e:
            error_msg = f"OpenAI rate limit exceeded: {str(e)}"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "Rate Limit Error",
                "message": "OpenAI API rate limit exceeded. Please try again later.",
                "debug_info": str(e)
            })
        except openai.APIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "API Error",
                "message": f"OpenAI API error: {str(e)}",
                "debug_info": str(e)
            })
        except Exception as e:
            error_msg = f"Unexpected OpenAI error: {str(e)}"
            print(f"❌ {error_msg}")
            return JSONResponse({
                "success": False, 
                "error": "Connection Error",
                "message": "Failed to connect to OpenAI API",
                "debug_info": str(e)
            })
        
        # Step 5: Process book content for character analysis
        print("🔍 Step 5: Analyzing characters...")
        
        # Use smaller chunks for more reliable processing
        chunk_size = 8000  # Reduced from 15000 for better reliability
        chunks = []
        
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            chunks.append(chunk)
        
        print(f"📄 Split book into {len(chunks)} chunks for analysis")
        
        all_characters = set()
        successful_chunks = 0
        failed_chunks = 0
        
        # Process chunks with better error handling
        for idx, chunk in enumerate(chunks):
            print(f"🔍 Analyzing chunk {idx + 1}/{len(chunks)}...")
            
            # Skip very short chunks
            if len(chunk.strip()) < 100:
                print(f"⏭️ Skipping short chunk {idx + 1}")
                continue
            
            prompt = f"""Extract character names from this section of "{book['title']}".
Find ALL characters mentioned: main characters, minor characters, named people, animals with names.
Only return actual character names, not descriptions or titles alone.

Text section:
{chunk[:4000]}

Return ONLY comma-separated character names. If no characters found, return "None"."""
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are an expert at identifying character names in literature. Extract only actual names of characters."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=300,
                    timeout=30  # Add timeout
                )
                
                chunk_characters = response.choices[0].message.content.strip()
                
                if chunk_characters and chunk_characters.lower() != "none":
                    characters_in_chunk = [c.strip() for c in chunk_characters.split(',') if c.strip() and len(c.strip()) > 1]
                    all_characters.update(characters_in_chunk)
                    print(f"✅ Chunk {idx + 1}: Found {len(characters_in_chunk)} characters")
                else:
                    print(f"⚪ Chunk {idx + 1}: No characters found")
                
                successful_chunks += 1
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except openai.RateLimitError as e:
                print(f"⚠️ Rate limit hit on chunk {idx + 1}, waiting...")
                await asyncio.sleep(2)
                failed_chunks += 1
                continue
            except Exception as e:
                print(f"⚠️ Error in chunk {idx + 1}: {str(e)}")
                failed_chunks += 1
                continue
        
        print(f"📊 Processing complete: {successful_chunks} successful, {failed_chunks} failed")
        
        # Step 6: Clean and deduplicate characters
        print("🧹 Step 6: Cleaning and deduplicating characters...")
        
        unique_characters = []
        seen_lower = set()
        
        for char in sorted(all_characters):
            if char and len(char) > 1 and len(char) < 50:  # Reasonable name length
                char_clean = char.strip().strip('"').strip("'")
                char_lower = char_clean.lower()
                
                # Skip common non-character words
                skip_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'chapter', 'book', 'story', 'tale'}
                if char_lower not in skip_words and char_lower not in seen_lower:
                    seen_lower.add(char_lower)
                    unique_characters.append(char_clean)
        
        print(f"✅ Found {len(unique_characters)} unique characters")
        print(f"📝 Characters: {', '.join(unique_characters[:10])}{'...' if len(unique_characters) > 10 else ''}")
        
        # Step 7: Detect chapters and update database
        print("📖 Step 7: Detecting chapters and updating database...")
        
        try:
            from routes.books import detect_chapters_universal
            chapter_count = detect_chapters_universal(content)
            word_count = len(content.split())
            
            print(f"📊 Analysis results: {word_count:,} words, {chapter_count} chapters")
            
            # Update database
            await database.update_book_analysis(
                book_id, 
                word_count, 
                chapter_count, 
                ", ".join(unique_characters)
            )
            
            print("✅ Database updated successfully")
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to update database: {str(e)}")
            # Continue anyway, we still have the characters
            chapter_count = 0
            word_count = len(content.split())
        
        # Step 8: Return success response
        print("🎉 Step 8: Analysis complete!")
        
        return JSONResponse({
            "success": True,
            "characters": unique_characters,
            "message": f"Successfully found {len(unique_characters)} characters",
            "word_count": word_count,
            "chapter_count": chapter_count,
            "debug_info": {
                "chunks_processed": successful_chunks,
                "chunks_failed": failed_chunks,
                "total_chunks": len(chunks),
                "content_length": len(content)
            }
        })
        
    except Exception as e:
        error_msg = f"Unexpected error during character analysis: {str(e)}"
        print(f"❌ {error_msg}")
        print("🔍 Full traceback:")
        traceback.print_exc()
        
        return JSONResponse({
            "success": False,
            "error": "Analysis Error",
            "message": "Character analysis failed due to an unexpected error",
            "debug_info": {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        })
