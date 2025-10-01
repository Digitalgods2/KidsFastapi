#!/usr/bin/env python3
"""
Quick script to transform A Christmas Carol chapters to age-appropriate text
"""
import asyncio
import sys
import requests

BASE_URL = "http://127.0.0.1:8000"
ADAPTATION_ID = 11  # A Christmas Carol for ages 6-8

async def transform_all_chapters():
    """Transform all chapters in A Christmas Carol adaptation"""
    print("=" * 60)
    print("TRANSFORMING A CHRISTMAS CAROL TO AGE-APPROPRIATE TEXT")
    print("=" * 60)
    print(f"\nAdaptation ID: {ADAPTATION_ID}")
    print(f"Target Age Group: 6-8 years")
    print("\nThis will transform all 17 chapters from Victorian English")
    print("to simple, child-friendly language.\n")
    
    # Call the transform-all endpoint
    print("Calling API endpoint...")
    print(f"POST {BASE_URL}/adaptations/{ADAPTATION_ID}/transform-all")
    print("\nThis may take 5-10 minutes for 17 chapters...\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/adaptations/{ADAPTATION_ID}/transform-all",
            timeout=600  # 10 minute timeout for all chapters
        )
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!\n")
            print(f"Total chapters: {result.get('total_chapters')}")
            print(f"Successfully transformed: {result.get('success_count')}")
            print(f"Errors: {result.get('error_count')}")
            
            if result.get('results'):
                print("\nPer-chapter results:")
                for r in result.get('results', []):
                    status_icon = "✅" if r['status'] == 'success' else "⏭️" if r['status'] == 'skipped' else "❌"
                    print(f"  {status_icon} Chapter {r['chapter_number']}: {r['status']}")
                    if r['status'] == 'success':
                        print(f"     Original: {r.get('original_length')} chars")
                        print(f"     Transformed: {r.get('transformed_length')} chars")
            
            print("\n🎉 Transformation complete!")
            print("\nNow you can:")
            print("1. View preview at: http://127.0.0.1:8000/publish/adaptation/11")
            print("2. Export PDF at: http://127.0.0.1:8000/publish/")
            print("\nThe text will now be age-appropriate for 6-8 year olds!")
            
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("\n⏱️  Request timed out. The transformation may still be running.")
        print("Check the server logs or try viewing the preview page.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    print("\nNOTE: Make sure the FastAPI server is running first!")
    print("      Run: cd /home/user/webapp && uvicorn main:app\n")
    
    proceed = input("Proceed with transformation? (y/n): ")
    if proceed.lower() == 'y':
        asyncio.run(transform_all_chapters())
    else:
        print("Transformation cancelled.")
