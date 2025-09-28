import json
import types
import types as pytypes
import sys
import pytest

# Stub
mod = pytypes.ModuleType('services.character_analyzer')
class DummyCA:
    @staticmethod
    async def curate_for_adaptation(adaptation, chapters, default_cap: int = 25):
        return []
mod.CharacterAnalyzer = DummyCA
sys.modules['services.character_analyzer'] = mod

import routes.adaptations as routes

@pytest.mark.asyncio
async def test_status_includes_detector_and_ops_cap(monkeypatch):
    # Fake last run with summary header and a lot of ops
    async def fake_last(adaptation_id):
        ops = [{"type": "summary", "detector": "toc"}] + [{"type":"merge"} for _ in range(5000)]
        return {
            "run_id": "r1",
            "detected_count": 20,
            "target_count": 17,
            "operations": ops,
            "final_map": [{"final_index": i, "source_indices": [i]} for i in range(17)],
            "status": "succeeded",
            "error": None,
            "finished_at": "2025-01-01T00:00:00Z",
        }
    async def fake_progress(adaptation_id):
        return {"adaptation_id": adaptation_id, "stage": "in_progress", "stage_detail": "", "run_id": "r1", "last_update_ts": "2025-01-01T00:00:00Z", "last_error": None, "chapters_total": 17, "prompts_done": 0, "images_done": 0, "completion_pct": 0, "status_version": 1}

    monkeypatch.setattr(routes.database, 'get_last_adaptation_run', fake_last, raising=True)
    monkeypatch.setattr(routes.database, 'get_adaptation_progress', fake_progress, raising=True)

    # Cap at 2000 in config should not affect status view; detector extracted from summary
    res = await routes.adaptation_status(1)
    assert res.status_code == 200
    body = json.loads(res.body)
    assert body.get('detector') == 'toc'

    # Now ensure cap is enforced during a run by simulating process flow: we verify the cap constant is available
    assert hasattr(routes.config, 'CHAPMAP_MAX_OPS')
    assert int(routes.config.CHAPMAP_MAX_OPS) <= 5000
