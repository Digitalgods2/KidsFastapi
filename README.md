# 📚 KidsKlassiks - AI-Powered Children's Book Transformer

> Transform classic literature into beautifully illustrated children's books using AI

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

KidsKlassiks is a full-stack web application that uses AI to adapt classic literature for young readers. It analyzes books, transforms content for specific age groups, generates custom illustrations, and produces print-ready publications.

---

## ✨ Features

### 📖 Book Management
- **Import Books**: Upload EPUB, PDF, or TXT files
- **Metadata Extraction**: Automatic title, author, and chapter detection
- **Library Organization**: Browse and manage your book collection
- **Character Analysis**: AI-powered character identification and preservation

### 🎨 Intelligent Adaptation
- **Age-Appropriate Transformation**: Tailor content for ages 3-5, 6-8, or 9-12
- **Style Selection**: Choose transformation styles (simplified, educational, imaginative)
- **Theme Customization**: Set overall tone (adventure, educational, whimsical, etc.)
- **Smart Chapter Segmentation**: Auto-detect or manually configure chapter structure

### 🖼️ AI Image Generation
- **Multiple AI Backends**: Support for DALL-E 3, Vertex AI, and more
- **Per-Chapter Illustrations**: Generate custom images for each chapter
- **Image Review & Regeneration**: 
  - View all generated images in a beautiful gallery
  - Edit prompts and regenerate unsatisfactory images
  - Quick regenerate with same prompt or create custom variations
  - Delete and replace images
- **Cover Art Generation**: Create stunning book covers
- **Batch Processing**: Generate multiple images simultaneously

### 📊 Processing Pipeline
- **Visual Progress Tracking**: Real-time status updates
- **Run History**: Track all processing runs with detailed logs
- **Chapter Mapping**: Intelligent chapter detection and normalization
- **Error Recovery**: Graceful handling of failures with retry capabilities

### 📝 Review & Editing
- **Chapter Preview**: Review transformed content before finalizing
- **Inline Editing**: Edit chapter titles and content
- **Image Management**: Review, approve, or regenerate illustrations
- **Quality Control**: Ensure consistency across all chapters

### 📤 Publishing
- **PDF Export**: Generate print-ready PDFs (coming soon)
- **EPUB Generation**: Create digital ebooks (coming soon)
- **Publishing Platform**: Share adaptations online (coming soon)

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (Python 3.12 supported)
- **Virtual Environment** (recommended)
- **OpenAI API Key** (for image generation)

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

# OpenAI API Key (required for image generation)
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
```

### Running the Application

```bash
# Start the development server
uvicorn main:app --reload --port 8000

# The application will be available at:
# http://localhost:8000
```

---

## 📖 User Guide

### 1. Import a Book

1. Navigate to **Books** → **Import**
2. Upload a book file (EPUB, PDF, or TXT)
3. Enter book details (title, author, original chapter count)
4. Click **Import Book**

### 2. Create an Adaptation

1. Go to **Adaptations** → **Create New**
2. Select a book from your library
3. Choose target age group (3-5, 6-8, or 9-12)
4. Select transformation style and theme
5. Specify key characters to preserve (optional)
6. Choose chapter structure (keep original or auto-segment)
7. Click **Create Adaptation**

### 3. Process Chapters

1. Click **Process** on your adaptation
2. Click **Reprocess Chapters** to start the pipeline
3. Watch the progress in real-time
4. Review the chapter mapping and operations performed

### 4. Generate Images

#### Option A: Batch Generation
1. Click **Generate All Images** from the adaptation view
2. Select your preferred image backend
3. Monitor batch progress
4. Review all generated images

#### Option B: Individual Generation
1. Navigate to **Images** → **Chapters**
2. Click **Generate** on individual chapters
3. Edit prompts before generation (optional)
4. Review and approve images

### 5. Review & Edit

1. Go to the adaptation detail page (`/adaptations/{id}`)
2. View all chapters in list or grid view
3. Click on any chapter to:
   - View full content
   - Edit title and text
   - View associated image
4. Click on image thumbnails to:
   - View full-size image
   - See the generation prompt
   - Regenerate with same prompt
   - Edit prompt and regenerate
   - Delete the image

### 6. Review Images

The image review modal provides comprehensive controls:

- **View Mode**: Large preview with chapter details
- **Quick Regenerate**: Use the same prompt to get a variation
- **Edit & Regenerate**: Modify the prompt for different results
- **Delete**: Remove unsatisfactory images
- **Prompt Display**: See exactly what was used to generate the image

---

## 🏗️ Architecture

### Technology Stack

**Backend:**
- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database (default)
- **Pydantic**: Data validation
- **Asyncio**: Async/await support

**Frontend:**
- **HTMX**: Dynamic updates without page reloads
- **Jinja2**: Server-side templating
- **Bootstrap 5**: Responsive UI framework
- **Alpine.js**: Reactive components

**AI Services:**
- **OpenAI GPT-4**: Content transformation
- **DALL-E 3**: Image generation
- **Vertex AI**: Alternative image backend (optional)

### Project Structure

```
KidsKlassiks/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── database_fixed.py      # Database operations
├── models.py              # Data models
├── requirements.txt       # Python dependencies
│
├── routes/                # API endpoints
│   ├── adaptations.py     # Adaptation management
│   ├── books.py           # Book import & management
│   ├── chapters.py        # Chapter CRUD operations
│   ├── images.py          # Batch image generation
│   ├── images_individual.py # Single image operations
│   ├── images_gallery.py  # Image gallery views
│   ├── review.py          # Review & editing
│   ├── publish.py         # Publishing features
│   ├── settings.py        # Application settings
│   └── health.py          # Health checks
│
├── services/              # Business logic
│   ├── image_generation_service.py
│   ├── transformation_service.py
│   ├── character_analyzer.py
│   ├── chat_helper.py
│   └── logger.py
│
├── templates/             # HTML templates
│   ├── layouts/           # Base templates
│   ├── pages/             # Full page views
│   └── components/        # Reusable components
│
├── static/                # Static assets
│   ├── css/               # Stylesheets
│   ├── js/                # JavaScript
│   └── images/            # Static images
│
├── tests/                 # Test suite
│   ├── test_books.py
│   ├── test_adaptations.py
│   └── test_images.py
│
├── legacy/                # Legacy code (compatibility)
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

