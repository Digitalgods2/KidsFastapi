#!/usr/bin/env python3
"""
KidsKlassiks Migration Test Script
Run this after migration to verify everything works
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("\n📦 Testing imports...")
    
    modules_to_test = [
        ("fastapi", "FastAPI framework"),
        ("openai", "OpenAI API"),
        ("jinja2", "Template engine"),
        ("psycopg2", "PostgreSQL driver"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
    ]
    
    success = True
    for module, description in modules_to_test:
        try:
            __import__(module)
            print(f"  ✅ {module:15} - {description}")
        except ImportError as e:
            print(f"  ❌ {module:15} - {description} - {e}")
            success = False
    
    return success
    # Use assert to avoid PyTestReturnNotNoneWarning
    assert success
    return success

def test_files():
    """Test that all required files exist"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        ("main_clean.py", "Main application"),
        ("requirements_clean.txt", "Dependencies"),
        ("config.py", "Configuration"),
        ("database.py", "Database module"),
        ("services/chat_helper.py", "Chat helper (OpenAI >= 1.0)"),
        ("routes/books.py", "Books routes"),
        ("templates", "Template directory"),
        ("static", "Static files directory"),
    ]
    
    success = True
    for filepath, description in required_files:
        path = Path(filepath)
        if path.exists():
            print(f"  ✅ {filepath:35} - {description}")
        else:
            print(f"  ❌ {filepath:35} - {description} - NOT FOUND")
            success = False
    
    return success

def test_openai_api():
    """Test OpenAI API configuration"""
    print("\n🔑 Testing OpenAI API...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("  ❌ OPENAI_API_KEY not found in .env")
            return False
        
        if api_key.startswith("sk-"):
            print(f"  ✅ API key found: sk-...{api_key[-4:]}")
        else:
            print("  ⚠️ API key found but doesn't look like an OpenAI key")
            return False
        
        # Test the new API
        print("\n  Testing OpenAI client initialization...")
        from openai import OpenAI
        
        try:
            client = OpenAI(api_key=api_key)
            print("  ✅ OpenAI client initialized successfully")
            
            # Test a simple API call
            print("  Testing API connection...")
            response = client.models.list()
            print(f"  ✅ API connection successful - {len(list(response))} models available")
            return True
            
        except Exception as e:
            print(f"  ❌ OpenAI API error: {e}")
            return False
            
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

def test_database():
    """Test database connection"""
    print("\n🗄️ Testing database...")
    
    try:
        import database
        
        # Try to initialize
        database.initialize_database()
        print("  ✅ Database initialized")
        
        # Try a simple query
        from database import get_dashboard_stats
        import asyncio
        
        async def test_query():
            stats = await get_dashboard_stats()
            return stats
        
        stats = asyncio.run(test_query())
        print(f"  ✅ Database query successful")
        print(f"     Books: {stats.get('total_books', 0)}")
        print(f"     Adaptations: {stats.get('total_adaptations', 0)}")
        return True
        
    except Exception as e:
        print(f"  ⚠️ Database test failed: {e}")
        print("     This is okay if you haven't set up the database yet")
        return False

def test_server():
    """Test if the server can start"""
    print("\n🌐 Testing server startup...")
    
    try:
        # Try to import the main app
        sys.path.insert(0, str(Path.cwd()))
        
        # Import from the clean version
        if Path("main_clean.py").exists():
            import main_clean
            app = main_clean.app
            print("  ✅ main_clean.py imported successfully")
        else:
            print("  ❌ main_clean.py not found")
            return False
        
        # Check app configuration
        print(f"  ✅ FastAPI app configured: {app.title}")
        print(f"     Version: {app.version}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        important_routes = ["/", "/books/library", "/health", "/dashboard"]
        
        for route in important_routes:
            if route in routes:
                print(f"  ✅ Route registered: {route}")
            else:
                print(f"  ⚠️ Route missing: {route}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Server test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("KidsKlassiks Migration Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Import Test", test_imports()))
    results.append(("File Structure Test", test_files()))
    results.append(("OpenAI API Test", test_openai_api()))
    results.append(("Database Test", test_database()))
    results.append(("Server Test", test_server()))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20} : {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All tests passed! Your migration was successful.")
        print("\nYou can now run: python main_clean.py")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("1. Run: pip install -r requirements_clean.txt")
        print("2. Check your .env file has OPENAI_API_KEY")
        print("3. Run: python comprehensive_migration_fix.py")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
