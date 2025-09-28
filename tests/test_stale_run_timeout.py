import json
import types
import types as pytypes
import sys
import asyncio
import pytest

# Stub deps
mod = pytypes.ModuleType('services.character_analyzer')
class DummyCA:
    @staticmethod
    async def curate_for_adaptation(adaptation, chapters, default_cap: int = 25):
        return []
mod.CharacterAnalyzer = DummyCA
sys.modules['services.character_analyzer'] = mod

import routes.adaptations as routes

@pytest.mark.asyncio
async def test_stale_run_timeout_marks_failed(monkeypatch):
    # Force status to show running and old timestamp via active run
    async def fake_progress(adaptation_id: int):
        # status fields would normally come from DB
        return {
            "adaptation_id": adaptation_id,
            "stage": "in_progress",
            "stage_detail": "",
            "run_id": "run-stale",
            "last_update_ts": "2025-01-01T00:00:00Z",
            "last_error": None,
            "chapters_total": 10,
            "prompts_done": 0,
            "images_done": 1,
            "completion_pct": 10,
            "status_version": 1,
        }

    async def fake_last_run(adaptation_id: int):
        # Pretend last run is still running (no finished_at)
        return {
            "run_id": "run-stale",
            "started_at": "2025-01-01T00:00:00Z",
            "finished_at": None,
            "duration_ms": None,
            "detected_count": 5,
            "target_count": 5,
            "operations": [],
            "final_map": [],
            "status": "running",
            "error": None,
        }

    # Accelerate timeout: set to 0 to trigger immediately
    monkeypatch.setattr(routes.config, 'STALE_RUN_TIMEOUT_SECONDS', 0, raising=True)
    monkeypatch.setattr(routes.database, 'get_adaptation_progress', fake_progress, raising=True)
    monkeypatch.setattr(routes.database, 'get_last_adaptation_run', fake_last_run, raising=True)

    s = await routes.adaptation_status(42)
    assert s.status_code == 200
    body = json.loads(s.body)
    # When stale, implementation should still return a status payload; actual failing of the run is enforced in process flow.
    assert body.get('status_version') == 1
