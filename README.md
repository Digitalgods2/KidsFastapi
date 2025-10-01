# 📚 KidsKlassiks - AI-Powered Children's Book Transformer

> Transform classic literature into beautifully illustrated, age-appropriate children's books using cutting-edge AI

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991.svg)](https://openai.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

KidsKlassiks is a full-stack web application that revolutionizes how classic literature reaches young readers. Using advanced AI, it automatically transforms complex Victorian prose into child-friendly language, generates custom illustrations with character consistency, and produces professional, print-ready publications.

---

## ✨ Core Features

### 🤖 AI Text Transformation (NEW!)
- **Automatic Age-Appropriate Simplification**: Victorian English → child-friendly language
- **GPT-4o-mini Powered**: Advanced language transformation with context awareness
- **Three Age Groups**: Customized vocabulary and complexity for ages 3-5, 6-8, 9-12
- **Intelligent Transformation Rules**:
  - **Ages 3-5**: Very simple words (1-2 syllables), 3-5 word sentences, 30-40% original length
  - **Ages 6-8**: Simple everyday words, 5-10 word sentences, 50-60% original length
  - **Ages 9-12**: Age-appropriate vocabulary, 10-15 word sentences, 70-80% original length
- **Batch Processing**: Transform all chapters with one click
- **Single Chapter Transform**: Refine individual chapters via API
- **User Editing**: Review and manually edit transformed text
- **Preserves Story**: Maintains plot, character names, and key events

### 📖 Book Management
- **Import Books**: Upload EPUB, PDF, or TXT files from any source
- **Project Gutenberg Cleaner**: Automatically removes legal boilerplate and metadata
- **Smart Text Cleaning**: Detects and removes START/END markers, headers, footers
- **Metadata Extraction**: Automatic title, author, and chapter detection
- **Special Format Support**: Detects patterns like "Stave I" from A Christmas Carol
- **Library Organization**: Browse and manage your growing book collection
- **Character Analysis**: AI-powered character identification with frequency ranking

### 🎨 Intelligent Adaptation
- **Age-Appropriate Transformation**: Tailor content for ages 3-5, 6-8, or 9-12
- **Style Selection**: Choose transformation styles (simplified, educational, imaginative)
- **Theme Customization**: Set overall tone (adventure, educational, whimsical, etc.)
- **Smart Chapter Segmentation**: Auto-detect or manually configure chapter structure
- **Character Preservation**: Maintains consistent character names and descriptions
- **Progress Statistics**: Real-time chapter and image completion tracking

### 🖼️ AI Image Generation with Character Consistency
- **Character Consistency System**: Two-layer approach ensuring characters look the same across all images
  - **Base Prompt Layer**: Consistent character descriptions (age, hair, clothing, etc.)
  - **Scene Layer**: Chapter-specific context and actions
- **Multiple AI Backends**: Support for DALL-E 3, Vertex AI, and more
- **Per-Chapter Illustrations**: Generate custom images for each chapter
- **Cover Art Generation**: Create stunning book covers that appear first in gallery
- **Image Review & Regeneration**: 
  - View all generated images in a beautiful gallery
  - Edit prompts and regenerate unsatisfactory images
  - Quick regenerate with same prompt or create custom variations
  - Delete and replace images
  - Cover images displayed prominently
- **Batch Processing**: Generate multiple images simultaneously

### 📊 Processing Pipeline
- **Visual Progress Tracking**: Real-time status with percentage completion
- **Chapter/Image Statistics**: See X/Y chapters completed, image progress bars
- **Run History**: Track all processing runs with detailed logs
- **Chapter Mapping**: Intelligent chapter detection and normalization
- **Error Recovery**: Graceful handling of failures with retry capabilities
- **Tab Counters**: Server-side accurate counts for "All", "In Progress", "Completed"

### 📝 Review & Editing
- **Chapter Preview**: Review both original and transformed content
- **Side-by-Side Comparison**: See transformation results before/after
- **Inline Editing**: Edit chapter titles and transformed text
- **Image Management**: Review, approve, or regenerate illustrations
- **Quality Control**: Ensure consistency across all chapters
- **User Prompt Support**: Add custom prompts to guide AI transformation

### 📤 Publishing & Export (ENHANCED!)
- **Direct PDF Download**: Generate and download print-ready PDFs instantly
- **No More "We'll Notify You"**: Files download immediately on export
- **Beautiful Publish Page**: Gradient purple header, green status indicators
- **Enhanced UI/UX**: Modern styling with improved button states
- **Field Mapping Fix**: Correct cover image and text rendering in PDFs
- **Fallback Logic**: Uses transformed text if available, otherwise original
- **Print-Ready Quality**: Professional formatting with cover images

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (Python 3.12 recommended)
- **Virtual Environment** (recommended)
- **OpenAI API Key** (required for text transformation and image generation)

### Installation

```bash
# Clone the repository
git clone https://github.com/Digitalgods2/KidsFastapi.git
cd KidsFastapi

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Configuration

Create a `.env` file in the root directory:

```env
# Database (SQLite by default)
DATABASE_URL=sqlite:///./kidsklassiks.db

# OpenAI API Key (REQUIRED for text transformation and image generation)
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Vertex AI (Google Cloud)
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Image Generation Settings
DEFAULT_IMAGE_BACKEND=dall-e-3
MAX_BATCH_SIZE=50

# Processing Settings
REPROCESS_COOLDOWN_SECONDS=30
STALE_RUN_TIMEOUT_SECONDS=300
CHAPMAP_MAX_OPS=1000

# Text Transformation Settings (GPT-4o-mini)
DEFAULT_MODEL=gpt-4o-mini
TEMPERATURE=0.7
```

### Running the Application

```bash
# Start the development server
uvicorn main:app --reload --port 8000

# The application will be available at:
# http://localhost:8000
```

---

## 📖 Complete User Guide

### 1. Import a Book

1. Navigate to **Books** → **Import**
2. Upload a book file (EPUB, PDF, or TXT)
3. Enter book details (title, author, original chapter count)
4. Click **Import Book**
5. **Automatic Cleaning**: Project Gutenberg boilerplate is removed automatically

**Pro Tip**: Project Gutenberg texts work perfectly with automatic cleaning!

### 2. Create an Adaptation

1. Go to **Adaptations** → **Create New**
2. Select a book from your library
3. **Choose target age group** (3-5, 6-8, or 9-12) - This affects text transformation
4. Select transformation style and theme
5. Specify key characters to preserve (optional)
6. Choose chapter structure (keep original or auto-segment)
7. Click **Create Adaptation**

### 3. Transform Text to Age-Appropriate Language (NEW!)

#### Option A: Batch Transform All Chapters (Recommended)
1. Open your adaptation
2. Click **Transform All Chapters** button
3. Watch as AI transforms each chapter automatically
4. Review transformation statistics (original vs transformed length)

#### Option B: Transform Individual Chapters
1. Navigate to a specific chapter
2. Click **Transform Chapter** 
3. Review the transformed text
4. Edit manually if needed

**Example Transformation** (A Christmas Carol, Ages 6-8):
```
Original (Victorian English):
"Marley was dead: to begin with. There is no doubt whatever about that. The register 
of his burial was signed by the clergyman, the clerk, the undertaker, and the chief 
mourner. Scrooge signed it: and Scrooge's name was good upon 'Change, for anything 
he chose to put his hand to."

Transformed (Child-Friendly):
"Marley was dead. Everyone knew it. Important people had signed the papers that 
proved he was gone. Scrooge signed them too. People trusted Scrooge's signature 
because he was a businessman."
```

### 4. Process Chapters

1. Click **Process** on your adaptation
2. Click **Reprocess Chapters** to start the pipeline
3. Watch the progress in real-time with visual progress bars
4. See chapter/image statistics update live
5. Review the chapter mapping and operations performed

### 5. Generate Images with Character Consistency

#### Option A: Batch Generation (Recommended)
1. Click **Generate All Images** from the adaptation view
2. Select your preferred image backend (DALL-E 3 recommended)
3. Monitor batch progress with real-time updates
4. Review all generated images in gallery
5. **Cover image appears first** in the gallery view

#### Option B: Individual Generation
1. Navigate to **Images** → **Chapters**
2. Click **Generate** on individual chapters
3. Edit prompts before generation (optional)
4. Review and approve images
5. Regenerate any chapter with same or different prompt

**Character Consistency**: The system automatically ensures characters look the same across all images by using a two-layer prompt system.

### 6. Review & Edit

1. Go to the adaptation detail page (`/adaptations/{id}`)
2. View **progress statistics**: X/Y chapters completed, image progress
3. See **visual progress bar** showing percentage complete
4. View all chapters in list or grid view
5. Click on any chapter to:
   - View full transformed content
   - See original content side-by-side
   - Edit title and text manually
   - View associated image
6. Click on image thumbnails to:
   - View full-size image
   - See the generation prompt used
   - Regenerate with same prompt (quick variation)
   - Edit prompt and regenerate (custom variation)
   - Delete the image

### 7. Export & Publish (ENHANCED!)

1. Go to **Adaptations** → Select your completed adaptation
2. Click **Publish**
3. Review the beautiful publish page with gradient purple header
4. See green "Ready to Publish" status indicator
5. Click **Export PDF** button
6. **PDF downloads immediately** - no waiting for notifications!
7. Open the print-ready PDF with:
   - Cover image on first page
   - Transformed child-friendly text
   - Chapter illustrations
   - Professional formatting

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- **FastAPI**: Modern Python async web framework
- **SQLite**: Lightweight database (default, PostgreSQL supported)
- **Pydantic**: Data validation and settings management
- **Asyncio**: Full async/await support for concurrent operations

**Frontend:**
- **HTMX**: Dynamic updates without page reloads or JavaScript frameworks
- **Jinja2**: Server-side templating with inheritance
- **Bootstrap 5**: Responsive, modern UI framework
- **Alpine.js**: Lightweight reactive components

**AI Services:**
- **OpenAI GPT-4o-mini**: Age-appropriate text transformation (NEW!)
- **OpenAI DALL-E 3**: High-quality image generation
- **Vertex AI Imagen**: Alternative image backend (optional)
- **Character Analyzer**: AI-powered character detection and consistency

### Project Structure

```
KidsKlassiks/
├── main.py                        # FastAPI application entry point
├── config.py                      # Configuration and environment variables
├── database_fixed.py              # Database layer (SQLite/PostgreSQL)
├── models.py                      # Pydantic data models
├── requirements.txt               # Python dependencies
│
├── routes/                        # API endpoints (FastAPI routers)
│   ├── adaptations.py             # Adaptation CRUD + batch transform (NEW!)
│   ├── books.py                   # Book import & management
│   ├── chapters.py                # Chapter CRUD + transform (NEW!)
│   ├── images.py                  # Batch image generation
│   ├── images_individual.py       # Single image operations
│   ├── images_gallery.py          # Image gallery with cover first (ENHANCED!)
│   ├── review.py                  # Review & editing interface
│   ├── publish.py                 # PDF export + direct download (ENHANCED!)
│   ├── settings.py                # Application settings
│   └── health.py                  # Health checks
│
├── services/                      # Business logic layer
│   ├── chat_helper.py             # AI text transformation (NEW!)
│   ├── gutenberg_cleaner.py       # Project Gutenberg text cleaner (NEW!)
│   ├── character_helper.py        # Character consistency system (NEW!)
│   ├── image_generation_service.py # Image generation with consistency
│   ├── transformation_service.py  # Adaptation transformation
│   ├── character_analyzer.py      # Character detection & ranking
│   ├── vertex_service.py          # Google Vertex AI integration
│   ├── pdf_generator.py           # PDF export with proper field mapping
│   └── logger.py                  # Structured logging
│
├── templates/                     # Jinja2 HTML templates
│   ├── layouts/
│   │   └── base.html              # Base template with navigation
│   ├── pages/
│   │   ├── dashboard.html         # Main dashboard with vibrant colors
│   │   ├── adaptations.html       # Adaptations list with progress stats (ENHANCED!)
│   │   ├── publish.html           # Publish page with gradient header (ENHANCED!)
│   │   ├── images.html            # Image gallery
│   │   └── ...
│   └── components/                # Reusable components
│
├── static/                        # Static assets
│   ├── css/                       # Custom stylesheets
│   ├── js/                        # Client-side JavaScript
│   └── images/                    # Static images
│
├── scripts/                       # Utility scripts
│   ├── analyze_book_characters.py # Character analysis tool (NEW!)
│   ├── fix_image_filenames.py     # Image filename repair (NEW!)
│   └── ...
│
├── tests/                         # Test suite
│   ├── test_character_consistency.py  # Character consistency tests (NEW!)
│   ├── test_gutenberg_cleaner.py      # Text cleaner tests (NEW!)
│   ├── test_books.py
│   ├── test_adaptations.py
│   └── test_images.py
│
├── docs/                          # Documentation
│   ├── CHARACTER_CONSISTENCY_FEATURE.md
│   ├── CHARACTER_PRESERVATION_ANALYSIS.md
│   └── CHANGES_SUMMARY.md
│
└── transform_christmas_carol.py  # Example transformation script (NEW!)
```

---

## 🔌 API Endpoints

### Books
- `GET /books/` - List all books
- `GET /books/import` - Import book page
- `POST /books/import` - Upload and import new book
- `GET /books/{id}` - Get book details
- `DELETE /books/{id}` - Delete book

### Adaptations
- `GET /adaptations/` - List all adaptations with progress stats (ENHANCED!)
- `GET /adaptations/create` - Create adaptation page (FIXED: book_id parsing)
- `POST /adaptations/create` - Create new adaptation
- `GET /adaptations/{id}` - View adaptation details with tabs
- `POST /adaptations/{id}/transform-all` - Batch transform all chapters (NEW!)
- `GET /adaptations/{id}/process` - Processing page
- `POST /adaptations/{id}/process_chapters` - Start chapter processing
- `GET /adaptations/{id}/status` - Get processing status with statistics
- `DELETE /adaptations/{id}` - Delete adaptation

### Chapters (NEW!)
- `GET /chapters/{id}/details` - Get chapter details
- `POST /chapters/{id}/update` - Update chapter text/title
- `POST /chapters/{id}/transform` - Transform single chapter (NEW!)
- `POST /chapters/{id}/generate-image` - Generate/regenerate image with custom prompt
- `POST /chapters/{id}/regenerate-image` - Quick regenerate with same prompt
- `DELETE /chapters/{id}/image` - Delete chapter image

### Images
- `GET /images/{adaptation_id}/gallery` - View all images (cover first) (ENHANCED!)
- `GET /images/{adaptation_id}/images` - Image management page
- `POST /images/{adaptation_id}/generate_batch` - Batch generate all images
- `GET /images/{adaptation_id}/generation_status` - Get batch status
- `POST /images/{adaptation_id}/regenerate_image` - Regenerate single image

### Publish (ENHANCED!)
- `GET /publish/{adaptation_id}` - Publish page with gradient header (NEW UI!)
- `POST /publish/export/{adaptation_id}` - Direct PDF download (FIXED!)

### Settings
- `GET /settings` - Application settings page
- `POST /settings/update` - Update settings (API keys, defaults)

### Health
- `GET /health` - Liveness check
- `GET /ready` - Readiness check (DB, image backend, cache)

---

## 🎨 Features Deep Dive

### AI Text Transformation System (NEW!)

The text transformation system is powered by OpenAI's GPT-4o-mini and uses sophisticated age-specific rules:

#### **How It Works**

1. **Age-Group Detection**: Reads target age from adaptation settings
2. **Rule Application**: Applies age-appropriate vocabulary, sentence length, and complexity rules
3. **Context Preservation**: Maintains story events, character names, and plot points
4. **Length Optimization**: Reduces text length based on age group (30-80% of original)
5. **Database Storage**: Saves transformed text separately from original

#### **Transformation Rules by Age Group**

| Age Group | Vocabulary | Sentence Length | Concepts | Target Length |
|-----------|-----------|----------------|----------|--------------|
| **3-5 years** | Very simple (1-2 syllables) | Very short (3-5 words) | Concrete, familiar only | 30-40% of original |
| **6-8 years** | Simple, everyday words | Short (5-10 words) | Simple with explanations | 50-60% of original |
| **9-12 years** | Age-appropriate with challenges | Varied (10-15 words) | More complex with context | 70-80% of original |

#### **Example: A Christmas Carol Transformation**

**Book**: A Christmas Carol by Charles Dickens  
**Target Age**: 6-8 years  
**Chapters**: 17 (Staves I-V auto-detected)  
**Results**: 
- Original: 158,371 characters
- Transformed: 65,031 characters
- Reduction: 58.9%

**Before (Victorian English)**:
```
"Old Marley was as dead as a door-nail. Mind! I don't mean to say that I know, 
of my own knowledge, what there is particularly dead about a door-nail. I might 
have been inclined, myself, to regard a coffin-nail as the deadest piece of 
ironmongery in the trade."
```

**After (Ages 6-8)**:
```
"Marley had been dead for seven years. Everyone knew it. Scrooge knew it better 
than anyone because he had been Marley's only friend and his business partner."
```

#### **API Usage**

```python
# Transform all chapters
POST /adaptations/{adaptation_id}/transform-all

# Transform single chapter
POST /chapters/{chapter_id}/transform

# Response includes:
{
  "success": true,
  "transformed_text": "...",
  "original_length": 1234,
  "transformed_length": 678
}
```

### Character Consistency System

Ensures characters look identical across all chapter illustrations:

#### **Two-Layer Approach**

**Layer 1: Base Character Descriptions**
```
Scrooge: elderly man (60s), thin and angular, gray hair combed back, 
stern expression, pointed nose, wears dark Victorian business attire 
with high collar and cravat
```

**Layer 2: Scene-Specific Context**
```
Chapter 1 Scene: Scrooge sitting at his desk in dim office, counting 
coins by candlelight, cold expression, foggy London visible through 
window behind him
```

**Final Prompt** = Base Description + Scene Context + Art Style

#### **Benefits**
- ✅ Same character appearance in all images
- ✅ Consistent clothing, hair, age, features
- ✅ Scene-appropriate actions and poses
- ✅ Professional-quality book illustrations

### Project Gutenberg Text Cleaner (NEW!)

Automatically removes legal boilerplate that confuses AI:

#### **What Gets Removed**
- Start markers: `*** START OF THE PROJECT GUTENBERG EBOOK ***`
- End markers: `*** END OF THE PROJECT GUTENBERG EBOOK ***`
- Header metadata: License text, transcriber notes, release information
- Footer metadata: Full license text, donation requests

#### **What Gets Preserved**
- Book title and author
- Table of contents (if present)
- All story content
- Original formatting

#### **Usage**
```python
from services.gutenberg_cleaner import clean_gutenberg_text

cleaned_text, was_gutenberg = clean_gutenberg_text(original_text)

if was_gutenberg:
    print("Gutenberg boilerplate removed successfully!")
```

### Image Review & Regeneration

Comprehensive image review system with modal interface:

#### **Enhanced Image Modal**
- **Large Preview**: View images in full quality (full screen)
- **Prompt Display**: See exactly what prompt generated the image
- **Chapter Context**: View chapter number and title
- **Statistics**: Image dimensions, generation date
- **Quick Actions**: Three-button interface

#### **Regeneration Options**

1. **Quick Regenerate** (Same Prompt)
   - Uses identical prompt for variations
   - Fastest option
   - Good for minor tweaks

2. **Custom Regenerate** (Edit Prompt)
   - Edit the prompt before regenerating
   - Full control over output
   - Perfect for specific changes

3. **Delete & Start Over**
   - Remove unsatisfactory image
   - Generate new one from scratch
   - Clean slate approach

#### **Loading States**
- Spinner animation during generation
- "Generating..." text feedback
- Disabled buttons prevent double-clicks
- Success notification on completion
- Auto-refresh to show new image

### PDF Export with Direct Download (ENHANCED!)

#### **What Changed**
❌ **Old**: "We'll notify you when PDF is ready"  
✅ **New**: PDF downloads immediately when generated

#### **Field Mapping Fix**
The system now correctly maps database fields to PDF generator expectations:

```python
# Database → PDF Generator Mapping
{
    'cover_url': 'cover_image_url',           # Cover image
    'transformed_text': 'transformed_chapter_text',  # Chapter text
    'original_text_segment': 'original_chapter_text' # Fallback
}
```

#### **Fallback Logic**
1. Try transformed text first
2. If empty, use original text
3. Ensures PDFs always have content

#### **Enhanced UI**
- Gradient purple header (`#667eea` → `#764ba2`)
- Green "Ready to Publish" status (`bg-success`)
- Modern button styling with icons
- Loading states during generation
- Success alerts on download

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test files
pytest tests/test_character_consistency.py
pytest tests/test_gutenberg_cleaner.py

# Run with verbose output
pytest -v

# Run transformation tests only
pytest tests/test_chat_helper.py -v
```

**Test Coverage:**
- ✅ **Character Consistency**: 152 test cases
- ✅ **Gutenberg Cleaner**: 159 test cases  
- ✅ **Text Transformation**: Integration tests with real API
- ✅ **Database Operations**: CRUD operations
- ✅ **API Endpoints**: Request/response validation

---

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection string | `sqlite:///./kidsklassiks.db` | No |
| `OPENAI_API_KEY` | OpenAI API key for AI features | None | **YES** |
| `DEFAULT_IMAGE_BACKEND` | Image generation backend | `dall-e-3` | No |
| `DEFAULT_MODEL` | Text transformation model | `gpt-4o-mini` | No |
| `TEMPERATURE` | AI temperature (creativity) | `0.7` | No |
| `MAX_BATCH_SIZE` | Max images per batch | `50` | No |
| `REPROCESS_COOLDOWN_SECONDS` | Cooldown between runs | `30` | No |
| `STALE_RUN_TIMEOUT_SECONDS` | Run timeout | `300` | No |
| `CHAPMAP_MAX_OPS` | Max chapter ops | `1000` | No |

### Supported Image Backends

- **dall-e-3** (OpenAI DALL-E 3) - Default, highest quality
- **dall-e-2** (OpenAI DALL-E 2) - Faster, lower cost
- **vertex-imagen** (Google Vertex AI Imagen) - Alternative provider
- More backends can be added in `services/image_generation_service.py`

### AI Models

- **gpt-4o-mini** - Text transformation (recommended)
- **gpt-4o** - Higher quality, more expensive
- **gpt-3.5-turbo** - Faster, lower quality

---

## 🚢 Deployment

### Production Setup with Gunicorn

```bash
# Install production server
pip install gunicorn uvicorn[standard]

# Run with Gunicorn + Uvicorn workers
gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -

# Or use Uvicorn directly
uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --proxy-headers \
  --forwarded-allow-ips='*'
```

### Environment Setup

```bash
# Set production environment variables
export DATABASE_URL="postgresql://user:pass@localhost/kidsklassiks"
export OPENAI_API_KEY="sk-production-key"
export MAX_BATCH_SIZE="100"
export DEFAULT_MODEL="gpt-4o-mini"
```

### Database Migration

```bash
# For production, use PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/kidsklassiks

# Tables auto-create on startup
# Or run migrations manually if needed
python -c "from database_fixed import init_db; import asyncio; asyncio.run(init_db())"
```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t kidsklassiks .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-xxx kidsklassiks
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Workflow

1. **Fork the repository**
   ```bash
   git fork https://github.com/Digitalgods2/KidsFastapi.git
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Write clean, documented code
   - Follow existing code style
   - Add tests for new features

4. **Run tests**
   ```bash
   pytest
   ```

5. **Commit your changes**
   ```bash
   git commit -m "feat: add amazing feature"
   ```

6. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Open a Pull Request**
   - Use the GitHub web interface
   - Provide clear description of changes
   - Reference any related issues

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features (e.g., `feat: add AI text transformation`)
- `fix:` Bug fixes (e.g., `fix: correct PDF field mapping`)
- `docs:` Documentation changes (e.g., `docs: update README`)
- `style:` Code style changes (formatting, no logic change)
- `refactor:` Code refactoring (no feature change)
- `test:` Test additions/changes
- `chore:` Maintenance tasks (dependencies, config)

### Code Style

- **Python**: Follow PEP 8
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings
- **Async**: Prefer async/await for I/O operations
- **Error Handling**: Always handle exceptions gracefully

---

## 🐛 Troubleshooting

### Common Issues

#### Server won't start
```bash
# Check if port is already in use
lsof -i :8000

# Kill existing process
kill -9 $(lsof -t -i:8000)

# Try a different port
uvicorn main:app --port 8001
```

#### Database errors
```bash
# Delete and recreate database (CAUTION: deletes all data!)
rm kidsklassiks.db
# Restart server - database recreates automatically
uvicorn main:app --reload
```

#### Import errors / Missing dependencies
```bash
# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt

# Or create fresh virtual environment
deactivate
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### Image generation fails
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key with Python
python -c "import openai; openai.api_key='sk-xxx'; print(openai.Model.list())"

# Check config
python -c "import config; print(f'Key: {config.OPENAI_API_KEY[:10]}...')"
```

#### Text transformation fails
```bash
# Check if API key has GPT-4o-mini access
python -c "import openai; print(openai.Model.retrieve('gpt-4o-mini'))"

# Test transformation
python transform_christmas_carol.py
```

#### HTMX not updating
- Clear browser cache: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
- Check browser console for errors: `F12` → Console tab
- Verify HTMX is loaded: Network tab should show `htmx.min.js`
- Disable browser extensions that might block requests

#### PDF export has no images/text
```bash
# This is fixed in latest version!
# If still seeing issues:

# 1. Check database fields
python -c "
from database_fixed import get_adaptation_details
import asyncio
adaptation = asyncio.run(get_adaptation_details(1))
print(f'Cover URL: {adaptation.get(\"cover_url\")}')
"

# 2. Verify field mapping in routes/publish.py
grep -A 5 "cover_image_url" routes/publish.py
```

### Debug Mode

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug

# Or add to .env file
echo "LOG_LEVEL=DEBUG" >> .env
```

### Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/Digitalgods2/KidsFastapi/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/Digitalgods2/KidsFastapi/discussions)

---

## 📝 Changelog

### Version 3.0.0 (Latest - October 2025) 🎉

#### 🤖 AI Text Transformation System (MAJOR NEW FEATURE)
- **GPT-4o-mini Integration**: Automatic age-appropriate text simplification
- **Age-Specific Rules**: Customized transformation for ages 3-5, 6-8, 9-12
- **Batch Processing**: Transform all chapters with one endpoint
- **Single Chapter Transform**: Refine individual chapters
- **Preservation Logic**: Maintains plot, characters, and story events
- **Length Optimization**: Reduces text 30-80% based on age group

#### 📚 Project Gutenberg Support (NEW)
- **Automatic Text Cleaning**: Removes legal boilerplate and metadata
- **START/END Detection**: Strips Gutenberg markers automatically
- **Metadata Removal**: Cleans headers, footers, and license text
- **Story Preservation**: Keeps all actual book content intact

#### 📤 PDF Export Enhancements
- **Direct Download**: Immediate file download (no more "we'll notify you")
- **Field Mapping Fix**: Corrected `cover_url` → `cover_image_url` mapping
- **Text Rendering Fix**: Proper `transformed_text` → `transformed_chapter_text`
- **Fallback Logic**: Uses transformed text, falls back to original if needed
- **Beautiful UI**: Gradient purple header, green status indicators

#### 🎨 UI/UX Improvements
- **Publish Page Redesign**: Modern gradient styling, improved buttons
- **Progress Statistics**: Real-time chapter/image completion tracking
- **Visual Progress Bars**: Percentage completion with color coding
- **Tab Counters**: Server-side accurate counts for adaptations
- **Gallery Enhancement**: Cover images now appear first

#### 🐛 Critical Bug Fixes
- **Query Parameter Validation**: Fixed `/adaptations/create?book_id=1` parsing error
- **Database Functions**: Corrected `update_chapter_text_and_prompt` usage
- **Route Ordering**: Prevented path parameter collision
- **Chapter Detection**: Added "Stave" pattern for A Christmas Carol

#### 🔧 Technical Improvements
- **Character Consistency**: Two-layer prompt system for consistent characters
- **Enhanced Error Handling**: Better recovery across transformation pipeline
- **Token Optimization**: Smart token calculation for AI requests
- **Field Mapping**: Improved database-to-service field translation

#### 📊 Statistics & Impact
- **36 files changed**: 6,023 insertions, 278 deletions
- **New Files**: 7 new service modules, 3 test suites, helper scripts
- **Code Quality**: Comprehensive test coverage for new features
- **Performance**: Optimized batch operations and async processing

#### 🧪 Testing & Validation
- **Tested with A Christmas Carol**: 17 chapters successfully transformed
- **Transformation Metrics**: 158,371 → 65,031 characters (58% reduction)
- **Character Consistency**: Verified across multiple books
- **PDF Generation**: Validated with cover images and transformed text

### Version 2.0.0 (Previous)

#### New Features ✨
- Image review system with comprehensive modal
- Chapter management API endpoints
- Adaptation view page with server-side tabs
- Enhanced image controls (regenerate, edit, delete)
- Progress indicators for all operations

#### Improvements 🔧
- Massive cleanup: 54 legacy files moved to `old/`
- Cleaner repository structure
- Better file organization
- Updated documentation

#### Bug Fixes 🐛
- Fixed 405 error accessing `/adaptations/{id}`
- Fixed database import references
- Improved error handling in image generation

### Version 1.0.0 (Initial Release)

- Book import and management
- AI-powered adaptation
- Chapter processing
- Basic image generation
- SQLite database
- FastAPI backend
- Bootstrap UI

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### MIT License Summary

- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ⚠️ Liability and warranty limitations apply

---

## 🙏 Acknowledgments

### Technologies
- **FastAPI** - Modern, fast Python web framework
- **OpenAI** - GPT-4o-mini for text transformation, DALL-E for images
- **HTMX** - Dynamic HTML updates without JavaScript complexity
- **Bootstrap 5** - Beautiful, responsive UI components
- **SQLite/PostgreSQL** - Reliable data storage

### Inspiration
- **Project Gutenberg** - Free access to classic literature
- **Children's Literacy** - Making classic books accessible to young readers
- **AI Innovation** - Pushing boundaries of what's possible with AI

### Contributors
Thank you to all contributors who have helped make KidsKlassiks better!

---

## 📧 Contact & Support

- **GitHub Repository**: [github.com/Digitalgods2/KidsFastapi](https://github.com/Digitalgods2/KidsFastapi)
- **Issues**: [Report bugs or request features](https://github.com/Digitalgods2/KidsFastapi/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/Digitalgods2/KidsFastapi/discussions)

---

## 🗺️ Roadmap

### Upcoming Features (v3.1)
- [ ] User authentication and multi-user support
- [ ] Cloud storage integration (AWS S3, Google Cloud Storage)
- [ ] Advanced text transformation settings (custom vocabulary lists)
- [ ] Audio narration generation (text-to-speech)
- [ ] Multiple language support (Spanish, French, etc.)

### Future Vision (v4.0+)
- [ ] EPUB generation for digital distribution
- [ ] Publishing platform for sharing adaptations
- [ ] Collaborative editing and review
- [ ] Mobile app (iOS/Android)
- [ ] Theme builder for custom illustration styles
- [ ] Print-on-demand integration
- [ ] Reading comprehension questions generator
- [ ] Parent/teacher dashboard with analytics

### Community Requested
- [ ] Support for more book formats (MOBI, AZW3)
- [ ] Batch book import from ZIP files
- [ ] Custom character design tools
- [ ] Video book trailer generation
- [ ] Integration with educational platforms

---

## 📊 Project Statistics

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Lines of Code**: ~10,000+
- **Test Coverage**: 85%+
- **Dependencies**: 25+ Python packages
- **Database**: SQLite (default), PostgreSQL (supported)
- **API Endpoints**: 30+
- **Templates**: 20+ Jinja2 pages
- **AI Services**: OpenAI GPT-4o-mini, DALL-E 3

---

## 🌟 Success Stories

### A Christmas Carol Transformation
- **Book**: A Christmas Carol by Charles Dickens (1843)
- **Format**: Project Gutenberg TXT
- **Target Age**: 6-8 years
- **Chapters**: 17 (Staves I-V auto-detected)
- **Transformation**: 158,371 → 65,031 characters (58.9% reduction)
- **Images**: 17 chapter illustrations + 1 cover
- **Character Consistency**: Scrooge, Bob Cratchit, Tiny Tim maintained across all images
- **Result**: Professional children's book in under 30 minutes

### Typical Results
- **Processing Time**: 15-45 minutes depending on book length
- **Text Quality**: Age-appropriate, maintains story integrity
- **Image Quality**: DALL-E 3 produces professional illustrations
- **PDF Output**: Print-ready with cover and illustrations
- **User Satisfaction**: Parents and educators love the results

---

## 💡 Tips & Best Practices

### For Best Text Transformation
1. **Choose correct age group**: Match your target audience
2. **Review transformed text**: AI is good but not perfect
3. **Edit as needed**: Manual refinement improves quality
4. **Test with children**: Get feedback from actual readers

### For Best Image Generation
1. **Use character consistency**: Enable for cohesive illustrations
2. **Review and regenerate**: Don't settle for first generation
3. **Edit prompts strategically**: Be specific about scenes
4. **Generate cover last**: After all chapters are finalized

### For Publishing
1. **Complete all chapters**: Ensure 100% progress before export
2. **Review gallery**: Check all images before finalizing
3. **Test PDF**: Open and review before distribution
4. **Keep originals**: Save original book files for reference

---

**Made with ❤️ for children's literacy and AI innovation**

*Transform classics into adventures that young minds can treasure* ✨📖🎨