---

## 🔌 API Endpoints

### Books
- `GET /books/` - List all books
- `GET /books/{id}` - Get book details
- `POST /books/import` - Import new book
- `DELETE /books/{id}` - Delete book

### Adaptations
- `GET /adaptations/` - List all adaptations
- `GET /adaptations/{id}` - View adaptation details (NEW)
- `GET /adaptations/create` - Create adaptation page
- `POST /adaptations/create` - Create new adaptation
- `GET /adaptations/{id}/process` - Processing page
- `POST /adaptations/{id}/process_chapters` - Start chapter processing
- `GET /adaptations/{id}/status` - Get processing status
- `DELETE /adaptations/{id}` - Delete adaptation

### Chapters (NEW)
- `GET /chapters/{id}/details` - Get chapter details
- `POST /chapters/{id}/update` - Update chapter
- `POST /chapters/{id}/generate-image` - Generate/regenerate image
- `POST /chapters/{id}/regenerate-image` - Quick regenerate
- `DELETE /chapters/{id}/image` - Delete chapter image

### Images
- `GET /images/{adaptation_id}/images` - View all images
- `POST /images/{adaptation_id}/generate_batch` - Batch generate
- `GET /images/{adaptation_id}/generation_status` - Get status
- `POST /images/{adaptation_id}/regenerate_image` - Regenerate single

### Review
- `GET /review/adaptation/{id}` - Review adaptation page

### Health
- `GET /health` - Liveness check
- `GET /ready` - Readiness check (DB, image backend, cache)

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_books.py

# Run with verbose output
pytest -v
```

**Expected Results:**
- ✅ 50+ tests passing
- ⚠️ 1 warning (legacy OpenAI import fallback)

---

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./kidsklassiks.db` |
| `OPENAI_API_KEY` | OpenAI API key (required) | None |
| `DEFAULT_IMAGE_BACKEND` | Image generation backend | `dall-e-3` |
| `MAX_BATCH_SIZE` | Max images per batch | `50` |
| `REPROCESS_COOLDOWN_SECONDS` | Cooldown between runs | `30` |
| `STALE_RUN_TIMEOUT_SECONDS` | Run timeout before abandonment | `300` |
| `CHAPMAP_MAX_OPS` | Max chapter mapping operations | `1000` |

### Supported Image Backends

- **dall-e-3** (OpenAI DALL-E 3) - Default
- **dall-e-2** (OpenAI DALL-E 2)
- **vertex-imagen** (Google Vertex AI Imagen)
- More backends can be added in `services/backends.py`

---

## 🎨 Features Deep Dive

### Image Review & Regeneration (NEW)

The latest update includes a comprehensive image review system:

#### **Enhanced Image Modal**
- **Large Preview**: View images in full quality
- **Prompt Display**: See exactly what prompt was used
- **Chapter Context**: View chapter number and title
- **Quick Actions**: Regenerate, edit, or delete with one click

