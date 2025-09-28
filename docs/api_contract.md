# API Contract

This document freezes response schemas and versioning policies for key endpoints.

## POST /adaptations/{id}/process_chapters

- HTMX (text/html): returns HTML fragments and sets HX-Redirect header on success to /images/adaptation/{id}/chapters.
- JSON (application/json) for API/tests:
  - 200: {"success": true, "chapters_count": int}
  - 400: {"error": "..."} for validation/guard failures (e.g., no_original_chapter_count, empty_input)
  - 409: {"error": "cooldown"}, with Retry-After header when run is rate-limited
  - 429: {"error": "cooldown"}, with Retry-After header when run is limited by cooldown

## GET /adaptations/{id}/status

- JSON:
  - Fields (status_version=1):
    - run_id: string|null
    - stage: running|normalizing|completed|failed
    - stage_detail: string
    - completion_pct: 0..100
    - last_update_ts: ISO8601
    - last_error: string|null
    - detector: regex|toc|auto_wordcount|null
    - last_run: {
        detected_count: int,
        target_count: int,
        operations_count: int,
        status: running|succeeded|failed,
        error: string|null,
        final_map: array (may be truncated in UI),
        finished_at: ISO8601|null,
        chapter_map_url: string
      }
  - Policy: Any field change requires bump to status_version and additive compatibility.

## GET /adaptations/{id}/chapter_map

- Request: offset=int>=0, limit=int[1..1000]
- JSON:
  - run_id, detected_count, target_count
  - operations: array slice
  - final_map: array slice
  - operations_total: int
  - final_map_total: int
  - offset: int
  - limit: int
  - started_at, finished_at, duration_ms, status, error

## Errors

- Standard JSON error envelope: {"error": "code_or_message"}
- 400 validation/guard errors: no_original_chapter_count, empty_input
- 409/429 cooldown: Retry-After header present
