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
        self._active = None
    async def try_acquire_adaptation_lock(self, adaptation_id):
        return object()
    async def release_adaptation_lock(self, conn):
        return True
    def get_current_run(self, adaptation_id):
        return None
    def set_current_run(self, adaptation_id, run_id):
        pass
    async def get_adaptation_details(self, adaptation_id):
        return {"adaptation_id": adaptation_id, "book_id": 1}
    async def get_book_details(self, book_id):
        return {"book_id": 1, "original_content_path": "/dev/null"}
    async def get_active_run(self, adaptation_id):
        return self._active
    async def upsert_active_run(self, adaptation_id, run_id, stage='normalizing'):
        self._active = {"run_id": run_id, "stage": stage, "updated_at": self._active.get('updated_at') if self._active else None}
    async def create_adaptation_run(self, *a, **k):
        return True
    async def finish_adaptation_run(self, *a, **k):
        return True
    async def replace_adaptation_chapters(self, *a, **k):
        return True
    async def clear_active_run(self, adaptation_id):
        self._active = None

@pytest.mark.asyncio
async def test_rate_limit_returns_429(monkeypatch):
    db = DummyDB()
    monkeypatch.setattr(routes, 'database', db, raising=True)
    # Set cooldown to a very large number to force rate-limit
    monkeypatch.setattr(routes.config, 'REPROCESS_COOLDOWN_SECONDS', 9999, raising=True)
    # Pretend an active run started just now
    from datetime import datetime, timezone
    db._active = {"run_id": "r1", "stage": "normalizing", "updated_at": datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}

    resp = await routes.process_chapters(adaptation_id=123, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 429
    body = json.loads(resp.body)
    assert body.get('error') == 'rate_limited'
    assert 'retry_after_seconds' in body
