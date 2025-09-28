import pytest, types, json
import routes.adaptations as routes

import tempfile, os

class DummyDB:
    def __init__(self, ops_cap=10):
        self._ops_cap = ops_cap
        self._run = None
        self._saved = None
        self._tmp = None
    async def try_acquire_adaptation_lock(self, adaptation_id:int):
        return object()
    async def release_adaptation_lock(self, conn):
        pass
    def set_current_run(self, adaptation_id, run_id):
        pass
    async def get_adaptation_details(self, adaptation_id:int):
        return {"adaptation_id": adaptation_id, "book_id": 1, "chapter_structure_choice": "Keep original"}
    async def get_book_details(self, book_id:int):
        # Create a temp file with a lot of small paragraphs to force many merges
        if not self._tmp:
            fd, path = tempfile.mkstemp(prefix='book_', suffix='.txt')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(["para" for _ in range(500)]))
            self._tmp = path
        return {"book_id": book_id, "chapter_count": 10, "original_content_path": self._tmp}
    async def create_adaptation_run(self, adaptation_id, run_id, detected_count, target_count, started_at):
        self._run = {"run_id": run_id, "detected_count": detected_count, "target_count": target_count}
        return True
    async def finish_adaptation_run(self, run_id, finished_at, duration_ms, operations, final_map, status, error, meta=None):
        self._saved = {"operations": operations, "meta": meta}
        return True
    async def clear_active_run(self, adaptation_id:int):
        pass
    async def get_chapters_for_adaptation(self, adaptation_id:int):
        return []
    async def replace_adaptation_chapters(self, adaptation_id, segments):
        return True

class DummyTransformer:
    def __init__(self, n=200):
        self.last_method = 'regex'
        self._n = n
    def detect_chapters_in_text(self, content: str):
        # produce n tiny segments to force many ops
        return [{"content": "x"} for _ in range(self._n)]

@pytest.mark.asyncio
async def test_ops_are_capped(monkeypatch):
    # Force a very small cap
    monkeypatch.setattr(routes.config, 'CHAPMAP_MAX_OPS', 10, raising=True)
    db = DummyDB()
    tx = DummyTransformer(n=500)
    monkeypatch.setattr(routes, 'database', db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', tx, raising=True)

    resp = await routes.process_chapters(adaptation_id=2, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 200
    # ensure saved operations never exceed cap
    assert db._saved is not None
    ops = db._saved['operations']
    assert isinstance(ops, list)
    assert len(ops) <= 10
    # summary should include counters
    meta = db._saved['meta'] or {}
    assert 'merge_ops' in meta and 'split_ops' in meta
