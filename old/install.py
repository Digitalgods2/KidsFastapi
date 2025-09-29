#!/usr/bin/env python3
"""
KidsKlassiks Installation Script
Run this to set up the application properly
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd):
    """Run a command and return success status"""
    try:
        subprocess.run(cmd, shell=True, check=True)
        return True
    except:
        return False

def main():
    print("🚀 KidsKlassiks Installation Script")
    print("====================================")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    print(f"✅ Python {sys.version}")
    
    # Create virtual environment
    print("\n📦 Setting up virtual environment...")
    if not Path("venv").exists():
        if not run_command(f"{sys.executable} -m venv venv"):
            print("❌ Failed to create virtual environment")
            return False
    
    # Determine activation script
    if os.name == 'nt':  # Windows
        activate = "venv\\Scripts\\activate"
        pip = "venv\\Scripts\\pip"
    else:  # Unix/Linux/Mac
        activate = "source venv/bin/activate"
        pip = "venv/bin/pip"
    
    # Upgrade pip
    print("\n📦 Upgrading pip...")
    run_command(f"{pip} install --upgrade pip")
    
    # Install requirements
    print("\n📦 Installing dependencies...")
    if not run_command(f"{pip} install -r requirements_clean.txt"):
        print("⚠️ Some dependencies failed to install")
    
    # Create directories
    print("\n📁 Creating directories...")
    dirs = ["uploads", "generated_images", "publications", "exports", "backups"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    # Check for .env file
    if not Path(".env").exists():
        print("\n⚠️ No .env file found!")
        print("📝 Creating .env from template...")
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Created .env file - please add your API keys")
        else:
            print("❌ No .env.example found - please create .env manually")
    
    print("\n✅ Installation complete!")
    print("\n📝 Next steps:")
    print("1. Edit .env and add your OPENAI_API_KEY")
    print("2. Configure your database settings in .env")
    print("3. Run: python main_clean.py")
    print("4. Open: http://localhost:8000")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
