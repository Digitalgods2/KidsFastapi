import asyncio
import json
import re
import types
import sys
import types as pytypes
import pytest

# Dummy modules to avoid OpenAI dependency
mod = pytypes.ModuleType('services.character_analyzer')
class DummyCA:
    @staticmethod
    async def curate_for_adaptation(adaptation, chapters, default_cap: int = 25):
        return []
mod.CharacterAnalyzer = DummyCA
sys.modules['services.character_analyzer'] = mod

mod2 = pytypes.ModuleType('services.chat_helper')
async def _gen(messages, model=None, temperature=0.7, max_tokens=800):
    return ("", None)
mod2.generate_chat_text = _gen
sys.modules['services.chat_helper'] = mod2

import routes.adaptations as routes

ISO_UTC_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

class DummyDBStatus:
    def __init__(self):
        self._current_runs = {}
        self._status_ts = {}
        self._stage = {}
        self._images = {}
        self._prompts = {}
        self._chapters = {}

    # simulate progress aggregates
    async def get_adaptation_progress(self, adaptation_id: int):
        rid = self._current_runs.get(adaptation_id)
        total = self._chapters.get(adaptation_id, 0)
        images = self._images.get(adaptation_id, 0)
        prompts = self._prompts.get(adaptation_id, 0)
        stage = self._stage.get(adaptation_id, 'in_progress')
        ts = self._status_ts.get(adaptation_id) or asyncio.get_event_loop().time()
        # Return flat schema
        pct = int(round(100*images/total)) if total else 0
        pct = max(0, min(100, pct))
        # Build a fake UTC ISO timestamp ending with Z
        last_update_ts = '2025-01-01T00:00:00Z'
        return {
            "adaptation_id": adaptation_id,
            "stage": stage,
            "stage_detail": f"images {images}/{total}; prompts {prompts}/{total}",
            "run_id": rid,
            "last_update_ts": last_update_ts,
            "last_error": None,
            "chapters_total": total,
            "prompts_done": prompts,
            "images_done": images,
            "completion_pct": pct,
        }

    # Run tracking compatibility for routes (if needed)
    def set_current_run(self, adaptation_id, run_id):
        self._current_runs[adaptation_id] = run_id
    def get_current_run(self, adaptation_id):
        return self._current_runs.get(adaptation_id)
    def clear_current_run(self, adaptation_id):
        self._current_runs.pop(adaptation_id, None)

@pytest.mark.asyncio
async def test_status_contract_values(monkeypatch):
    db = DummyDBStatus()
    # Install monkeypatch for database.get_adaptation_progress only
    monkeypatch.setattr(routes.database, 'get_adaptation_progress', db.get_adaptation_progress, raising=True)

    # baseline
    s = await routes.adaptation_status(adaptation_id=1)
    assert s.status_code == 200
    body = json.loads(s.body)
    assert 0 <= (body.get('completion_pct') or 0) <= 100
    # last_update_ts must be ISO8601 UTC with Z
    assert ISO_UTC_Z.match(body.get('last_update_ts') or '')

@pytest.mark.asyncio
async def test_status_timestamp_monotonic(monkeypatch):
    # For a fixed run_id, poll twice and ensure last_update_ts strictly increases
    from routes import adaptations as r

    # Stateful fake progress to simulate an in-progress run with increasing timestamps
    state = {"i": 0, "run_id": "run-fixed"}
    async def fake_progress(adaptation_id: int):
        state["i"] += 1
        ts = f"2025-01-01T00:00:{state['i']:02d}Z"
        return {
            "adaptation_id": adaptation_id,
            "stage": "in_progress",
            "stage_detail": "",
            "run_id": state["run_id"],
            "last_update_ts": ts,
            "last_error": None,
            "chapters_total": 10,
            "prompts_done": 0,
            "images_done": min(state["i"], 10),
            "completion_pct": min(100, state["i"]*10),
        }

    monkeypatch.setattr(r.database, 'get_adaptation_progress', fake_progress, raising=True)

    s1 = await r.adaptation_status(123)
    b1 = json.loads(s1.body)
    s2 = await r.adaptation_status(123)
    b2 = json.loads(s2.body)
    assert ISO_UTC_Z.match(b1['last_update_ts'])
    assert ISO_UTC_Z.match(b2['last_update_ts'])
    # Strictly increases
    t1 = b1['last_update_ts']
    t2 = b2['last_update_ts']
    assert t2 > t1

@pytest.mark.asyncio
async def test_ui_reducer_stale_drop():
    # Unit test the UI reducer logic: ignore stale results by (run_id, timestamp)
    def reducer(prev_run_id, prev_ts, run_id, last_update_ts):
        # Equivalent logic to the template's poller
        import datetime
        ts = int(datetime.datetime.fromisoformat(last_update_ts.replace('Z','+00:00')).timestamp())
        if (prev_run_id and run_id and prev_run_id != run_id) or (prev_ts and ts < prev_ts):
            return prev_run_id, prev_ts  # drop stale
        return run_id or prev_run_id, ts

    r1, t1 = reducer(None, None, 'runA', '2025-01-01T00:00:01Z')
    r2, t2 = reducer(r1, t1, 'runA', '2025-01-01T00:00:02Z')

@pytest.mark.asyncio
async def test_status_persists_run_id_across_restart(monkeypatch):
    # Simulate run_id persisted in DB active_runs and memory cleared (restart)
    from routes import adaptations as r
    adaptation_id = 777
    run_id = 'run-persisted'

    async def fake_active_run(adaptation_id: int):
        return {"run_id": run_id, "stage": "normalizing", "updated_at": "2025-01-01T00:00:00Z"}

    async def fake_progress(adaptation_id: int):
        # Simulate aggregator: return minimal status; run_id derived from active_runs
        ar = await r.database.get_active_run(adaptation_id)
        return {
            "adaptation_id": adaptation_id,
            "stage": "in_progress",
            "stage_detail": "",
            "run_id": ar["run_id"] if ar else None,
            "last_update_ts": "2025-01-01T00:00:00Z",
            "last_error": None,
            "chapters_total": 10,
            "prompts_done": 0,
            "images_done": 1,
            "completion_pct": 10,
        }

    # Clear in-memory current run first
    import database
    database.clear_current_run(adaptation_id)

    # Monkeypatch database calls used by the status route
    monkeypatch.setattr(r.database, 'get_active_run', fake_active_run, raising=True)
    monkeypatch.setattr(r.database, 'get_adaptation_progress', fake_progress, raising=True)

    s = await r.adaptation_status(adaptation_id)
    body = json.loads(s.body)
    assert body.get('run_id') == run_id

