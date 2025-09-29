#!/usr/bin/env python3
"""
Deep OpenAI Debugging Script
Finds the exact source of the 'proxies' parameter issue
"""

import os
import sys
import inspect
import traceback
from dotenv import load_dotenv

def trace_openai_init():
    """Trace exactly what's happening in OpenAI initialization"""
    print("🔍 Deep tracing OpenAI initialization...")
    
    try:
        import openai
        print(f"✅ OpenAI imported from: {openai.__file__}")
        print(f"✅ OpenAI version: {getattr(openai, '__version__', 'Unknown')}")
        
        # Get the OpenAI class
        openai_class = openai.OpenAI
        print(f"✅ OpenAI class: {openai_class}")
        
        # Inspect the __init__ method
        init_method = openai_class.__init__
        print(f"✅ __init__ method: {init_method}")
        
        # Get the signature
        sig = inspect.signature(init_method)
        print(f"✅ __init__ signature: {sig}")
        
        # List all parameters
        print("📋 __init__ parameters:")
        for name, param in sig.parameters.items():
            print(f"  - {name}: {param}")
        
        # Check if 'proxies' is in the parameters
        if 'proxies' in sig.parameters:
            print("✅ 'proxies' parameter is supported")
        else:
            print("❌ 'proxies' parameter is NOT supported")
        
        return sig.parameters
        
    except Exception as e:
        print(f"❌ Error tracing OpenAI init: {e}")
        traceback.print_exc()
        return None

def test_minimal_init():
    """Test the most minimal OpenAI initialization possible"""
    print("\n🧪 Testing minimal OpenAI initialization...")
    
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ No API key found")
        return False
    
    try:
        import openai
        
        # Try with absolutely minimal parameters
        print("🔍 Attempting minimal initialization...")
        
        # Method 1: Only api_key
        try:
            print("  Method 1: openai.OpenAI(api_key=api_key)")
            client = openai.OpenAI(api_key=api_key)
            print("  ✅ Success!")
            return client
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        # Method 2: Using keyword arguments explicitly
        try:
            print("  Method 2: openai.OpenAI(**{'api_key': api_key})")
            client = openai.OpenAI(**{'api_key': api_key})
            print("  ✅ Success!")
            return client
        except Exception as e:
            print(f"  ❌ Failed: {e}")
        
        # Method 3: Check if there are any default parameters being set
        try:
            print("  Method 3: Checking for default parameters...")
            
            # Get the class
            openai_class = openai.OpenAI
            
            # Try to create with no parameters at all (will fail but show us the signature)
            try:
                client = openai_class()
            except Exception as e:
                print(f"  📋 No-param error (expected): {e}")
                
                # This error message might tell us what parameters are required/default
                error_str = str(e)
                if 'proxies' in error_str:
                    print("  🔍 'proxies' mentioned in error - this is the clue!")
        
        except Exception as e:
            print(f"  ❌ Method 3 failed: {e}")
        
        return None
        
    except Exception as e:
        print(f"❌ Minimal init test failed: {e}")
        traceback.print_exc()
        return None

def check_environment_variables():
    """Check for any environment variables that might affect OpenAI"""
    print("\n🌍 Checking environment variables...")
    
    openai_related_vars = []
    proxy_related_vars = []
    
    for key, value in os.environ.items():
        if 'openai' in key.lower():
            openai_related_vars.append((key, value))
        if 'proxy' in key.lower() or 'http_proxy' in key.lower() or 'https_proxy' in key.lower():
            proxy_related_vars.append((key, value))
    
    if openai_related_vars:
        print("📋 OpenAI-related environment variables:")
        for key, value in openai_related_vars:
            # Mask sensitive values
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"  {key} = {display_value}")
    else:
        print("✅ No OpenAI-related environment variables found")
    
    if proxy_related_vars:
        print("📋 Proxy-related environment variables:")
        for key, value in proxy_related_vars:
            print(f"  {key} = {value}")
        print("🔍 These proxy settings might be causing the issue!")
        return proxy_related_vars
    else:
        print("✅ No proxy-related environment variables found")
        return []

def check_openai_config_files():
    """Check for OpenAI configuration files"""
    print("\n📁 Checking for OpenAI configuration files...")
    
    possible_config_locations = [
        os.path.expanduser("~/.openai"),
        os.path.expanduser("~/.config/openai"),
        os.path.join(os.getcwd(), ".openai"),
        os.path.join(os.getcwd(), "openai.conf"),
    ]
    
    found_configs = []
    
    for location in possible_config_locations:
        if os.path.exists(location):
            found_configs.append(location)
            print(f"📋 Found config: {location}")
            
            try:
                if os.path.isfile(location):
                    with open(location, 'r') as f:
                        content = f.read()
                        if 'proxies' in content.lower():
                            print(f"🔍 'proxies' found in {location}!")
                            print(f"Content preview: {content[:200]}...")
            except Exception as e:
                print(f"⚠️ Could not read {location}: {e}")
    
    if not found_configs:
        print("✅ No OpenAI configuration files found")
    
    return found_configs

def try_older_openai_version():
    """Try the very old OpenAI library version with different API"""
    print("\n🕰️ Trying older OpenAI library version (0.28.x)...")
    
    try:
        import subprocess
        
        # Install old version
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "openai==0.28.1"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to install openai==0.28.1: {result.stderr}")
            return False
        
        print("✅ Installed openai==0.28.1")
        
        # Clear the module cache
        if 'openai' in sys.modules:
            del sys.modules['openai']
        
        # Import the old version
        import openai
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        # Old API style
        openai.api_key = api_key
        
        # Test with old API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Say 'old API works'"}],
            max_tokens=10
        )
        
        print(f"✅ Old API test successful: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ Old version test failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🚀 Deep OpenAI Debugging Script")
    print("=" * 50)
    
    # Step 1: Trace the OpenAI initialization
    params = trace_openai_init()
    
    # Step 2: Check environment variables
    proxy_vars = check_environment_variables()
    
    # Step 3: Check for config files
    config_files = check_openai_config_files()
    
    # Step 4: Test minimal initialization
    client = test_minimal_init()
    
    # Step 5: If all else fails, try old version
    if not client:
        print("\n🔄 All modern versions failed, trying legacy version...")
        if try_older_openai_version():
            print("🎉 Legacy OpenAI version works!")
            print("📋 Recommendation: Use openai==0.28.1 with old API style")
        else:
            print("❌ Even legacy version failed")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    if proxy_vars:
        print("🔍 LIKELY CAUSE: Proxy environment variables detected")
        print("💡 SOLUTION: Unset proxy variables or configure OpenAI to ignore them")
        for key, value in proxy_vars:
            print(f"   Unset: {key}")
    
    if config_files:
        print("🔍 POSSIBLE CAUSE: OpenAI configuration files found")
        print("💡 SOLUTION: Check these files for proxy settings")
    
    if not client:
        print("🔍 RECOMMENDATION: Use legacy OpenAI version (0.28.1)")
        print("💡 SOLUTION: pip install openai==0.28.1 and use old API style")
    
    print("\n🏁 Deep debugging complete")

if __name__ == "__main__":
    main()
