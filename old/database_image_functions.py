"""
Additional database functions for individual image management
These functions should be added to database.py
"""

import psycopg2
from typing import Optional, Dict, Any, List
import config

async def get_chapter_details(chapter_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a specific chapter"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    adaptation_id,
                    chapter_number,
                    original_chapter_text,
                    transformed_chapter_text,
                    ai_generated_image_prompt,
                    user_edited_image_prompt,
                    image_url,
                    status,
                    created_at,
                    updated_at
                FROM chapters 
                WHERE id = %s
            """, (chapter_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'adaptation_id': row[1],
                    'chapter_number': row[2],
                    'original_chapter_text': row[3],
                    'transformed_chapter_text': row[4],
                    'ai_generated_image_prompt': row[5],
                    'user_edited_image_prompt': row[6],
                    'image_url': row[7],
                    'status': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }
            return None
            
    except Exception as e:
        print(f"❌ Error getting chapter details: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

async def update_chapter_image_prompt(chapter_id: int, prompt: str) -> bool:
    """Update the image prompt for a chapter"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE chapters 
                SET user_edited_image_prompt = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (prompt, chapter_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
    except Exception as e:
        print(f"❌ Error updating chapter image prompt: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def update_chapter_image_url(chapter_id: int, image_url: Optional[str]) -> bool:
    """Update the image URL for a chapter"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE chapters 
                SET image_url = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (image_url, chapter_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
    except Exception as e:
        print(f"❌ Error updating chapter image URL: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def update_chapter_status(chapter_id: int, status: str) -> bool:
    """Update the status of a chapter"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE chapters 
                SET status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, chapter_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
    except Exception as e:
        print(f"❌ Error updating chapter status: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def update_adaptation_cover_prompt(adaptation_id: int, prompt: str) -> bool:
    """Update the cover image prompt for an adaptation"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE adaptations 
                SET cover_image_prompt = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (prompt, adaptation_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
    except Exception as e:
        print(f"❌ Error updating adaptation cover prompt: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def update_adaptation_cover_image(adaptation_id: int, prompt: str, image_url: str) -> bool:
    """Update both cover prompt and image URL for an adaptation"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE adaptations 
                SET cover_image_prompt = %s,
                    cover_image_url = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (prompt, image_url, adaptation_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
    except Exception as e:
        print(f"❌ Error updating adaptation cover image: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

async def get_adaptation_chapters(adaptation_id: int) -> List[Dict[str, Any]]:
    """Get all chapters for an adaptation with their details"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    adaptation_id,
                    chapter_number,
                    original_chapter_text,
                    transformed_chapter_text,
                    ai_generated_image_prompt,
                    user_edited_image_prompt,
                    image_url,
                    status,
                    created_at,
                    updated_at
                FROM chapters 
                WHERE adaptation_id = %s
                ORDER BY chapter_number
            """, (adaptation_id,))
            
            rows = cursor.fetchall()
            chapters = []
            
            for row in rows:
                chapters.append({
                    'id': row[0],
                    'adaptation_id': row[1],
                    'chapter_number': row[2],
                    'original_chapter_text': row[3],
                    'transformed_chapter_text': row[4],
                    'ai_generated_image_prompt': row[5],
                    'user_edited_image_prompt': row[6],
                    'image_url': row[7],
                    'status': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                })
            
            return chapters
            
    except Exception as e:
        print(f"❌ Error getting adaptation chapters: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

async def get_adaptation_details(adaptation_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about an adaptation"""
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DATABASE_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    book_id,
                    title,
                    target_age_group,
                    transformation_style,
                    overall_theme_tone,
                    key_characters_to_preserve,
                    preserve_original_chapters,
                    cover_image_prompt,
                    cover_image_url,
                    status,
                    created_at,
                    updated_at
                FROM adaptations 
                WHERE id = %s
            """, (adaptation_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'book_id': row[1],
                    'title': row[2],
                    'target_age_group': row[3],
                    'transformation_style': row[4],
                    'overall_theme_tone': row[5],
                    'key_characters_to_preserve': row[6],
                    'preserve_original_chapters': row[7],
                    'cover_image_prompt': row[8],
                    'cover_image_url': row[9],
                    'status': row[10],
                    'created_at': row[11],
                    'updated_at': row[12]
                }
            return None
            
    except Exception as e:
        print(f"❌ Error getting adaptation details: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

# Add these functions to your existing database.py file
