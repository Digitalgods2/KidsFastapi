"""
Complete Database operations for KidsKlassiks FastAPI
Based on app5.py with ALL functions that routes actually import
This is the final, complete version with every function needed
"""

import sqlite3
import asyncio
import os
import json
import shutil
import uuid
import re
from typing import List, Dict, Optional, Any
from datetime import datetime

# Support SQLAlchemy-style SQLite URLs via env (DATABASE_URL or SQLITE_URL)
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SQLITE_URL") or ""

# Project root is the directory of this file to avoid CWD drift across restarts
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# Ensure an event loop exists (Py3.12 get_event_loop behavior)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


def _forward_slashes(p: str) -> str:
    return p.replace("\\", "/")


def _resolve_sqlite_path() -> str:
    url = (DATABASE_URL or "").strip()
    default_abs = os.path.join(PROJECT_ROOT, "kidsklassiks.db")
    if not url:
        return default_abs
    if url.startswith("sqlite:////"):
        # Absolute path form: sqlite:////full/path/to.db
        return "/" + url[len("sqlite:////"):]
    if url.startswith("sqlite:///"):
        # Relative path form: sqlite:///./kidsklassiks.db
        rel = url[len("sqlite:///"):]
        return os.path.abspath(rel)
    # Fallback: treat as file path
    return os.path.abspath(url)

DATABASE_PATH = _resolve_sqlite_path()

# Expose a stable, sanitized URL for debugging and routing layers
RESOLVED_DATABASE_URL = (
    (DATABASE_URL.strip() if DATABASE_URL else f"sqlite:////{_forward_slashes(DATABASE_PATH)}")
)


def get_sqlite_path() -> str:
    return DATABASE_PATH


def get_database_url() -> str:
    return RESOLVED_DATABASE_URL


def get_database_debug() -> dict:
    try:
        exists = os.path.exists(DATABASE_PATH)
        size = os.path.getsize(DATABASE_PATH) if exists else 0
    except Exception:
        exists, size = False, 0
    return {
        "database_url": get_database_url(),
        "absolute_path": DATABASE_PATH,
        "exists": bool(exists),
        "size_bytes": int(size),
        "cwd": os.getcwd(),
    }

class DatabaseManager:
    """Database manager matching app5.py functionality"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database if it doesn't exist"""
        if not os.path.exists(self.db_path):
            self._create_database()
    
    def _create_database(self):
        """Create database with schema matching app5.py + run tracking tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Books table (matches app5.py schema)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    source_type TEXT DEFAULT 'upload',
                    path TEXT,
                    character_reference TEXT,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Adaptations table (matches app5.py schema)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adaptations (
                    adaptation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    target_age_group TEXT NOT NULL,
                    transformation_style TEXT NOT NULL,
                    overall_theme_tone TEXT,
                    key_characters_to_preserve TEXT,
                    chapter_structure_choice TEXT,
                    cover_prompt TEXT,
                    cover_url TEXT,
                    status TEXT DEFAULT 'created',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books (book_id)
                )
            ''')
            
            # Chapters table (matches app5.py schema)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    chapter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    adaptation_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    original_text_segment TEXT,
                    transformed_text TEXT,
                    ai_prompt TEXT,
                    user_prompt TEXT,
                    image_url TEXT,
                    status TEXT DEFAULT 'created',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
                )
            ''')

            # Run tracking for chapter processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adaptation_runs (
                    run_id TEXT PRIMARY KEY,
                    adaptation_id INTEGER NOT NULL,
                    detected_count INTEGER DEFAULT 0,
                    target_count INTEGER DEFAULT 0,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    operations TEXT,
                    final_map TEXT,
                    status TEXT,
                    error TEXT,
                    meta TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_runs (
                    adaptation_id INTEGER PRIMARY KEY,
                    run_id TEXT,
                    stage TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
                )
            ''')

            # Simple advisory locks for processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adaptation_locks (
                    adaptation_id INTEGER PRIMARY KEY,
                    holder TEXT,
                    acquired_at TEXT,
                    FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
                )
            ''')
            
            # Settings table for application configuration
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            print("✅ Database created successfully")
            
        except Exception as e:
            print(f"❌ Database creation failed: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_connection(self):
        """Get database connection with WAL mode enabled"""
        # Ensure SQLite allows cross-thread usage (FastAPI background tasks & reloads)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
        except Exception:
            pass
        return conn

# Global database manager

# --- Book analysis update helper (used by routes/books.py) ---
async def update_book_analysis(book_id: int, word_count: int | None = None, chapter_count: int | None = None, unique_characters: list[str] | str | None = None) -> bool:
    """Update analysis data on books.character_reference as JSON.
    Accepts optional word_count, chapter_count, and unique_characters (list or comma-separated string).
    """
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT character_reference FROM books WHERE book_id = ?', (book_id,))
        row = cursor.fetchone()
        ref = {}
        if row and row[0]:
            try:
                ref = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except Exception:
                ref = {"raw": row[0]}
        if word_count is not None:
            ref["word_count"] = int(word_count)
        if chapter_count is not None:
            ref["chapter_count"] = int(chapter_count)
        if unique_characters is not None:
            if isinstance(unique_characters, str):
                parts = [p.strip() for p in unique_characters.split(',') if p.strip()]
                ref["unique_characters"] = parts
            elif isinstance(unique_characters, list):
                ref["unique_characters"] = unique_characters
        cursor.execute('UPDATE books SET character_reference = ? WHERE book_id = ?', (json.dumps(ref), book_id))
        conn.commit()
        return True
    finally:
        conn.close()

def ensure_aux_tables():
    """Create any auxiliary tables that may be missing in existing DBs."""
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_runs (
                run_id TEXT PRIMARY KEY,
                adaptation_id INTEGER NOT NULL,
                detected_count INTEGER DEFAULT 0,
                target_count INTEGER DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                duration_ms INTEGER,
                operations TEXT,
                final_map TEXT,
                status TEXT,
                error TEXT,
                meta TEXT,
                updated_at TEXT,
                FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS active_runs (
                adaptation_id INTEGER PRIMARY KEY,
                run_id TEXT,
                stage TEXT,
                updated_at TEXT,
                FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_locks (
                adaptation_id INTEGER PRIMARY KEY,
                holder TEXT,
                acquired_at TEXT,
                FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def ensure_aux_tables():
    """Create any auxiliary tables that may be missing in existing DBs."""
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_runs (
                run_id TEXT PRIMARY KEY,
                adaptation_id INTEGER NOT NULL,
                detected_count INTEGER DEFAULT 0,
                target_count INTEGER DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                duration_ms INTEGER,
                operations TEXT,
                final_map TEXT,
                status TEXT,
                error TEXT,
                meta TEXT,
                updated_at TEXT,
                FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS active_runs (
                adaptation_id INTEGER PRIMARY KEY,
                run_id TEXT,
                stage TEXT,
                updated_at TEXT,
                FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_locks (
                adaptation_id INTEGER PRIMARY KEY,
                holder TEXT,
                acquired_at TEXT,
                FOREIGN KEY (adaptation_id) REFERENCES adaptations (adaptation_id)
            )
        ''')
        conn.commit()
    finally:
        conn.close()

db_manager = DatabaseManager()

def initialize_database():
    """Initialize the database and ensure schema exists"""
    db_manager._ensure_database_exists()
    # Ensure settings table exists (migration for existing databases)
    ensure_settings_table()
    print("✅ Database initialized")

def ensure_settings_table():
    """Ensure settings table exists - can be run on existing databases"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        print("✅ Settings table ensured")
    except Exception as e:
        print(f"❌ Settings table creation failed: {e}")
        conn.rollback()
    finally:
        conn.close()

