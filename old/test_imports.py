#!/usr/bin/env python3
"""
Test script to identify import issues with legacy OpenAI
"""

print("🧪 Testing imports for KidsKlassiks...")

try:
    print("1. Testing basic OpenAI import...")
    import openai
    print(f"   ✅ OpenAI version: {openai.__version__}")
except Exception as e:
    print(f"   ❌ OpenAI import failed: {e}")

try:
    print("2. Testing legacy OpenAI service...")
    from legacy.services.openai_service_legacy_complete import get_legacy_openai_service
    service = get_legacy_openai_service()
    print("   ✅ Legacy OpenAI service imported successfully")
except Exception as e:
    print(f"   ❌ Legacy OpenAI service failed: {e}")

try:
    print("3. Testing transformation service...")
    from services.transformation_service import TransformationService
    print("   ✅ Transformation service imported successfully")
except Exception as e:
    print(f"   ❌ Transformation service failed: {e}")

try:
    print("4. Testing services package...")
    import services
    print("   ✅ Services package imported successfully")
except Exception as e:
    print(f"   ❌ Services package failed: {e}")

try:
    print("5. Testing routes package...")
    import routes
    print("   ✅ Routes package imported successfully")
except Exception as e:
    print(f"   ❌ Routes package failed: {e}")

try:
    print("6. Testing main application...")
    import main
    print("   ✅ Main application imported successfully")
except Exception as e:
    print(f"   ❌ Main application failed: {e}")

print("\n🏁 Import test complete!")
