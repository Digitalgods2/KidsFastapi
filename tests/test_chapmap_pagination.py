import json
import types
import types as pytypes
import sys
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

class DummyDB:
    def __init__(self):
        pass
    async def get_last_adaptation_run(self, adaptation_id):
        ops = [{"type":"merge","from":[i,i+1],"to":i} for i in range(100)]
        fm = [{"final_index": i, "source_indices": [i]} for i in range(100)]
        return {
            "run_id": "r",
            "detected_count": 100,
            "target_count": 100,
            "operations": ops,
            "final_map": fm,
            "started_at": "2025-01-01T00:00:00Z",
            "finished_at": "2025-01-01T00:10:00Z",
            "duration_ms": 600000,
            "status": "succeeded",
            "error": None,
        }

@pytest.mark.asyncio
async def test_chapter_map_pagination(monkeypatch):
    db = DummyDB()
    monkeypatch.setattr(routes, 'database', db, raising=True)
    # first page
    res1 = await routes.get_chapter_map(1, offset=0, limit=10)
    assert res1.status_code == 200
    b1 = json.loads(res1.body)
    assert b1['operations_total'] == 100
    assert len(b1['operations']) == 10
    assert b1['offset'] == 0 and b1['limit'] == 10
    # second page
    res2 = await routes.get_chapter_map(1, offset=10, limit=10)
    assert res2.status_code == 200
    b2 = json.loads(res2.body)
    assert b2['operations'][0]['from'] == [10,11]
    assert b2['final_map'][0]['final_index'] == 10