# Compat: expose a simple connection getter expected by some routes
# Returns a new sqlite3 connection. Caller should close it.

def get_db_connection():
    return db_manager.get_connection()

# High-level book import used by routes
async def import_book(title: str, author: str, content: str, source_type: str) -> Optional[int]:
    """High-level import used by routes.
    Writes content to disk under ./uploads and stores the file path in DB.
    """
    # Ensure uploads directory exists
    uploads_dir = os.path.abspath(os.path.join(os.getcwd(), 'uploads'))
    os.makedirs(uploads_dir, exist_ok=True)

    # Build a safe filename
    def _slugify(text: str) -> str:
        t = (text or '').strip()
        t = re.sub(r'[^A-Za-z0-9\-_. ]+', '', t)
        t = t.replace(' ', '_')
        return t[:80] or 'book'

    base = _slugify(title) if title else 'book'
    unique = uuid.uuid4().hex[:8]
    filename = f"{base}_{unique}.txt"
    file_path = os.path.join(uploads_dir, filename)

    # Write content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content or '')
    except Exception:
        # Fallback to latin-1 if unusual encoding edge case
        with open(file_path, 'w', encoding='latin-1') as f:
            f.write((content or '').encode('latin-1', errors='ignore').decode('latin-1'))

    # Store record in DB
    book_id = await import_book_to_db(title, author, source_type, file_path)
    # ensure per-book generated_images directory like legacy tests expect
    try:
        if book_id:
            os.makedirs(os.path.join('generated_images', str(book_id)), exist_ok=True)
    except Exception:
        pass
    return book_id



# Repair helper: backfill file path when content was mistakenly stored in source_type
async def repair_book_file_path(book_id: int) -> Optional[str]:
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT title, author, source_type, path FROM books WHERE book_id = ?', (book_id,))
        row = cursor.fetchone()
        if not row:
            return None
        title, author, source_type, path = row
        # If path looks valid and exists, nothing to do
        if path and isinstance(path, str) and os.path.exists(path):
            return path
        # If source_type contains the original content incorrectly, write it to disk
        content_candidate = None
        if isinstance(source_type, str) and (('\n' in source_type) or len(source_type) > 1000):
            content_candidate = source_type
        # If author was polluted with content (rare case), detect and use
        if not content_candidate and isinstance(author, str) and (('\n' in author) or len(author) > 1000):
            content_candidate = author
        if not content_candidate:
            # Cannot repair automatically
            return None
        uploads_dir = os.path.abspath(os.path.join(os.getcwd(), 'uploads'))
        os.makedirs(uploads_dir, exist_ok=True)
        base = re.sub(r'[^A-Za-z0-9\-_. ]+', '', (title or 'book')).strip().replace(' ', '_') or 'book'
        file_path = os.path.join(uploads_dir, f"{base}_{uuid.uuid4().hex[:8]}.txt")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_candidate)
        except Exception:
            with open(file_path, 'w', encoding='latin-1') as f:
                f.write(content_candidate.encode('latin-1', errors='ignore').decode('latin-1'))
        # Update DB: set proper path and correct source_type to 'upload' if it held content
        new_source_type = 'upload'
        cursor.execute('UPDATE books SET path = ?, source_type = ? WHERE book_id = ?', (file_path, new_source_type, book_id))
        conn.commit()
        return file_path
    finally:
        conn.close()

