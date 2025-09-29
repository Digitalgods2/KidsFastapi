#!/usr/bin/env python3
"""
Direct fix script for KidsKlassiks import issues
This script will modify the existing files to fix the OpenAI import conflicts
"""

import os
import shutil

def backup_file(filepath):
    """Create a backup of a file"""
    if os.path.exists(filepath):
        backup_path = filepath + ".backup"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backed up {filepath} to {backup_path}")
        return True
    return False

def fix_routes_init():
    """Fix the routes/__init__.py file"""
    routes_init_path = "routes/__init__.py"
    
    if not os.path.exists(routes_init_path):
        print(f"❌ {routes_init_path} not found")
        return False
    
    backup_file(routes_init_path)
    
    new_content = '''"""
Routes package for KidsKlassiks FastAPI application
Contains all API endpoints and route handlers
"""

# Import only the routes that don't have modern OpenAI dependencies
from . import adaptations, review, settings

# Note: books and images are imported directly in main.py as legacy versions

__all__ = ['adaptations', 'review', 'settings']
'''
    
    with open(routes_init_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Fixed {routes_init_path}")
    return True

def fix_services_init():
    """Fix the services/__init__.py file"""
    services_init_path = "services/__init__.py"
    
    if not os.path.exists(services_init_path):
        print(f"❌ {services_init_path} not found")
        return False
    
    backup_file(services_init_path)
    
    new_content = '''"""
Services package for KidsKlassiks FastAPI application
Contains AI operations, text processing, and other business logic
"""

# Use legacy OpenAI service for compatibility with openai==0.28.1
try:
    from .openai_service_legacy_complete import get_legacy_openai_service
    OpenAIService = get_legacy_openai_service
except ImportError:
    print("⚠️ Legacy OpenAI service not available, using placeholder")
    OpenAIService = None

from .text_processing import TextProcessor
from .pdf_generator import PDFGenerator

# Use simplified vertex service to avoid Google Cloud dependencies
try:
    from .vertex_service import VertexService
except ImportError:
    from .vertex_service_simple import VertexService
    print("ℹ️ Using simplified Vertex AI service (Google Cloud dependencies not available)")

__all__ = [
    'OpenAIService',
    'VertexService', 
    'TextProcessor',
    'PDFGenerator'
]
'''
    
    with open(services_init_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Fixed {services_init_path}")
    return True

def create_legacy_openai_service():
    """Create the legacy OpenAI service if it doesn't exist"""
    service_path = "services/openai_service_legacy_complete.py"
    
    if os.path.exists(service_path):
        print(f"✅ {service_path} already exists")
        return True
    
    service_content = '''"""
Legacy OpenAI Service for KidsKlassiks
Uses OpenAI 0.28.1 API that works without the 'proxies' parameter issue
"""

import openai
import os
from typing import Optional, Tuple, Dict, Any

# Set API key from environment
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_legacy_openai_service():
    """Get configured legacy OpenAI service instance"""
    return LegacyOpenAIService()

class LegacyOpenAIService:
    def __init__(self):
        """Initialize legacy OpenAI service"""
        pass
        
    async def analyze_characters(self, book_content: str, book_title: str) -> Tuple[Optional[str], Optional[str]]:
        """Analyze characters in the book content using legacy OpenAI API"""
        try:
            print(f"🎭 Starting legacy character analysis for book: {book_title}")
            
            # Truncate content if too long
            content_preview = book_content[:8000] if len(book_content) > 8000 else book_content
            
            prompt = f"""
            Analyze this book text and extract all the main and important minor characters.
            
            Book Title: {book_title}
            
            Text to analyze:
            {content_preview}
            
            Please provide a comma-separated list of character names only. Include:
            - Main protagonists and antagonists
            - Important supporting characters
            - Characters that appear multiple times
            - Characters essential to the plot
            
            Format: Character Name 1, Character Name 2, Character Name 3, etc.
            
            Do not include generic terms like "narrator" or "townspeople". Only specific named characters.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert literary analyst. Extract character names accurately and concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            if response and response.choices:
                characters_text = response.choices[0].message.content.strip()
                print(f"✅ Legacy character analysis complete: {characters_text[:100]}...")
                return characters_text, None
            else:
                error_msg = "No response from OpenAI for character analysis"
                print(f"❌ {error_msg}")
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Error in character analysis: {str(e)}"
            print(f"❌ {error_msg}")
            return None, error_msg
    
    async def test_connection(self) -> Tuple[bool, str]:
        """Test OpenAI API connection"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10
            )
            
            if response and response.choices:
                return True, "OpenAI API connection successful"
            else:
                return False, "No response from OpenAI API"
                
        except Exception as e:
            return False, f"OpenAI API connection failed: {str(e)}"
'''
    
    with open(service_path, 'w', encoding='utf-8') as f:
        f.write(service_content)
    
    print(f"✅ Created {service_path}")
    return True

def main():
    """Main fix function"""
    print("🔧 KidsKlassiks Direct Import Fix")
    print("=================================")
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ main.py not found. Please run this script from the KidsKlassiks directory.")
        return False
    
    print("📁 Current directory:", os.getcwd())
    
    # Apply fixes
    success = True
    
    print("\\n🔧 Fixing routes/__init__.py...")
    success &= fix_routes_init()
    
    print("\\n🔧 Fixing services/__init__.py...")
    success &= fix_services_init()
    
    print("\\n🔧 Creating legacy OpenAI service...")
    success &= create_legacy_openai_service()
    
    if success:
        print("\\n✅ All fixes applied successfully!")
        print("🚀 Try starting the server now:")
        print("   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload")
    else:
        print("\\n❌ Some fixes failed. Check the error messages above.")
    
    return success

if __name__ == "__main__":
    main()
