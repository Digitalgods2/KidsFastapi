# KidsKlassiks (FastAPI + HTMX)

KidsKlassiks is a FastAPI app with HTMX-powered UI for importing books, analyzing chapters, generating and reviewing images per chapter, and tracking processing runs. It uses SQLite by default and stores generated images per-book.

- Tech: FastAPI, Jinja2 templates, HTMX for partial updates
- Default DB: SQLite (configurable via DATABASE_URL)
- Storage: generated_images/{book_id} for per-book images
- Images APIs include a legacy alias: /images/adaptation/{id}/status
- HTMX actions return partial templates instead of redirects
- Run-tracking/locking prevents overlapping chapter processing runs


## Table of contents
- Quick start
- Requirements and installation
- Configuration
- Running the app
- End-to-end smoke test
- Core features and behavior
- API notes and endpoints
- Data storage and cleanup
- Testing
- Development notes
- Troubleshooting


## Quick start

- Set database location (SQLite):
  - export DATABASE_URL="sqlite:///./kidsklassiks.db"  # default if unset
- Install dependencies:
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
- Run the app:
  - uvicorn main:app --reload --port 8000


## Requirements and installation
- Python: 3.11+ (3.12 supported)
- Recommended: virtual environment
- Install:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

Optional tools:
- pytest for tests: pip install -r requirements.txt (already included)


## Configuration
- DATABASE_URL (optional):
  - Defaults to sqlite:///./kidsklassiks.db
  - Examples:
    - SQLite file in project root: export DATABASE_URL="sqlite:///./kidsklassiks.db"
    - Absolute SQLite path: export DATABASE_URL="sqlite:////abs/path/kidsklassiks.db"
- Generated images path:
  - generated_images/{book_id} will be created on import
- Optional AI keys (if using image/LLM integrations):
  - Set provider-specific keys as needed; not required for tests or basic flows

Example .env.sample (do not commit real secrets):

DATABASE_URL=sqlite:///./kidsklassiks.db
# OPENAI_API_KEY=sk-...
# OTHER_PROVIDER_KEY=...


## Running the app
- Start the server:
  - uvicorn main:app --reload --port 8000
- Visit the UI in your browser: http://localhost:8000/

Notes:
- On startup, auxiliary tables for run tracking are ensured.
- The app resolves SQLite paths relative to the project root when using sqlite:///.


## End-to-end smoke test
1) Import a test book via UI: Books → Import
2) Navigate to the Adaptation created for the book
3) Click "Reprocess Chapters" (HTMX) — the chapters table updates without a full-page reload
4) Open Images → Chapters to see chapter rows with mapped fields
5) Verify legacy status API:
   - GET /images/adaptation/{adaptation_id}/status
   - Expect counters such as total_chapters, completed, pending
6) Review page:
   - GET /review/adaptation/{adaptation_id}


## Core features and behavior
- HTMX partial updates
  - Chapter processing (process_chapters) returns the chapters table partial for HX requests, not a redirect. This avoids blank pages and improves UX.
- Run tracking and locking
  - Advisory lock prevents overlapping reprocess runs per adaptation.
  - Lifecycle hooks tolerate test DBs (no-op if DB doesn’t implement run-tracking methods).
- Stable SQLite path
  - DATABASE_URL default ensures a stable sqlite file path in project root.
- Images storage and cleanup
  - On import, generated_images/{book_id} is created.
  - Deleting a book removes its generated_images folder via delete_book_completely.
- Legacy status alias
  - /images/adaptation/{id}/status is mounted and returns counters for images generation status.


## API notes and endpoints
- Images status (legacy alias):
  - GET /images/adaptation/{adaptation_id}/status → { total_chapters, completed, pending, ... }
- Reprocess chapters (HTMX-enabled)
  - Triggered from the Adaptation page via "Reprocess Chapters"
  - Returns a partial template with the updated chapters table when HX-Request is true
- Review page
  - GET /review/adaptation/{adaptation_id}

Tip: use browser dev tools to verify HTMX requests/partials.


## Data storage and cleanup
- SQLite database file: kidsklassiks.db in project root by default
- Generated images: generated_images/{book_id}
- Uploads: uploads/
- Exports: exports/

When deleting a book, generated_images/{book_id} is removed. Ensure no external process holds file locks.


## Testing
- Run the full test suite:
  - pytest
- Expected: 50 passed, 1 warning (legacy OpenAI import fallback)
- Notes:
  - Tests include end-to-end flow, images status alias, and HTMX partial behavior
  - Async event loop guards are in place to avoid RuntimeError in Python 3.12


## Development notes
- Templates: templates/
- Routes: routes/
- Services/DB helpers: services/, database_fixed.py
- Static assets: static/
- Tests: tests/
- HTMX components: templates/components/ (e.g., chapters_table.html)

Contributions:
- Create a feature branch
- Open a PR with a description and verification steps


## Troubleshooting
- Blank page after reprocess
  - Ensure HTMX requests return partials; this app returns the chapters table partial for HX requests.
- SQLite locking or path issues
  - Verify DATABASE_URL is set correctly; for relative paths use sqlite:///./kidsklassiks.db
- Concurrent reprocess clicks
  - Advisory lock prevents overlapping runs; try again once the lock clears
- Event loop errors (tests)
  - We guard event loop creation in tests and at module import for Python 3.12