async def repair_all_book_paths() -> int:
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT book_id FROM books')
        ids = [r[0] for r in cursor.fetchall()]
    finally:
        conn.close()
    fixed = 0
    for bid in ids:
        p = await repair_book_file_path(bid)
        if p:
            fixed += 1
    return fixed

    db_manager._ensure_database_exists()
    print("✅ Database initialized")

# ==================== BOOK OPERATIONS ====================

async def import_book_to_db(title: str, author: str, source_type: str, path: str) -> Optional[int]:
    """Import book to database - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO books (title, author, source_type, path)
            VALUES (?, ?, ?, ?)
        ''', (title, author, source_type, path))
        
        book_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Imported book: {title}")
        return book_id
        
    except Exception as e:
        print(f"❌ Book import failed: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

async def get_all_books() -> List[Dict]:
    """Get all books - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT book_id, title, author, source_type, path, character_reference, imported_at
            FROM books
            ORDER BY imported_at DESC
        ''')
        
        books = []
        for row in cursor.fetchall():
            item = {
                "book_id": row[0],
                "title": row[1],
                "author": row[2],
                "source_type": row[3],
                "path": row[4],
                "imported_at": row[6]
            }
            # Parse analysis from character_reference JSON if present
            ref = row[5]
            if ref:
                try:
                    data = json.loads(ref) if isinstance(ref, str) else ref
                    if isinstance(data, dict):
                        if "word_count" in data:
                            item["word_count"] = int(data.get("word_count") or 0)
                        if "chapter_count" in data:
                            item["chapter_count"] = int(data.get("chapter_count") or 0)
                        if "unique_characters" in data:
                            item["unique_characters"] = data.get("unique_characters")
                except Exception:
                    pass
            books.append(item)
        
        return books
    finally:
        conn.close()

async def get_all_books_with_adaptations() -> List[Dict]:
    """Get all books with adaptation counts and adaptation details"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # First get all books with counts
        cursor.execute('''
            SELECT 
                b.book_id,
                b.title,
                b.author,
                b.source_type,
                b.imported_at,
                COUNT(a.adaptation_id) as adaptation_count
            FROM books b
            LEFT JOIN adaptations a ON b.book_id = a.book_id
            GROUP BY b.book_id, b.title, b.author, b.source_type, b.imported_at
            ORDER BY b.imported_at DESC
        ''')
        
        books = []
        for row in cursor.fetchall():
            book_id = row[0]
            book = {
                "book_id": book_id,
                "title": row[1],
                "author": row[2],
                "source_type": row[3],
                "imported_at": row[4],
                "adaptation_count": row[5],
                "adaptations": []
            }
            
            # Get adaptations for this book
            if row[5] > 0:  # If adaptation_count > 0
                cursor.execute('''
                    SELECT adaptation_id, target_age_group, transformation_style, 
                           overall_theme_tone, status, created_at
                    FROM adaptations WHERE book_id = ?
                    ORDER BY created_at DESC
                ''', (book_id,))
                
                for adapt_row in cursor.fetchall():
                    book["adaptations"].append({
                        "adaptation_id": adapt_row[0],
                        "target_age_group": adapt_row[1],
                        "transformation_style": adapt_row[2],
                        "overall_theme_tone": adapt_row[3],
                        "status": adapt_row[4],
                        "created_at": adapt_row[5]
                    })
            
            books.append(book)
        
        return books
    finally:
        conn.close()

async def get_book_details(book_id: int) -> Optional[Dict]:
    """Get book details - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT book_id, title, author, source_type, path, character_reference, imported_at
            FROM books WHERE book_id = ?
        ''', (book_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "book_id": row[0],
                "title": row[1],
                "author": row[2],
                "source_type": row[3],
                "path": row[4],
                "character_reference": row[5],
                "imported_at": row[6]
            }
        return None
    finally:
        conn.close()

