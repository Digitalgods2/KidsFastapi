#!/usr/bin/env python3
"""
Script to ensure Vertex AI settings are properly configured in the database
This fixes the issue where Vertex credentials are lost
"""

import json
import sqlite3
import os
import sys

def fix_vertex_settings():
    """Fix Vertex AI settings in the database"""
    
    # Path to vertexapi.json
    vertex_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'vertexapi.json')
    db_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'kidsklassiks.db')
    
    if not os.path.exists(vertex_file):
        print(f"❌ Error: vertexapi.json not found at {vertex_file}")
        print("Please ensure the Vertex AI credentials file exists")
        return False
    
    if not os.path.exists(db_file):
        print(f"❌ Error: Database not found at {db_file}")
        return False
    
    try:
        # Read the vertex credentials
        with open(vertex_file, 'r') as f:
            creds = json.load(f)
        
        # Get project ID
        project_id = creds.get('project_id', '')
        if not project_id:
            print("❌ Error: No project_id found in credentials")
            return False
        
        print(f"📋 Found Project ID: {project_id}")
        
        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Ensure settings table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Save settings
        settings_to_save = [
            ('vertex_project_id', project_id, 'Google Cloud Project ID for Vertex AI'),
            ('vertex_credentials', json.dumps(creds), 'Vertex AI service account credentials'),
            ('vertex_location', 'us-central1', 'Vertex AI service location'),
            ('default_image_backend', 'vertex-imagen', 'Default image generation backend'),
            ('default_aspect_ratio', '16:9', 'Default aspect ratio for images')
        ]
        
        for key, value, desc in settings_to_save:
            cursor.execute('''
                INSERT OR REPLACE INTO settings (setting_key, setting_value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, value, desc))
            print(f"✅ Saved: {key}")
        
        conn.commit()
        
        # Verify settings
        cursor.execute('SELECT COUNT(*) FROM settings WHERE setting_key LIKE "vertex%"')
        count = cursor.fetchone()[0]
        print(f"\n✅ Successfully saved {count} Vertex AI settings to database")
        
        # Set environment variable
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = vertex_file
        print(f"✅ Set GOOGLE_APPLICATION_CREDENTIALS to {vertex_file}")
        
        conn.close()
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in vertexapi.json - {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_vertex_settings()
    sys.exit(0 if success else 1)