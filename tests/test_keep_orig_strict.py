import pytest, types, json
# flake8: noqa

import routes.adaptations as routes

class DummyDB:
    def __init__(self):
        self._writes = 0
        self._runs = []
        self._lock = False
        self._active = None
    async def try_acquire_adaptation_lock(self, adaptation_id:int):
        if self._lock:
            return None
        self._lock = True
        return object()
    async def release_adaptation_lock(self, conn):
        self._lock = False
    def set_current_run(self, adaptation_id, run_id):
        pass
    async def get_adaptation_details(self, adaptation_id:int):
        return {"adaptation_id": adaptation_id, "book_id": 1, "chapter_structure_choice": "Keep original"}
    async def get_book_details(self, book_id:int):
        return {"book_id": book_id, "chapter_count": 0, "original_content_path": "/dev/null"}
    async def create_adaptation_run(self, adaptation_id, run_id, detected_count, target_count, started_at):
        self._runs.append({"run_id": run_id, "status": "running"})
        return True
    async def finish_adaptation_run(self, run_id, finished_at, duration_ms, operations, final_map, status, error, meta=None):
        for r in self._runs:
            if r["run_id"] == run_id:
                r.update({"status": status, "error": error})
        return True
    async def clear_active_run(self, adaptation_id:int):
        pass
    async def get_chapters_for_adaptation(self, adaptation_id:int):
        return []
    async def replace_adaptation_chapters(self, adaptation_id, segments):
        self._writes += 1
        return True

class DummyTransformer:
    def __init__(self):
        self.last_method = None
    def detect_chapters_in_text(self, content: str):
        return []

@pytest.mark.asyncio
async def test_keep_original_first_run_guard(monkeypatch):
    db = DummyDB()
    tx = DummyTransformer()
    monkeypatch.setattr(routes, 'database', db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', tx, raising=True)

    resp = await routes.process_chapters(adaptation_id=1, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 400
    body = json.loads(resp.body)
    assert body.get('error') == 'no_original_chapter_count'
    # No writes
    assert db._writes == 0