async def update_book_details(book_id: int, title: str, author: str) -> bool:
    """Update book details - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE books SET title = ?, author = ? WHERE book_id = ?
        ''', (title, author, book_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Book update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_book_character_reference(book_id: int, character_reference: str) -> bool:
    """Update book character reference"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE books SET character_reference = ? WHERE book_id = ?
        ''', (character_reference, book_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Character reference update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def delete_book_from_db(book_id: int) -> bool:
    """Delete book and all related records and files.
    - Deletes chapters, adaptations, runs, locks
    - Removes uploads file for the book
    - Removes generated_images/{book_id}
    """
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Capture upload file path before deleting
        cursor.execute('SELECT path FROM books WHERE book_id = ?', (book_id,))
        row = cursor.fetchone()
        upload_path = row[0] if row else None

        # Identify adaptation ids for this book
        cursor.execute('SELECT adaptation_id FROM adaptations WHERE book_id = ?', (book_id,))
        adap_ids = [r[0] for r in cursor.fetchall()]

        # Delete run tracking and locks for these adaptations
        if adap_ids:
            qmarks = ','.join(['?'] * len(adap_ids))
            cursor.execute(f'DELETE FROM adaptation_runs WHERE adaptation_id IN ({qmarks})', adap_ids)
            cursor.execute(f'DELETE FROM active_runs WHERE adaptation_id IN ({qmarks})', adap_ids)
            cursor.execute(f'DELETE FROM adaptation_locks WHERE adaptation_id IN ({qmarks})', adap_ids)

        # Delete chapters first
        cursor.execute('''
            DELETE FROM chapters 
            WHERE adaptation_id IN (
                SELECT adaptation_id FROM adaptations WHERE book_id = ?
            )
        ''', (book_id,))
        
        # Delete adaptations
        cursor.execute('DELETE FROM adaptations WHERE book_id = ?', (book_id,))
        
        # Delete book
        cursor.execute('DELETE FROM books WHERE book_id = ?', (book_id,))
        
        conn.commit()

        # Remove per-book folder under generated_images if exists
        try:
            import shutil as _sh
            _dir = os.path.join('generated_images', str(book_id))
            if os.path.isdir(_dir):
                _sh.rmtree(_dir)
        except Exception:
            pass

        # Remove upload file if exists
        try:
            if upload_path and os.path.isfile(upload_path):
                os.remove(upload_path)
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"❌ Book deletion failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def delete_book_completely(book_id: int) -> bool:
    """Compatibility wrapper expected by tests: remove DB records and per-book folder."""
    ok = await delete_book_from_db(book_id)
    # Folder removal already attempted in delete_book_from_db; ensure again just in case
    try:
        import shutil as _sh
        _dir = os.path.join('generated_images', str(book_id))
        if os.path.isdir(_dir):
            _sh.rmtree(_dir)
    except Exception:
        pass
    return ok

# ==================== ADAPTATION OPERATIONS ====================

async def create_adaptation_record(
    book_id: int,
    target_age_group: str,
    transformation_style: str,
    overall_theme_tone: str,
    key_characters_to_preserve: str,
    chapter_structure_choice: str = None
) -> Optional[int]:
    """Create adaptation record - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO adaptations (
                book_id, target_age_group, transformation_style,
                overall_theme_tone, key_characters_to_preserve, chapter_structure_choice
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (book_id, target_age_group, transformation_style, 
              overall_theme_tone, key_characters_to_preserve, chapter_structure_choice))
        
        adaptation_id = cursor.lastrowid
        conn.commit()
        
        print(f"✅ Created adaptation {adaptation_id} for book {book_id}")
        return adaptation_id
        
    except Exception as e:
        print(f"❌ Adaptation creation failed: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

async def get_adaptation_details(adaptation_id: int) -> Optional[Dict]:
    """Get adaptation details - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                a.adaptation_id, a.book_id, a.target_age_group, a.transformation_style,
                a.overall_theme_tone, a.key_characters_to_preserve, a.chapter_structure_choice,
                a.cover_prompt, a.cover_url, a.status, a.created_at,
                b.title, b.author
            FROM adaptations a
            JOIN books b ON a.book_id = b.book_id
            WHERE a.adaptation_id = ?
        ''', (adaptation_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "adaptation_id": row[0],
                "book_id": row[1],
                "target_age_group": row[2],
                "transformation_style": row[3],
                "overall_theme_tone": row[4],
                "key_characters_to_preserve": row[5],
                "chapter_structure_choice": row[6],
                "cover_prompt": row[7],
                "cover_url": row[8],
                "status": row[9],
                "created_at": row[10],
                "book_title": row[11],
                "book_author": row[12]
            }
        return None
    finally:
        conn.close()