#### **Regeneration Options**
1. **Same Prompt**: Quick variation with identical prompt
2. **Custom Prompt**: Edit the prompt for different results
3. **Delete**: Remove and start fresh

#### **Loading States**
- Visual indicators during generation
- Progress feedback
- Success/error notifications

#### **Auto-Refresh**
- Automatic page reload after generation
- Cache-busting to show latest images
- Seamless user experience

### Chapter Detection & Normalization

The application uses intelligent chapter detection:

#### **Detection Methods**
1. **Table of Contents Parsing**: Extracts chapter structure from ToC
2. **Regex Pattern Matching**: Finds chapter markers in text
3. **Auto-Segmentation**: Splits by word count for age-appropriate chunks

#### **Normalization Process**
- **Merge Operations**: Combine short chapters to reach target count
- **Split Operations**: Divide long chapters for better pacing
- **Audit Trail**: Track all operations for transparency
- **Final Mapping**: Map original to normalized chapters

### Character Preservation

AI-powered character analysis ensures consistency:

- **Automatic Detection**: Identifies main characters from text
- **Frequency Ranking**: Prioritizes important characters
- **User Override**: Manually specify characters to preserve
- **Consistent References**: Maintains character names across adaptations

---

## 🚢 Deployment

### Production Considerations

```bash
# Use production ASGI server
pip install gunicorn uvicorn[standard]

# Run with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use Uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Environment Setup

```bash
# Set production environment variables
export DATABASE_URL="postgresql://user:pass@localhost/kidsklassiks"
export OPENAI_API_KEY="sk-production-key"
export MAX_BATCH_SIZE="100"
```

### Database Migration

```bash
# For production, consider PostgreSQL
# Update DATABASE_URL in .env:
DATABASE_URL=postgresql://user:password@localhost/kidsklassiks

# The application will auto-create tables on startup
```

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Write/update tests**
5. **Commit your changes**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
6. **Push to your branch**
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open a Pull Request**

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `chore:` Maintenance tasks
- `refactor:` Code refactoring
- `test:` Test additions/changes

---

## 🐛 Troubleshooting

### Common Issues

#### Server won't start
```bash
# Check if port is already in use
lsof -i :8000

# Try a different port
uvicorn main:app --port 8001
```

#### Database errors
```bash
# Delete and recreate database
rm kidsklassiks.db
# Restart the server - database will be recreated
```

#### Import errors
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

#### Image generation fails
```bash
# Check API key
echo $OPENAI_API_KEY

# Verify backend setting
python -c "import config; print(config.OPENAI_API_KEY)"
```

#### HTMX not updating
- Clear browser cache
- Check browser console for errors
- Verify HTMX is loaded (check Network tab)

### Debug Mode

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

---

## 📝 Changelog

### Version 2.0.0 (Latest)

#### New Features ✨
- **Image Review System**: Comprehensive modal for reviewing and regenerating images
- **Chapter Management API**: New `/chapters` endpoints for CRUD operations
- **Adaptation View Page**: Dedicated page for viewing adaptation details
- **Enhanced Image Controls**: Edit prompts, regenerate, or delete images
- **Progress Indicators**: Visual feedback for all operations

#### Improvements 🔧
- **Massive Cleanup**: Moved 54 legacy files to `old/` directory
- **Cleaner Repository**: Root directory reduced from 80+ to ~15 essential files
- **Better Organization**: Logical file structure and clear separation
- **Updated Documentation**: Comprehensive README and cleanup docs

#### Bug Fixes 🐛
- Fixed 405 error when accessing `/adaptations/{id}` directly
- Fixed database import references in health and publish routes
- Improved error handling in image generation

### Version 1.0.0

- Initial release
- Book import and management
- AI-powered adaptation
- Chapter processing
- Basic image generation

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern web framework
- **HTMX** - Dynamic HTML updates
- **OpenAI** - AI capabilities
- **Bootstrap** - UI framework
- All contributors and testers

---

## 📧 Contact & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/Digitalgods2/KidsFastapi/issues)
- **Repository**: [github.com/Digitalgods2/KidsFastapi](https://github.com/Digitalgods2/KidsFastapi)

---

## 🗺️ Roadmap

### Upcoming Features

- [ ] PDF Export for print-ready books
- [ ] EPUB generation for digital distribution
- [ ] Publishing platform for sharing adaptations
- [ ] Multi-language support
- [ ] Advanced character customization
- [ ] Theme builder for custom styles
- [ ] Collaborative editing
- [ ] Cloud storage integration
- [ ] Mobile app

---

**Made with ❤️ for children's literacy and AI innovation**
