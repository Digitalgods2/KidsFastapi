#!/usr/bin/env python3
"""Test adaptation tab filtering and counts"""

import asyncio
import sys
sys.path.insert(0, '/home/user/webapp')

import database_fixed as database

async def test_tabs():
    print("Testing adaptation tab logic...\n")
    
    all_items = await database.get_all_adaptations_with_stats()
    
    # Calculate counts using same logic as routes
    completed_count = sum(1 for a in all_items 
                         if a.get('chapter_count', 0) > 0 
                         and a.get('image_count', 0) >= a.get('chapter_count', 0))
    progress_count = sum(1 for a in all_items 
                        if a.get('chapter_count', 0) > 0 
                        and a.get('image_count', 0) < a.get('chapter_count', 0))
    
    print(f"Tab Counts:")
    print(f"  All: {len(all_items)}")
    print(f"  In Progress: {progress_count}")
    print(f"  Completed: {completed_count}")
    print()
    
    print("Adaptations Details:")
    for a in all_items:
        chapter_count = a.get('chapter_count', 0)
        image_count = a.get('image_count', 0)
        is_completed = chapter_count > 0 and image_count >= chapter_count
        is_in_progress = chapter_count > 0 and image_count < chapter_count
        
        status = 'Completed ✅' if is_completed else 'In Progress 🔄' if is_in_progress else 'Not Started ⏳'
        progress_pct = int(image_count / chapter_count * 100) if chapter_count > 0 else 0
        
        print(f"{a['book_title']} (Age {a['target_age_group']})")
        print(f"  Chapters: {chapter_count}, Images: {image_count}/{chapter_count} ({progress_pct}%)")
        print(f"  Status: {status}")
        print()
    
    # Verify counts
    expected_all = 3
    expected_progress = 2
    expected_completed = 1
    
    if len(all_items) == expected_all and progress_count == expected_progress and completed_count == expected_completed:
        print("✅ SUCCESS: Tab counts are correct!")
        return True
    else:
        print(f"❌ FAILED: Expected All={expected_all}, Progress={expected_progress}, Completed={expected_completed}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tabs())
    sys.exit(0 if success else 1)