async def get_adaptations_for_book(book_id: int) -> List[Dict]:
    """Get all adaptations for a book - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT adaptation_id, target_age_group, transformation_style, 
                   overall_theme_tone, status, created_at
            FROM adaptations WHERE book_id = ?
            ORDER BY created_at DESC
        ''', (book_id,))
        
        adaptations = []
        for row in cursor.fetchall():
            adaptations.append({
                "adaptation_id": row[0],
                "target_age_group": row[1],
                "transformation_style": row[2],
                "overall_theme_tone": row[3],
                "status": row[4],
                "created_at": row[5]
            })
        
        return adaptations
    finally:
        conn.close()

async def get_all_adaptations() -> List[Dict]:
    """Get all adaptations with book details - used by adaptations list page"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                a.adaptation_id, a.book_id, a.target_age_group, a.transformation_style,
                a.overall_theme_tone, a.key_characters_to_preserve, a.chapter_structure_choice,
                a.cover_prompt, a.cover_url, a.status, a.created_at,
                b.title, b.author
            FROM adaptations a
            JOIN books b ON a.book_id = b.book_id
            ORDER BY a.created_at DESC
        ''')
        
        adaptations = []
        for row in cursor.fetchall():
            adaptations.append({
                "adaptation_id": row[0],
                "book_id": row[1],
                "target_age_group": row[2],
                "transformation_style": row[3],
                "overall_theme_tone": row[4],
                "key_characters_to_preserve": row[5],
                "chapter_structure_choice": row[6],
                "cover_prompt": row[7],
                "cover_url": row[8],
                "status": row[9],
                "created_at": row[10],
                "book_title": row[11],
                "book_author": row[12]
            })
        
        return adaptations
    finally:
        conn.close()

async def get_all_adaptations_with_stats() -> List[Dict]:
    """Get all adaptations with book details AND content statistics - used by publish page"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT 
                a.adaptation_id, a.book_id, a.target_age_group, a.transformation_style,
                a.overall_theme_tone, a.key_characters_to_preserve, a.chapter_structure_choice,
                a.cover_prompt, a.cover_url, a.status, a.created_at,
                b.title, b.author,
                COUNT(DISTINCT c.chapter_id) as chapter_count,
                SUM(CASE WHEN c.image_url IS NOT NULL AND c.image_url != '' THEN 1 ELSE 0 END) as image_count,
                SUM(CASE 
                    WHEN c.transformed_text IS NOT NULL AND LENGTH(c.transformed_text) > 0 
                    THEN LENGTH(c.transformed_text)
                    WHEN c.original_text_segment IS NOT NULL 
                    THEN LENGTH(c.original_text_segment)
                    ELSE 0
                END) as total_chars
            FROM adaptations a
            JOIN books b ON a.book_id = b.book_id
            LEFT JOIN chapters c ON a.adaptation_id = c.adaptation_id
            GROUP BY a.adaptation_id
            ORDER BY a.created_at DESC
        ''')
        
        adaptations = []
        for row in cursor.fetchall():
            total_chars = row[15] or 0
            word_count = max(1, total_chars // 5) if total_chars > 0 else 0  # Rough estimate: avg 5 chars per word
            
            adaptations.append({
                "adaptation_id": row[0],
                "book_id": row[1],
                "target_age_group": row[2],
                "transformation_style": row[3],
                "overall_theme_tone": row[4],
                "key_characters_to_preserve": row[5],
                "chapter_structure_choice": row[6],
                "cover_prompt": row[7],
                "cover_url": row[8],
                "status": row[9],
                "created_at": row[10],
                "book_title": row[11],
                "book_author": row[12],
                "chapter_count": row[13],
                "image_count": row[14],
                "total_chars": total_chars,
                "word_count": word_count
            })
        
        return adaptations
    finally:
        conn.close()

async def delete_adaptation_from_db(adaptation_id: int) -> bool:
    """Delete adaptation and chapters - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete chapters first
        cursor.execute('DELETE FROM chapters WHERE adaptation_id = ?', (adaptation_id,))
        
        # Delete adaptation
        cursor.execute('DELETE FROM adaptations WHERE adaptation_id = ?', (adaptation_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Adaptation deletion failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def save_cover_prompt(adaptation_id: int, cover_prompt: str) -> bool:
    """Save cover prompt for adaptation"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE adaptations 
            SET cover_prompt = ?
            WHERE adaptation_id = ?
        ''', (cover_prompt, adaptation_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Cover prompt save failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_adaptation_status(adaptation_id: int, status: str) -> bool:
    """Update adaptation status"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE adaptations 
            SET status = ?
            WHERE adaptation_id = ?
        ''', (status, adaptation_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Status update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_adaptation_cover_image(adaptation_id: int, cover_prompt: str, cover_url: str) -> bool:
    """Update adaptation cover - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE adaptations 
            SET cover_prompt = ?, cover_url = ?
            WHERE adaptation_id = ?
        ''', (cover_prompt, cover_url, adaptation_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Cover update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_adaptation_cover_image_prompt_only(adaptation_id: int, cover_prompt: str) -> bool:
    """Update adaptation cover prompt only - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE adaptations 
            SET cover_prompt = ?
            WHERE adaptation_id = ?
        ''', (cover_prompt, adaptation_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Cover prompt update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ==================== CHAPTER OPERATIONS ====================

async def save_chapter_data(
    adaptation_id: int,
    chapter_number: int,
    original_text_segment: str,
    transformed_text: str,
    ai_prompt: str,
    user_prompt: str,
    image_url: str = None,
    status: str = "created"
) -> Optional[int]:
    """Save chapter data - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO chapters (
                adaptation_id, chapter_number, original_text_segment, 
                transformed_text, ai_prompt, user_prompt, image_url, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (adaptation_id, chapter_number, original_text_segment, 
              transformed_text, ai_prompt, user_prompt, image_url, status))
        
        chapter_id = cursor.lastrowid
        conn.commit()
        return chapter_id
        
    except Exception as e:
        print(f"❌ Chapter save failed: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

async def get_chapters_for_adaptation(adaptation_id: int) -> List[Dict]:
    """Get chapters for adaptation - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT chapter_id, chapter_number, original_text_segment, transformed_text, 
                   ai_prompt, user_prompt, image_url, status, created_at
            FROM chapters 
            WHERE adaptation_id = ?
            ORDER BY chapter_number
        ''', (adaptation_id,))
        chapters = []
        for row in cursor.fetchall():
            chapters.append({
                "chapter_id": row[0],
                "chapter_number": row[1],
                "original_text_segment": row[2],
                "transformed_text": row[3],
                "ai_prompt": row[4],
                "user_prompt": row[5],
                "image_url": row[6],
                "status": row[7],
                "created_at": row[8]
            })
        return chapters
    finally:
        conn.close()

async def replace_adaptation_chapters(adaptation_id: int, segments: list[str]) -> bool:
    """Replace all chapters for an adaptation with the given list of text segments in a single transaction.
    Keeps chapter_number sequential starting at 1; clears image_url and prompts.
    """
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM chapters WHERE adaptation_id = ?', (adaptation_id,))
        for i, seg in enumerate(segments, start=1):
            cur.execute('''
                INSERT INTO chapters (adaptation_id, chapter_number, original_text_segment, transformed_text, ai_prompt, user_prompt, image_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (adaptation_id, i, seg, '', '', '', None, 'created'))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ replace_adaptation_chapters failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# --- Active run coordination (used by process_chapters and status) ---
_current_runs = {}

async def upsert_active_run(adaptation_id: int, run_id: str, stage: str = 'running'):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        ts = datetime.utcnow().isoformat() + 'Z'
        cur.execute('REPLACE INTO active_runs (adaptation_id, run_id, stage, updated_at) VALUES (?, ?, ?, ?)', (adaptation_id, run_id, stage, ts))
        conn.commit()
        _current_runs[adaptation_id] = run_id
        return True
    finally:
        conn.close()

async def get_active_run(adaptation_id: int):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT run_id, stage, updated_at FROM active_runs WHERE adaptation_id = ?', (adaptation_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {"run_id": row[0], "stage": row[1], "updated_at": row[2]}
    finally:
        conn.close()

async def clear_active_run(adaptation_id: int):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM active_runs WHERE adaptation_id = ?', (adaptation_id,))
        conn.commit()
        _current_runs.pop(adaptation_id, None)
        return True
    finally:
        conn.close()

# In-memory helper for quick holder lookup

# --- Run lifecycle persistence ---
async def create_adaptation_run(adaptation_id: int, run_id: str, detected_count: int, target_count: int, started_at):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('INSERT OR REPLACE INTO adaptation_runs (run_id, adaptation_id, detected_count, target_count, started_at, status, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (run_id, adaptation_id, int(detected_count), int(target_count), (started_at.isoformat()+"Z") if hasattr(started_at, 'isoformat') else str(started_at), 'running', datetime.utcnow().isoformat()+"Z"))
        conn.commit()
        await upsert_active_run(adaptation_id, run_id, stage='normalizing')
        return True
    finally:
        conn.close()

async def finish_adaptation_run(run_id: str, finished_at, duration_ms: int, operations: list, final_map: list, status: str = 'succeeded', error: Optional[str] = None, meta: Optional[dict] = None):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE adaptation_runs SET finished_at = ?, duration_ms = ?, operations = ?, final_map = ?, status = ?, error = ?, meta = ?, updated_at = ? WHERE run_id = ?',
            ((finished_at.isoformat()+"Z") if hasattr(finished_at, 'isoformat') else str(finished_at), int(duration_ms), json.dumps(operations or []), json.dumps(final_map or []), status, error, json.dumps(meta or {}), datetime.utcnow().isoformat()+"Z", run_id))
        conn.commit()
        # clear active run by adaptation id
        cur.execute('SELECT adaptation_id FROM adaptation_runs WHERE run_id = ?', (run_id,))
        row = cur.fetchone()
        if row:
            await clear_active_run(row[0])

        return True
    finally:
        conn.close()

async def get_chapter_details(chapter_id: int) -> Optional[Dict]:
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT chapter_id, adaptation_id, chapter_number, original_text_segment, transformed_text,
                   ai_prompt, user_prompt, image_url, status, created_at
            FROM chapters WHERE chapter_id = ?
        ''', (chapter_id,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            'chapter_id': row[0],
            'adaptation_id': row[1],
            'chapter_number': row[2],
            'original_text_segment': row[3],
            'transformed_text': row[4],
            'ai_prompt': row[5],
            'user_prompt': row[6],
            'image_url': row[7],
            'status': row[8],
            'created_at': row[9],
        }
    finally:
        conn.close()

async def update_chapter_image(chapter_id: int, image_url: str, image_prompt: Optional[str] = None) -> bool:
    """Compatibility wrapper: update image_url and optionally store prompt in ai_prompt."""
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        if image_prompt is not None:
            cur.execute('UPDATE chapters SET image_url = ?, ai_prompt = ? WHERE chapter_id = ?', (image_url, image_prompt, chapter_id))
        else:
            cur.execute('UPDATE chapters SET image_url = ? WHERE chapter_id = ?', (image_url, chapter_id))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"❌ Chapter image update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def remove_chapter_image(chapter_id: int) -> bool:
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE chapters SET image_url = NULL WHERE chapter_id = ?', (chapter_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"❌ Remove chapter image failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_adaptation_cover(adaptation_id: int, cover_image_url: str, cover_image_prompt: Optional[str] = None) -> bool:
    """Compatibility wrapper for routes.images expected signature."""
    if cover_image_prompt is None:
        return await update_adaptation_cover_image(adaptation_id, '', cover_image_url)
    return await update_adaptation_cover_image(adaptation_id, cover_image_prompt, cover_image_url)

async def get_generated_images() -> List[Dict]:
    """Return simple list of generated images across chapters for gallery."""
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT c.chapter_id, c.chapter_number, c.adaptation_id, c.image_url, c.ai_prompt, c.created_at,
                   a.book_id, a.target_age_group, a.transformation_style, a.created_at AS adaptation_created,
                   b.title AS book_title, b.author AS book_author, b.imported_at AS book_imported
            FROM chapters c
            JOIN adaptations a ON c.adaptation_id = a.adaptation_id
            JOIN books b ON a.book_id = b.book_id
            WHERE c.image_url IS NOT NULL
            ORDER BY c.created_at DESC
        ''')
        out = []
        for row in cur.fetchall():
            out.append({
                'chapter_id': row[0],
                'chapter_number': row[1],
                'adaptation_id': row[2],
                'image_url': row[3],
                'prompt': row[4],
                'created_at': row[5],
                'book_id': row[6],
                'target_age_group': row[7],
                'transformation_style': row[8],
                'adaptation_created': row[9],
                'book_title': row[10],
                'book_author': row[11],
                'book_imported': row[12],
            })
        return out
    finally:
        conn.close()

async def get_last_adaptation_run(adaptation_id: int):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT run_id, detected_count, target_count, started_at, finished_at, duration_ms, operations, final_map, status, error, meta FROM adaptation_runs WHERE adaptation_id = ? ORDER BY started_at DESC LIMIT 1', (adaptation_id,))
        row = cur.fetchone()
        if not row:
            return None
        ops = json.loads(row[6]) if row[6] else []
        fm = json.loads(row[7]) if row[7] else []
        meta = json.loads(row[10]) if row[10] else {}
        return {
            'run_id': row[0],
            'detected_count': row[1],
            'target_count': row[2],
            'started_at': row[3],
            'finished_at': row[4],
            'duration_ms': row[5],
            'operations': ops,
            'final_map': fm,
            'status': row[8],
            'error': row[9],
            'meta': meta,
        }
    finally:
        conn.close()

# Simple DB-level lock helpers
async def try_acquire_adaptation_lock(adaptation_id: int):
    conn = db_manager.get_connection()
    cur = conn.cursor()
    try:
        holder = 'server'
        ts = datetime.utcnow().isoformat()+"Z"
        # Try to acquire only if not already locked
        cur.execute('INSERT OR IGNORE INTO adaptation_locks (adaptation_id, holder, acquired_at) VALUES (?, ?, ?)', (adaptation_id, holder, ts))
        conn.commit()
        # Check if we acquired the lock (row exists and holder matches)
        cur.execute('SELECT holder FROM adaptation_locks WHERE adaptation_id = ?', (adaptation_id,))
        row = cur.fetchone()
        if not row or row[0] != holder:
            # Did not acquire
            try:
                conn.close()
            except Exception:
                pass
            return None
        return (conn, adaptation_id)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return None

async def release_adaptation_lock(lock_handle):
    try:
        # Support tuple returned by try_acquire
        if isinstance(lock_handle, tuple) and len(lock_handle) == 2:
            conn, adaptation_id = lock_handle
            try:
                cur = conn.cursor()
                cur.execute('DELETE FROM adaptation_locks WHERE adaptation_id = ?', (adaptation_id,))
                conn.commit()
            finally:
                conn.close()
            return
        # Fallback: just close if it's a connection
        try:
            lock_handle.close()
        except Exception:
            pass
    except Exception:
        pass


def set_current_run(adaptation_id: int, run_id: str):
    _current_runs[adaptation_id] = run_id

def get_current_run(adaptation_id: int):
    return _current_runs.get(adaptation_id)

def clear_current_run(adaptation_id: int):
    _current_runs.pop(adaptation_id, None)

# --- Progress helpers for status endpoints ---
async def get_adaptation_progress(adaptation_id: int) -> Dict[str, Any]:
    """Return a minimal progress payload used by /adaptations/{id}/status.
    Compatible with both legacy and new UI expectations.
    """
    try:
        chapters = await get_chapters_for_adaptation(adaptation_id)
        total = len(chapters)
        with_images = sum(1 for ch in chapters if ch.get('image_url'))
    except Exception:
        total, with_images = 0, 0
    # Try to surface active run id if any
    run = None
    try:
        run = await get_active_run(adaptation_id)
    except Exception:
        run = None
    stage = 'running' if (run and run.get('run_id')) else 'idle'
    return {
        'stage': stage,
        'stage_detail': None,
        'run_id': run.get('run_id') if run else None,
        'last_update_ts': run.get('updated_at') if run else None,
        'total_chapters': total,
        'chapters_with_prompts': 0,
        'chapters_with_images': with_images,
        'has_cover': False,
        'has_cover_prompt': False,
        'completion_percentage': (with_images/total*100) if total > 0 else 0,
        'images_done': with_images,
        'last_error': None,
    }

async def update_chapter_text_and_prompt(chapter_id: int, transformed_text: str, user_prompt: str) -> bool:
    """Update chapter text and prompt - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE chapters 
            SET transformed_text = ?, user_prompt = ?
            WHERE chapter_id = ?
        ''', (transformed_text, user_prompt, chapter_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Chapter update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_chapter_image_url(chapter_id: int, image_url: str) -> bool:
    """Update chapter image URL - matches app5.py function"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE chapters 
            SET image_url = ?
            WHERE chapter_id = ?
        ''', (image_url, chapter_id))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Chapter image update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ==================== DASHBOARD STATS ====================

async def get_dashboard_stats() -> Dict[str, int]:
    """Get dashboard statistics using keys expected by templates"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM books")
        total_books = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM adaptations")
        total_adaptations = cursor.fetchone()[0] or 0

        # Active books = books with at least one adaptation
        cursor.execute("SELECT COUNT(DISTINCT book_id) FROM adaptations")
        active_books = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM chapters WHERE image_url IS NOT NULL")
        total_images = cursor.fetchone()[0] or 0

        return {
            "total_books": total_books,
            "total_adaptations": total_adaptations,
            "active_books": active_books,
            "total_images": total_images,
        }
    finally:
        conn.close()
async def update_chapter_text(chapter_id: int, transformed_text: str) -> bool:
    """Update chapter text"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE chapters SET transformed_text = ? WHERE chapter_id = ?', (transformed_text, chapter_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Chapter text update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def update_chapter_image_prompt(chapter_id: int, image_prompt: str) -> bool:
    """Update chapter image prompt"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE chapters SET ai_prompt = ? WHERE chapter_id = ?', (image_prompt, chapter_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"❌ Chapter image prompt update failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def get_setting(setting_key: str, default_value: str = None) -> str:
    """Get setting value from database"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT setting_value FROM settings WHERE setting_key = ?', (setting_key,))
        row = cursor.fetchone()
        if row:
            return row[0]
        return default_value
    except Exception as e:
        print(f"❌ Get setting failed for {setting_key}: {e}")
        return default_value
    finally:
        conn.close()

async def update_setting(setting_key: str, setting_value: str, description: str = "") -> bool:
    """Update or insert setting value"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO settings (setting_key, setting_value, description, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP
        ''', (setting_key, setting_value, description))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Update setting failed for {setting_key}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

async def get_all_settings() -> dict:
    """Get all settings as a dictionary"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT setting_key, setting_value FROM settings')
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        print(f"❌ Get all settings failed: {e}")
        return {}
    finally:
        conn.close()


# ==================== COMPATIBILITY ALIASES ====================

# All possible aliases for compatibility
# Keep high-level async import_book defined above.
# Expose low-level insert helper under a different name for tests/tools.
import_book_to_db_low = import_book_to_db
get_book_by_id = get_book_details
get_adaptation_by_id = get_adaptation_details
create_adaptation = create_adaptation_record
delete_book = delete_book_from_db
delete_adaptation = delete_adaptation_from_db
get_all_books_with_adaptation_counts = get_all_books_with_adaptations
get_chapters_by_adaptation = get_chapters_for_adaptation
update_chapter_text = update_chapter_text_and_prompt
update_chapter_image = update_chapter_image_url
create_chapter = save_chapter_data
update_chapter_record = update_chapter_text_and_prompt
create_chapter_record = save_chapter_data


# ==================== SCHEMA FIX ====================

def _get_book_columns():
    """Get the actual columns in the books table"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(books)")
        columns = [row[1] for row in cursor.fetchall()]
        return columns
    finally:
        conn.close()

# Update get_book_details to handle missing columns gracefully
async def get_book_details_safe(book_id: int) -> Optional[Dict]:
    """Get book details with safe column handling"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    try:
        # Get available columns
        cursor.execute("PRAGMA table_info(books)")
        available_columns = [row[1] for row in cursor.fetchall()]
        
        # Build query with only available columns
        select_columns = []
        if 'book_id' in available_columns:
            select_columns.append('book_id')
        if 'title' in available_columns:
            select_columns.append('title')
        if 'author' in available_columns:
            select_columns.append('author')
        if 'source_type' in available_columns:
            select_columns.append('source_type')
        if 'path' in available_columns:
            select_columns.append('path')
        if 'original_content_path' in available_columns:
            select_columns.append('original_content_path')
        if 'character_reference' in available_columns:
            select_columns.append('character_reference')
        if 'imported_at' in available_columns:
            select_columns.append('imported_at')
        
        query = f"SELECT {', '.join(select_columns)} FROM books WHERE book_id = ?"
        cursor.execute(query, (book_id,))
        
        row = cursor.fetchone()
        if row:
            result = {}
            for i, col in enumerate(select_columns):
                result[col] = row[i]
            # Back-compat: attach parsed analysis fields for convenience
            try:
                if 'character_reference' in result and result['character_reference']:
                    ref = json.loads(result['character_reference']) if isinstance(result['character_reference'], str) else result['character_reference']
                    if isinstance(ref, dict):
                        if 'chapter_count' in ref:
                            result['chapter_count'] = ref.get('chapter_count')
                        if 'word_count' in ref:
                            result['word_count'] = ref.get('word_count')
                        if 'unique_characters' in ref:
                            result['unique_characters'] = ref.get('unique_characters')
            except Exception:
                pass
            return result
        return None
    finally:
        conn.close()

# Override the original function
get_book_details = get_book_details_safe

# Alias for routes expecting get_adaptation_chapters
get_adaptation_chapters = get_chapters_for_adaptation


# === Added compatibility functions for FastAPI dashboard ===

async def get_recent_books(limit: int = 5):
    """Get recent books for dashboard"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT book_id, title, author, imported_at
            FROM books
            ORDER BY imported_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        out = []
        for row in rows:
            out.append({
                'book_id': row[0],
                'title': row[1],
                'author': row[2],
                'import_date': row[3],
                'word_count': 0,
                'chapter_count': 0,
            })
        return out
    finally:
        conn.close()


async def get_recent_adaptations(limit: int = 5):
    """Get recent adaptations for dashboard"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT a.adaptation_id, a.target_age_group, a.created_at,
                   a.status, b.title as book_title, b.author
            FROM adaptations a
            LEFT JOIN books b ON a.book_id = b.book_id
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        out = []
        for row in rows:
            title = f"{row[4]} (Ages {row[1]})" if row[4] else f"Adaptation {row[0]}"
            out.append({
                'adaptation_id': row[0],
                'title': title,
                'target_age_group': row[1],
                'created_date': row[2],
                'status': row[3] or 'in_progress',
                'book_title': row[4],
                'author': row[5],
            })
        return out
    finally:
        conn.close()


async def get_adaptation_status_counts():
    """Get adaptation status counts for dashboard"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM adaptations WHERE status = 'completed'")
        completed = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM adaptations WHERE status IS NULL OR status != 'completed'")
        in_progress = cursor.fetchone()[0] or 0
        return {'completed': completed, 'in_progress': in_progress}
    finally:
        conn.close()


async def get_storage_usage():
    """Get rough storage usage estimate (MB)"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM chapters WHERE image_url IS NOT NULL")
        image_count = cursor.fetchone()[0] or 0
        return book_count * 1 + image_count * 2
    finally:
        conn.close()
