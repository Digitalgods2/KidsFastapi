#!/usr/bin/env python3
"""
Script to fix existing image filenames to use chapter_number instead of chapter_id
"""
import os
import sys
import sqlite3
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_image_filenames():
    """Rename existing image files to use chapter_number instead of chapter_id"""
    
    db_path = 'kidsklassiks.db'
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Get all chapters with images
        cur.execute('''
            SELECT chapter_id, chapter_number, adaptation_id, image_url
            FROM chapters
            WHERE image_url IS NOT NULL
            ORDER BY chapter_id
        ''')
        
        chapters = cur.fetchall()
        print(f"📊 Found {len(chapters)} chapters with images")
        
        renamed_count = 0
        skipped_count = 0
        error_count = 0
        
        for chapter_id, chapter_number, adaptation_id, image_url in chapters:
            # Parse the current filename
            # Example: /generated_images/9/adaptation_8_chapter_156_vertex.png
            old_path = image_url.lstrip('/')
            
            # Check if file exists
            if not os.path.exists(old_path):
                print(f"⚠️  File not found, skipping: {old_path}")
                skipped_count += 1
                continue
            
            # Extract the model name from filename
            filename = os.path.basename(old_path)
            parts = filename.split('_')
            
            # Expected format: adaptation_X_chapter_Y_model.png
            if len(parts) < 5:
                print(f"⚠️  Unexpected filename format, skipping: {filename}")
                skipped_count += 1
                continue
            
            # Get model name (everything after "chapter_XXX_")
            model_part = '_'.join(parts[4:])  # e.g., "vertex.png" or "dall-e-3.png"
            
            # Create new filename with chapter_number
            new_filename = f"adaptation_{adaptation_id}_chapter_{chapter_number}_{model_part}"
            directory = os.path.dirname(old_path)
            new_path = os.path.join(directory, new_filename)
            new_url = f"/{new_path}"
            
            # Check if already correct
            if old_path == new_path:
                print(f"✅ Already correct: {filename}")
                skipped_count += 1
                continue
            
            # Check if target already exists
            if os.path.exists(new_path):
                print(f"⚠️  Target exists, skipping: {new_filename}")
                skipped_count += 1
                continue
            
            try:
                # Rename the file
                shutil.move(old_path, new_path)
                
                # Update database
                cur.execute('''
                    UPDATE chapters
                    SET image_url = ?
                    WHERE chapter_id = ?
                ''', (new_url, chapter_id))
                
                print(f"✨ Renamed: {filename} → {new_filename}")
                renamed_count += 1
                
            except Exception as e:
                print(f"❌ Error renaming {filename}: {e}")
                error_count += 1
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*80)
        print(f"📊 Summary:")
        print(f"   ✨ Renamed: {renamed_count}")
        print(f"   ⚠️  Skipped: {skipped_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📁 Total: {len(chapters)}")
        print("="*80)
        
        return error_count == 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    print("🔧 Fixing image filenames...")
    print("="*80)
    success = fix_image_filenames()
    sys.exit(0 if success else 1)
