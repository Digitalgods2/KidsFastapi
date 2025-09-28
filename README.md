# KidsKlassiks

See ./docs for configuration, API contract, and metrics/logging checklists.

## Quick start

- Set database location (SQLite):
  - export DATABASE_URL="sqlite:///./kidsklassiks.db"  # default if unset
- Run the app:
  - uvicorn main:app --reload --port 8000

## Smoke test steps

1) Import a test book (UI: Books → Import)
2) Open Adaptations for the book and click "Reprocess Chapters" (HTMX)
3) Visit Images → Chapters to see chapter rows and image fields
4) Check legacy status API: GET /images/adaptation/{adaptation_id}/status
5) Review page: GET /review/adaptation/{adaptation_id}

## Notes
- Database path is resolved relative to project root when using sqlite:///.
- Generated images are stored under generated_images/{book_id}. Deleting a book removes its folder.

