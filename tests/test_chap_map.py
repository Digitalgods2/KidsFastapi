import json
import types
import asyncio
import sys
import types as pytypes
import importlib
import pytest

# Provide a dummy services.character_analyzer module before importing routes
mod = pytypes.ModuleType('services.character_analyzer')
class DummyCA:
    @staticmethod
    async def curate_for_adaptation(adaptation, chapters, default_cap: int = 25):
        return []
mod.CharacterAnalyzer = DummyCA
sys.modules['services.character_analyzer'] = mod

# Provide a dummy services.chat_helper too, to avoid importing OpenAI
mod2 = pytypes.ModuleType('services.chat_helper')
async def _gen(messages, model=None, temperature=0.7, max_tokens=800):
    return ("", None)
mod2.generate_chat_text = _gen
sys.modules['services.chat_helper'] = mod2

import routes.adaptations as routes

class DummyDB:
    def __init__(self, initial_chapters=None, book_path=None):
        self._chapters = list(initial_chapters or [])
        self._replaced_payloads = []
        self._runs = {}
        self._last_run = None
        self._book_path = book_path
        self._current_runs = {}
    async def get_adaptation_details(self, adaptation_id):
        return {"adaptation_id": adaptation_id, "book_id": 1}
    async def get_book_details(self, book_id):
        return {"book_id": book_id, "chapter_count": 17, "original_content_path": self._book_path}
    async def get_chapters_for_adaptation(self, adaptation_id):
        return [
            {"chapter_number": i+1, "original_text_segment": t}
            for i, t in enumerate(self._chapters)
        ]
    async def replace_adaptation_chapters(self, adaptation_id, texts):
        # transactional replace simulation
        self._chapters = list(texts)
        return True
    async def try_acquire_adaptation_lock(self, adaptation_id):
        # any truthy value works for code path
        return object()
    async def release_adaptation_lock(self, conn):
        return True
    def set_current_run(self, adaptation_id, run_id):
        self._current_runs[adaptation_id] = run_id
    def get_current_run(self, adaptation_id):
        return self._current_runs.get(adaptation_id)
    def clear_current_run(self, adaptation_id):
        self._current_runs.pop(adaptation_id, None)

    async def upsert_active_run(self, adaptation_id, run_id, stage='starting'):
        # no-op for test double to satisfy routes call
        self._current_runs[adaptation_id] = run_id
        return True
    async def get_active_run(self, adaptation_id):
        rid = self._current_runs.get(adaptation_id)
        if not rid:
            return None
        return {"run_id": rid, "updated_at": None}
    async def clear_active_run(self, adaptation_id):
        self._current_runs.pop(adaptation_id, None)

    async def create_adaptation_run(self, adaptation_id, run_id, detected_count, target_count, started_at):
        self._runs[run_id] = {
            "adaptation_id": adaptation_id,
            "detected_count": detected_count,
            "target_count": target_count,
            "started_at": started_at,
            "status": "running",
        }
        self._last_run = run_id
        return True
    async def finish_adaptation_run(self, run_id, finished_at, duration_ms, operations, final_map, status, error):
        r = self._runs.get(run_id, {})
        r.update({
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "operations": operations,
            "final_map": final_map,
            "status": status,
            "error": error,
        })
        self._runs[run_id] = r
        return True
    async def get_last_adaptation_run(self, adaptation_id):
        if not self._last_run:
            return None
        r = self._runs[self._last_run]
        return {
            "run_id": self._last_run,
            "detected_count": r.get("detected_count"),
            "target_count": r.get("target_count"),
            "operations": r.get("operations"),
            "final_map": r.get("final_map"),
            "status": r.get("status"),
            "error": r.get("error"),
            "finished_at": r.get("finished_at"),
            "updated_at": r.get("finished_at"),
        }

class DummyTransformer:
    def __init__(self, detected_segments):
        self.detected_segments = detected_segments
    def detect_chapters_in_text(self, content):
        # return shape of existing implementation: list of dicts with 'content'
        return [{"content": s} for s in self.detected_segments]

