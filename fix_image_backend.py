#!/usr/bin/env python3
"""
Script to update the default image backend to DALL-E
"""
import asyncio
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.insert(0, '/home/user/KidsFastapi')

import database_fixed as database

async def update_image_backend():
    """Update the default image backend to dall-e-3"""
    try:
        print("Updating default image backend to dall-e-3...")
        
        # Update the setting
        success = await database.update_setting("default_image_backend", "dall-e-3", "Default image generation backend")
        
        if success:
            print("✅ Successfully updated default_image_backend to dall-e-3")
            
            # Verify the setting
            current_value = await database.get_setting("default_image_backend", "unknown")
            print(f"✅ Current value: {current_value}")
        else:
            print("❌ Failed to update the setting")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(update_image_backend())