#!/usr/bin/env python3
"""
Migrate existing images to hierarchical structure:
/generated_images/{book_id}/covers/
/generated_images/{book_id}/chapters/
"""

import os
import shutil
import re
from pathlib import Path

def migrate_images():
    """Reorganize images into proper hierarchical structure"""
    
    base_dir = Path("generated_images")
    if not base_dir.exists():
        print("No generated_images directory found")
        return
    
    # Track migrations
    migrated = 0
    skipped = 0
    errors = 0
    
    # First, handle any loose files in the root
    for file in base_dir.glob("*.png"):
        try:
            filename = file.name
            
            # Parse filename to determine book_id and type
            # Patterns: adaptation_X_chapter_Y_*.png, cover_adaptation_X.png
            
            if filename.startswith("cover_adaptation_"):
                # Cover image: cover_adaptation_1.png
                match = re.search(r"cover_adaptation_(\d+)", filename)
                if match:
                    adaptation_id = match.group(1)
                    # For now, put in orphaned/covers since we don't know book_id
                    target_dir = base_dir / "orphaned" / "covers"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / filename
                    
                    if not target_path.exists():
                        shutil.move(str(file), str(target_path))
                        print(f"Moved cover: {filename} -> orphaned/covers/")
                        migrated += 1
                    else:
                        print(f"Skip existing: {filename}")
                        skipped += 1
                        
            elif "chapter" in filename:
                # Chapter image: adaptation_X_chapter_Y_*.png
                match = re.search(r"adaptation_(\d+)_chapter_(\d+)", filename)
                if match:
                    adaptation_id = match.group(1)
                    chapter_num = match.group(2)
                    # For now, put in orphaned/chapters since we don't know book_id
                    target_dir = base_dir / "orphaned" / "chapters"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / filename
                    
                    if not target_path.exists():
                        shutil.move(str(file), str(target_path))
                        print(f"Moved chapter: {filename} -> orphaned/chapters/")
                        migrated += 1
                    else:
                        print(f"Skip existing: {filename}")
                        skipped += 1
            else:
                print(f"Unknown pattern: {filename}")
                skipped += 1
                
        except Exception as e:
            print(f"Error processing {file}: {e}")
            errors += 1
    
    # Now handle existing book directories (numeric directories)
    for book_dir in base_dir.iterdir():
        if not book_dir.is_dir():
            continue
            
        # Skip our new structure directories
        if book_dir.name in ["covers", "chapters", "orphaned"]:
            continue
            
        # Check if it's a numeric book ID
        if not book_dir.name.isdigit():
            print(f"Skipping non-numeric directory: {book_dir.name}")
            continue
            
        book_id = book_dir.name
        print(f"\nProcessing book {book_id} directory...")
        
        # Create new structure
        covers_dir = book_dir / "covers"
        chapters_dir = book_dir / "chapters"
        covers_dir.mkdir(exist_ok=True)
        chapters_dir.mkdir(exist_ok=True)
        
        # Move files into appropriate subdirectories
        for file in book_dir.glob("*.png"):
            try:
                filename = file.name
                
                if filename.startswith("cover_"):
                    # Move to covers directory
                    target_path = covers_dir / filename
                    if not target_path.exists():
                        shutil.move(str(file), str(target_path))
                        print(f"  Moved: {filename} -> covers/")
                        migrated += 1
                    else:
                        print(f"  Skip existing: {filename}")
                        skipped += 1
                        
                elif "chapter" in filename:
                    # Move to chapters directory
                    target_path = chapters_dir / filename
                    if not target_path.exists():
                        shutil.move(str(file), str(target_path))
                        print(f"  Moved: {filename} -> chapters/")
                        migrated += 1
                    else:
                        print(f"  Skip existing: {filename}")
                        skipped += 1
                else:
                    # Unknown pattern, move to chapters by default
                    target_path = chapters_dir / filename
                    if not target_path.exists():
                        shutil.move(str(file), str(target_path))
                        print(f"  Moved (default): {filename} -> chapters/")
                        migrated += 1
                    else:
                        print(f"  Skip existing: {filename}")
                        skipped += 1
                        
            except Exception as e:
                print(f"  Error processing {file}: {e}")
                errors += 1
    
    # Clean up old empty directories
    for dir_name in ["covers", "chapters"]:
        old_dir = base_dir / dir_name
        if old_dir.exists() and old_dir.is_dir():
            try:
                # Only remove if empty
                if not any(old_dir.iterdir()):
                    old_dir.rmdir()
                    print(f"\nRemoved empty directory: {dir_name}")
            except Exception as e:
                print(f"Could not remove {dir_name}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Migration Complete!")
    print(f"  Migrated: {migrated} files")
    print(f"  Skipped:  {skipped} files")
    print(f"  Errors:   {errors}")
    print(f"{'='*50}")

if __name__ == "__main__":
    migrate_images()