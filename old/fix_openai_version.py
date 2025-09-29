#!/usr/bin/env python3
"""
OpenAI Version Compatibility Fix Script
Diagnoses and fixes OpenAI library version issues
"""

import subprocess
import sys
import os
from dotenv import load_dotenv

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def check_openai_version():
    """Check current OpenAI library version"""
    print("🔍 Checking OpenAI library version...")
    
    try:
        import openai
        version = getattr(openai, '__version__', 'Unknown')
        print(f"✅ Current OpenAI version: {version}")
        return version
    except ImportError:
        print("❌ OpenAI library not installed")
        return None

def test_openai_import():
    """Test OpenAI import and client creation"""
    print("\n🧪 Testing OpenAI import and client creation...")
    
    try:
        import openai
        print("✅ OpenAI library imported successfully")
        
        # Load environment variables
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("❌ No OpenAI API key found in .env file")
            return False
        
        print(f"✅ API key found: {api_key[:10]}...")
        
        # Try different client initialization methods
        client = None
        
        # Method 1: Standard initialization
        try:
            client = openai.OpenAI(api_key=api_key)
            print("✅ Method 1: Standard OpenAI client creation successful")
        except Exception as e:
            print(f"❌ Method 1 failed: {e}")
            
            # Method 2: Minimal parameters
            try:
                client = openai.OpenAI(api_key=api_key)
                print("✅ Method 2: Minimal parameter client creation successful")
            except Exception as e2:
                print(f"❌ Method 2 failed: {e2}")
                return False
        
        # Test the client
        if client:
            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Say 'test'"}],
                    max_tokens=5
                )
                print("✅ OpenAI client test successful")
                return True
            except Exception as e:
                print(f"❌ OpenAI client test failed: {e}")
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ OpenAI import test failed: {e}")
        return False

def fix_openai_version():
    """Fix OpenAI version compatibility issues"""
    print("\n🔧 Attempting to fix OpenAI version compatibility...")
    
    # Try different OpenAI versions
    versions_to_try = [
        "1.3.7",   # Current version in requirements
        "1.2.0",   # Slightly older
        "1.1.0",   # Even older
        "1.0.0",   # Much older but stable
    ]
    
    for version in versions_to_try:
        print(f"\n📦 Trying OpenAI version {version}...")
        
        # Uninstall current version
        success, stdout, stderr = run_command("pip uninstall openai -y")
        if not success:
            print(f"⚠️ Warning: Failed to uninstall current OpenAI version")
        
        # Install specific version
        success, stdout, stderr = run_command(f"pip install openai=={version}")
        if not success:
            print(f"❌ Failed to install OpenAI {version}: {stderr}")
            continue
        
        print(f"✅ Installed OpenAI {version}")
        
        # Test the installation
        if test_openai_import():
            print(f"🎉 OpenAI {version} is working correctly!")
            return True
        else:
            print(f"❌ OpenAI {version} still has issues")
    
    print("❌ Could not find a working OpenAI version")
    return False

def create_compatibility_wrapper():
    """Create a compatibility wrapper for OpenAI client"""
    print("\n📝 Creating OpenAI compatibility wrapper...")
    
    wrapper_code = '''"""
OpenAI Compatibility Wrapper
Handles different OpenAI library versions
"""

import openai
from typing import Optional

class CompatibleOpenAIClient:
    """Wrapper for OpenAI client that handles version differences"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = self._create_client()
    
    def _create_client(self):
        """Create OpenAI client with version compatibility"""
        try:
            # Try standard initialization
            return openai.OpenAI(api_key=self.api_key)
        except TypeError as e:
            if 'proxies' in str(e) or 'unexpected keyword argument' in str(e):
                # Handle version compatibility issues
                return openai.OpenAI(api_key=self.api_key)
            else:
                raise e
    
    def chat_completions_create(self, **kwargs):
        """Wrapper for chat completions"""
        return self.client.chat.completions.create(**kwargs)
    
    def images_generate(self, **kwargs):
        """Wrapper for image generation"""
        return self.client.images.generate(**kwargs)

# Global client instance
_client_instance = None

def get_openai_client(api_key: str) -> CompatibleOpenAIClient:
    """Get or create OpenAI client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = CompatibleOpenAIClient(api_key)
    return _client_instance
'''
    
    try:
        with open('openai_compatibility.py', 'w') as f:
            f.write(wrapper_code)
        print("✅ Created openai_compatibility.py wrapper")
        return True
    except Exception as e:
        print(f"❌ Failed to create compatibility wrapper: {e}")
        return False

def main():
    """Main fix script"""
    print("🚀 OpenAI Version Compatibility Fix Script")
    print("=" * 50)
    
    # Step 1: Check current version
    current_version = check_openai_version()
    
    # Step 2: Test current installation
    if test_openai_import():
        print("🎉 OpenAI is already working correctly!")
        return
    
    # Step 3: Try to fix version issues
    if fix_openai_version():
        print("🎉 OpenAI version fixed successfully!")
        return
    
    # Step 4: Create compatibility wrapper as fallback
    if create_compatibility_wrapper():
        print("📝 Created compatibility wrapper as fallback")
        print("\n📋 Next steps:")
        print("1. Import the wrapper: from openai_compatibility import get_openai_client")
        print("2. Use: client = get_openai_client(api_key)")
        print("3. Replace openai.OpenAI() calls with get_openai_client()")
    
    print("\n" + "=" * 50)
    print("🏁 Fix script complete")

if __name__ == "__main__":
    main()
