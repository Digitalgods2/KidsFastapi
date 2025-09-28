"""
OpenAI Client Fix for Version Compatibility Issues
Handles different OpenAI library versions and initialization parameters
"""

import openai
from typing import Optional

def create_openai_client(api_key: str, **kwargs) -> openai.OpenAI:
    """
    Create OpenAI client with version compatibility handling
    
    Args:
        api_key: OpenAI API key
        **kwargs: Additional parameters (filtered for compatibility)
        
    Returns:
        OpenAI client instance
    """
    
    # Get OpenAI library version
    openai_version = getattr(openai, '__version__', '0.0.0')
    print(f"🔍 OpenAI library version: {openai_version}")
    
    # Parameters that are safe for all versions
    safe_params = {
        'api_key': api_key
    }
    
    # Parameters that may not be supported in newer versions
    potentially_unsupported = ['proxies', 'organization', 'base_url']
    
    # Only add supported parameters
    for key, value in kwargs.items():
        if key not in potentially_unsupported:
            safe_params[key] = value
    
    try:
        # Try creating client with safe parameters only
        client = openai.OpenAI(**safe_params)
        print("✅ OpenAI client created successfully")
        return client
        
    except TypeError as e:
        if 'unexpected keyword argument' in str(e):
            print(f"⚠️ Parameter compatibility issue: {e}")
            
            # Fall back to minimal parameters
            minimal_params = {'api_key': api_key}
            
            try:
                client = openai.OpenAI(**minimal_params)
                print("✅ OpenAI client created with minimal parameters")
                return client
            except Exception as fallback_error:
                print(f"❌ Failed to create OpenAI client: {fallback_error}")
                raise fallback_error
        else:
            raise e
    except Exception as e:
        print(f"❌ Failed to create OpenAI client: {e}")
        raise e

def test_openai_client(client: openai.OpenAI) -> bool:
    """
    Test OpenAI client with a simple request
    
    Args:
        client: OpenAI client instance
        
    Returns:
        True if client works, False otherwise
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'test successful'"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI test response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        return False

# Example usage and testing
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OpenAI API key found")
        exit(1)
    
    print("🚀 Testing OpenAI Client Compatibility")
    print("=" * 40)
    
    try:
        # Create client
        client = create_openai_client(api_key)
        
        # Test client
        if test_openai_client(client):
            print("🎉 OpenAI client is working correctly!")
        else:
            print("❌ OpenAI client test failed")
            
    except Exception as e:
        print(f"❌ OpenAI client setup failed: {e}")
