# File Cleanup Analysis for KidsKlassiks

## Analysis Date: 2025-09-29

This document categorizes all files in the root directory and identifies which can be safely moved to an `old/` folder.

---

## ✅ KEEP - Essential Production Files

### Core Application Files
- `main.py` - Main FastAPI application entry point (CURRENTLY USED)
- `config.py` - Configuration management (CURRENTLY USED)
- `database_fixed.py` - Main database module (CURRENTLY USED)
- `models.py` - Data models (MAY BE USED)
- `requirements.txt` - Production dependencies (CURRENTLY USED)

### Configuration Files
- `.env.example` - Environment template for users
- `.env.sample` - Alternative environment template
- `.gitignore` - Git ignore rules
- `pytest.ini` - Test configuration

### Documentation (Active)
- `README.md` - Main documentation (CURRENTLY USED)
- `.env` - Local environment (DO NOT COMMIT, gitignored)

---

## 🗂️ MOVE TO OLD/ - Legacy/Obsolete Files

### 1. Old Fix Scripts (No Longer Needed)
These were one-time migration/fix scripts:
- `comprehensive_fix.py` - Old migration script
- `comprehensive_migration_fix.py` - Old migration script
- `direct_fix.py` - Old fix script
- `final_fix.py` - Old fix script
- `fix_openai_version.py` - Old version fix
- `openai_client_fix.py` - Old client fix
- `simple_one_step_fix.py` - Old fix script
- `install.py` - Old installer

### 2. Debug Scripts (No Longer Needed)
- `debug_character_analysis.py` - Debug script
- `deep_debug_openai.py` - Debug script
- `simple_openai_test.py` - Test script

### 3. Test Files (Can Be Moved, Tests Are in tests/ Directory)
These are ad-hoc test scripts in root, not proper test suite:
- `test_api_workflow.py` - Ad-hoc test
- `test_chapter_detection.py` - Ad-hoc test
- `test_chapters_and_adaptations.py` - Ad-hoc test
- `test_full_workflow.py` - Ad-hoc test
- `test_image_generation.py` - Ad-hoc test
- `test_image_prompt_quality.py` - Ad-hoc test
- `test_imports.py` - Ad-hoc test
- `test_logger_app.py` - Ad-hoc test
- `test_migration.py` - Ad-hoc test
- `test_web_api_complete.py` - Ad-hoc test
- `test.py` - Generic test file

### 4. Alternative Main Files (Not Used)
- `main_clean.py` - Old alternative main
- `main_minimal.py` - Old minimal version
- `template_context.py` - Old template helper

### 5. Old Database Modules (Not Used)
- `database.py` - Old database module (replaced by database_fixed.py)
- `database_image_functions.py` - Old image functions (integrated into database_fixed.py)

### 6. Old Requirements Files
- `requirements_clean.txt` - Old version
- `requirements_fixed.txt` - Old version
- `requirements_legacy.txt` - Old version
- `requirements_python313.txt` - Python 3.13 specific (not needed)

### 7. Windows Batch Files (Not Needed for Production)
All .bat and .ps1 files are Windows-specific and not needed for production:
- `fix_character_analysis.ps1`
- `fix_dependencies.bat`
- `fix_import_issues.bat`
- `quick_fix_python313.bat`
- `restart_server.bat`
- `run_comprehensive_fix.bat`
- `run_direct_fix.bat`
- `run_final_fix.bat`
- `run_migration_fix.bat`
- `start_legacy_windows.bat`
- `start_python313_windows.bat`
- `start_server.bat`
- `start_windows.bat`

### 8. Old Documentation Files
These are outdated migration/setup docs:
- `CLEAR_INSTRUCTIONS.md` - Old instructions
- `COMPLETE_TEST_REPORT.md` - Test report (can archive)
- `DEMO_COMPLETE_WORKFLOW.md` - Demo document (can archive)
- `FILE_MANIFEST.md` - Old manifest
- `KidsKlassiks FastAPI + HTMX.md` - Duplicate of README content
- `MIGRATION_README.md` - Old migration doc
- `WINDOWS_SETUP.md` - Windows-specific (can archive)
- `WINDOWS_TROUBLESHOOTING.md` - Windows-specific (can archive)

### 9. Other Files to Move
- `imageprompts.txt` - Old prompts file (not used)
- `desktop.ini` - Windows system file

---

## 📊 Summary

### Files to Keep in Root (15 files)
1. `main.py`
2. `config.py`
3. `database_fixed.py`
4. `models.py`
5. `requirements.txt`
6. `.env.example`
7. `.env.sample`
8. `.gitignore`
9. `pytest.ini`
10. `README.md`
11. `.env` (local, gitignored)
12. Directories: routes/, services/, templates/, static/, tests/, legacy/

### Files to Move to old/ (67 files)
- 8 fix scripts
- 3 debug scripts
- 11 test files
- 3 alternative main files
- 2 old database modules
- 4 old requirements files
- 13 Windows batch/PowerShell files
- 8 old documentation files
- 15 miscellaneous old files

### Verification Status
✅ No references to old files found in active code (routes/, services/, templates/)
✅ Main application only imports: config, database_fixed, routes, services
✅ All old files are standalone scripts or deprecated modules

---

## Recommended Action

1. Create `old/` directory
2. Move all 67 identified files to `old/`
3. Update `.gitignore` to ignore `old/` directory (optional)
4. Test application still works
5. Commit changes to git

This will clean up the root directory from 80+ files down to ~15 essential files.
