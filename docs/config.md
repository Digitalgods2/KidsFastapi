# Configuration

This app reads configuration from environment variables (or .env) and config.py defaults.

Key knobs for chapter processing runs:

- STALE_RUN_TIMEOUT_SECONDS (default: 1800)
  - Purpose: Maximum time a running normalization run can stay in "running" before considered abandoned. Past this timeout, the run is marked failed (run_abandoned) and the active run is cleared.
  - Trade-offs: Too low may mark long jobs as abandoned; too high delays recovery from stuck runs.
  - How to change: export STALE_RUN_TIMEOUT_SECONDS=seconds or set in .env

- CHAPMAP_MAX_OPS (default: 2000)
  - Purpose: Bound the number of operations saved per run to avoid oversized rows and payloads.
  - Trade-offs: Lower values reduce detail in the op history; higher values increase storage and payload size.
  - How to change: export CHAPMAP_MAX_OPS=N or set in .env

- REPROCESS_COOLDOWN_SECONDS (default: 60)
  - Purpose: Per-adaptation cooldown to prevent rapid repeated processing requests.
  - Trade-offs: Lower values allow faster retries but risk load spikes; higher values reduce noisy retries.
  - How to change: export REPROCESS_COOLDOWN_SECONDS=seconds or set in .env

Apply changes by restarting the server or reloading environment.