@pytest.mark.asyncio
async def test_chap_map_deterministic_merge_to_target(monkeypatch):
    # Build 26 detected segments with varying word lengths; content content_i has i words
    detected = [" ".join(["w"]*(i+1)) for i in range(26)]

    dummy_db = DummyDB(initial_chapters=None, book_path="/dev/null")
    dummy_tx = DummyTransformer(detected)

    # Patch database and transformation service in routes.adaptations
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    # Also patch file reading path resolver to None branch
    # Invoke handler
    resp = await routes.process_chapters(adaptation_id=123, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get('success') is True
    assert body.get('chapters_count') == 17  # target from book

    # Validate last run mapping and determinism aspects
    last = await dummy_db.get_last_adaptation_run(123)
    assert last is not None
    assert last['status'] == 'succeeded'
    assert last['detected_count'] == 26
    assert last['target_count'] == 17
    fm = last['final_map']
    assert isinstance(fm, list)
    assert len(fm) == 17
    # Ensure each entry has source_indices, non-empty
    assert all('source_indices' in e and isinstance(e['source_indices'], list) and len(e['source_indices'])>=1 for e in fm)

@pytest.mark.asyncio
async def test_chap_map_empty_input_failure(monkeypatch):
    dummy_db = DummyDB(initial_chapters=None, book_path="/dev/null")
    dummy_tx = DummyTransformer(detected_segments=[])  # no segments
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    resp = await routes.process_chapters(adaptation_id=999, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 400
    body = json.loads(resp.body)
    assert body.get('success') is False
    # run should be failed and chapters untouched
    last = await dummy_db.get_last_adaptation_run(999)
    assert last['status'] == 'failed'
    assert last['detected_count'] == 0

@pytest.mark.asyncio
async def test_chap_map_rerun_determinism(monkeypatch):
    detected = [" ".join(["w"]*(i+1)) for i in range(26)]
    dummy_db = DummyDB(initial_chapters=None, book_path="/dev/null")
    dummy_tx = DummyTransformer(detected)
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    resp1 = await routes.process_chapters(adaptation_id=321, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp1.status_code == 200
    last1 = await dummy_db.get_last_adaptation_run(321)
    fm1 = last1['final_map']
    ops1 = last1['operations']

    resp2 = await routes.process_chapters(adaptation_id=321, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp2.status_code == 200
    last2 = await dummy_db.get_last_adaptation_run(321)
    fm2 = last2['final_map']
    ops2 = last2['operations']

    assert fm1 == fm2
    assert ops1 == ops2
    # idempotency: chapters remain 17 with same segmentation boundaries count
    assert len(dummy_db._chapters) == 17


@pytest.mark.asyncio
async def test_chap_map_split_dominant(monkeypatch):
    # 12 detected -> need 5 splits to reach 17
    detected = ["word" for _ in range(12)]  # each is one word, so splits will be on mid-text
    dummy_db = DummyDB(initial_chapters=None, book_path="/dev/null")
    dummy_tx = DummyTransformer(detected)
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    resp = await routes.process_chapters(adaptation_id=555, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 200
    last = await dummy_db.get_last_adaptation_run(555)
    assert last['target_count'] == 17
    fm = last['final_map']
    assert len(fm) == 17
    # Check mapping validity
    for e in fm:
        assert isinstance(e['source_indices'], list)
        assert all(0 <= i < 12 for i in e['source_indices'])


@pytest.mark.asyncio
async def test_chap_map_midrun_crash_no_partials(monkeypatch):
    detected = [" ".join(["w"]*(i+1)) for i in range(10)]
    # Start with initial chapters present to detect unintended writes
    dummy_db = DummyDB(initial_chapters=["orig1", "orig2"], book_path="/dev/null")
    dummy_tx = DummyTransformer(detected)
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    async def boom(*args, **kwargs):
        raise RuntimeError("boom during replace")
    monkeypatch.setattr(dummy_db, 'replace_adaptation_chapters', boom, raising=True)

    resp = await routes.process_chapters(adaptation_id=777, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code == 400
    # Ensure no partial writes
    assert dummy_db._chapters == ["orig1", "orig2"]
    last = await dummy_db.get_last_adaptation_run(777)
    assert last['status'] == 'failed'


@pytest.mark.asyncio
async def test_chap_map_replace_failure(monkeypatch):
    detected = [" ".join(["w"]*(i+1)) for i in range(8)]
    dummy_db = DummyDB(initial_chapters=["keep"], book_path="/dev/null")
    dummy_tx = DummyTransformer(detected)
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    async def nope(*args, **kwargs):
        return False
    monkeypatch.setattr(dummy_db, 'replace_adaptation_chapters', nope, raising=True)

    resp = await routes.process_chapters(adaptation_id=888, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp.status_code in (400, 500)
    body = json.loads(resp.body)
    assert 'persist' in body.get('error', '').lower()
    # ensure not overwritten
    assert dummy_db._chapters == ["keep"]
    last = await dummy_db.get_last_adaptation_run(888)
    assert last['status'] == 'failed'


@pytest.mark.asyncio
async def test_concurrent_lock_returns_409(monkeypatch):
    detected = ["ok" for _ in range(5)]
    dummy_db = DummyDB(initial_chapters=None, book_path="/dev/null")
    dummy_tx = DummyTransformer(detected)
    # Override lock behavior to simulate contention
    lock_state = {"taken": False}
    async def lock_fn(aid):
        if not lock_state["taken"]:
            lock_state["taken"] = True
            return object()
        return None
    async def release_fn(conn):
        lock_state["taken"] = False
        return True
    monkeypatch.setattr(dummy_db, 'try_acquire_adaptation_lock', lock_fn, raising=True)
    monkeypatch.setattr(dummy_db, 'release_adaptation_lock', release_fn, raising=True)
    monkeypatch.setattr(routes, 'database', dummy_db, raising=True)
    monkeypatch.setattr(routes, 'transformation_service', dummy_tx, raising=True)

    # First run gets the lock and completes
    resp1 = await routes.process_chapters(adaptation_id=42, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp1.status_code == 200

    # Second immediate attempt sees lock and is rejected with 409
    lock_state["taken"] = True
    resp2 = await routes.process_chapters(adaptation_id=42, background_tasks=types.SimpleNamespace(add_task=lambda *a, **k: None))
    assert resp2.status_code == 409
    body = json.loads(resp2.body)
    assert body.get('error') == 'run_in_progress'

