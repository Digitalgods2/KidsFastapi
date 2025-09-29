# Save this as fix_character_analysis.ps1

Write-Host "Fixing KidsKlassiks Character Analysis" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Fix 1: Fix the CharacterAnalyzer OpenAI client
Write-Host "`nFixing character_analyzer.py..." -ForegroundColor Yellow

@'
"""
Character Analysis Service
Extracts and analyzes characters from book text
"""
import re
from typing import List, Dict
from openai import OpenAI
import config

class CharacterAnalyzer:
    def __init__(self):
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    async def extract_characters(self, text: str, title: str) -> List[Dict[str, str]]:
        """Extract characters from book text using AI"""
        # Take a sample of the text (first 10000 characters)
        sample_text = text[:10000]
        
        prompt = f"""
        Analyze this excerpt from "{title}" and identify the main characters.
        
        Text excerpt:
        {sample_text}
        
        Please identify:
        1. Main characters (protagonists, major supporting characters)
        2. Their role in the story
        3. Brief description
        
        Format as a comma-separated list of character names only.
        Example: Dorothy, Tin Man, Scarecrow, Cowardly Lion
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a literary analyst specializing in character identification."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            characters_text = response.choices[0].message.content.strip()
            characters = [c.strip() for c in characters_text.split(',')]
            
            return characters[:10]  # Limit to 10 main characters
            
        except Exception as e:
            print(f"Error analyzing characters: {e}")
            return []
'@ | Set-Content -Path "services\character_analyzer.py" -Encoding UTF8

Write-Host "Fixed character_analyzer.py" -ForegroundColor Green

# Fix 2: Create a complete books route
Write-Host "`nCreating complete books route..." -ForegroundColor Yellow

@'
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import database
import config
import asyncio

router = APIRouter()
templates = Jinja2Templates(directory='templates')

@router.get('/library', response_class=HTMLResponse)
async def library(request: Request):
    # Get books with proper async handling
    try:
        books = database.get_all_books()
        if asyncio.iscoroutine(books):
            books = await books
    except Exception as e:
        print(f'Error getting books: {e}')
        books = []
    
    # Ensure all required template variables are provided
    context = {
        'request': request,
        'books': books if books else [],
        'stats': {
            'total_books': len(books) if books else 0,
            'total_adaptations': 0,
            'total_images': 0,
            'recent_books': [],
            'recent_adaptations': []
        },
        'total_pages': 1,
        'current_page': 1,
        'page_size': 10,
        'search_query': '',
        'sort_by': 'date_added',
        'openai_status': bool(config.OPENAI_API_KEY),
        'vertex_status': False,
        'notifications': [],
        'notifications_count': 0
    }
    
    return templates.TemplateResponse('pages/library.html', context)

@router.get('/import', response_class=HTMLResponse)
async def import_page(request: Request):
    context = {
        'request': request,
        'openai_status': bool(config.OPENAI_API_KEY),
        'vertex_status': False,
        'notifications': [],
        'notifications_count': 0
    }
    return templates.TemplateResponse('pages/import.html', context)

@router.post('/analyze-characters')
async def analyze_characters(book_id: int = Form(...)):
    from services.character_analyzer import CharacterAnalyzer
    
    try:
        # Get book from database
        book = await database.get_book(book_id)
        if not book:
            return JSONResponse({'success': False, 'error': 'Book not found'}, status_code=404)
        
        # Get book content
        content = None
        if book.get('original_content'):
            content = book['original_content']
        elif book.get('original_content_path'):
            try:
                with open(book['original_content_path'], 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                pass
        
        if not content:
            return JSONResponse({'success': False, 'error': 'No content available for this book'})
        
        # Analyze characters
        analyzer = CharacterAnalyzer()
        characters = await analyzer.extract_characters(content, book.get('title', 'Unknown'))
        
        return JSONResponse({
            'success': True,
            'characters': characters,
            'message': f'Found {len(characters)} characters'
        })
        
    except Exception as e:
        print(f'Character analysis error: {e}')
        import traceback
        traceback.print_exc()
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
'@ | Set-Content -Path "routes\books.py" -Encoding UTF8

Write-Host "Created complete books route" -ForegroundColor Green

# Fix 3: Fix main_clean.py error handlers
Write-Host "`nFixing main_clean.py error handlers..." -ForegroundColor Yellow

$content = Get-Content "main_clean.py" -Raw
$content = $content -replace 'return templates.TemplateResponse\([^)]*"pages/error.html"[^)]*\)', 'return JSONResponse({"error": "Page not found"}, status_code=404)'
$content | Set-Content -Path "main_clean.py" -Encoding UTF8

Write-Host "Fixed error handlers" -ForegroundColor Green

Write-Host "`n=======================================" -ForegroundColor Cyan
Write-Host "All fixes applied successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Restart server: python -m uvicorn main_clean:app --host 127.0.0.1 --port 8000 --reload"
Write-Host "2. Go to http://localhost:8000/adaptations/create?book_id=35"
Write-Host "3. Character analysis should now work!"