import json
import types
import types as pytypes
import sys
import pytest

# Stub dependencies
mod = pytypes.ModuleType('services.character_analyzer')
class DummyCA:
    @staticmethod
    async def curate_for_adaptation(adaptation, chapters, default_cap: int = 25):
        return []
mod.CharacterAnalyzer = DummyCA
sys.modules['services.character_analyzer'] = mod

import routes.adaptations as routes

@pytest.mark.asyncio
async def test_status_version_is_1(monkeypatch):
    async def fake_progress(adaptation_id: int):
        return {
            "adaptation_id": adaptation_id,
            "stage": "in_progress",
            "stage_detail": "",
            "run_id": "r1",
            "last_update_ts": "2025-01-01T00:00:00Z",
            "last_error": None,
            "chapters_total": 10,
            "prompts_done": 0,
            "images_done": 1,
            "completion_pct": 10,
            "status_version": 1,
        }
    monkeypatch.setattr(routes.database, 'get_adaptation_progress', fake_progress, raising=True)
    s = await routes.adaptation_status(1)
    assert s.status_code == 200
    body = json.loads(s.body)
    assert body.get('status_version') == 1
