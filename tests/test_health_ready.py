import pytest
import json
import asyncio

# We test routes.health functions in isolation without spinning the whole app.
from routes import health as rh

@pytest.mark.asyncio
async def test_health_always_200():
    r = await rh.health()
    assert r.status_code == 200
    body = json.loads(r.body)
    assert body.get("status") == "up"
    assert isinstance(body.get("uptime_s"), int)
    assert body.get("checked_at", "").endswith("Z")

@pytest.mark.asyncio
async def test_ready_ok_all_green(monkeypatch):
    # Reset ready cache
    rh._last_ready.update({"ts": 0.0, "body": None, "status": 503})
    async def ok_db(t):
        return {"status":"up","latency_ms": 5}
    async def ok_img(t):
        return {"status":"up","latency_ms": 6}
    async def ok_cache(t):
        return {"status":"up","latency_ms": 7}
    monkeypatch.setattr(rh, '_probe_db', ok_db, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', ok_img, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', ok_cache, raising=True)
    resp = await rh.ready()
    assert resp.status_code == 200
    body = json.loads(resp.body)
    assert body.get("status") == "up"
    comps = body.get("components", {})
    assert comps.get("db", {}).get("status") == "up"
    assert comps.get("image_backend", {}).get("status") == "up"
    assert comps.get("cache", {}).get("status") == "up"
    assert body.get("checked_at", "").endswith("Z")

@pytest.mark.asyncio
async def test_ready_db_down_returns_503(monkeypatch):
    rh._last_ready.update({"ts": 0.0, "body": None, "status": 503})
    async def bad_db(t):
        return {"status":"down","latency_ms": 5, "error":"unavailable"}
    async def ok_img(t):
        return {"status":"up","latency_ms": 6}
    async def ok_cache(t):
        return {"status":"up","latency_ms": 7}
    monkeypatch.setattr(rh, '_probe_db', bad_db, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', ok_img, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', ok_cache, raising=True)
    resp = await rh.ready()
    assert resp.status_code == 503
    body = json.loads(resp.body)
    assert body.get("status") == "down"
    assert body.get("components", {}).get("db", {}).get("status") == "down"

@pytest.mark.asyncio
async def test_ready_image_backend_auth_failed(monkeypatch):
    rh._last_ready.update({"ts": 0.0, "body": None, "status": 503})
    async def ok_db(t):
        return {"status":"up","latency_ms": 5}
    async def bad_img(t):
        return {"status":"down","latency_ms": 6, "error":"auth_failed"}
    async def ok_cache(t):
        return {"status":"up","latency_ms": 7}
    monkeypatch.setattr(rh, '_probe_db', ok_db, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', bad_img, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', ok_cache, raising=True)
    resp = await rh.ready()
    assert resp.status_code == 503
    body = json.loads(resp.body)
    assert body.get("components", {}).get("image_backend", {}).get("error") == "auth_failed"

@pytest.mark.asyncio
async def test_ready_cache_down_returns_503(monkeypatch):
    rh._last_ready.update({"ts": 0.0, "body": None, "status": 503})
    async def ok_db(t):
        return {"status":"up","latency_ms": 5}
    async def ok_img(t):
        return {"status":"up","latency_ms": 6}
    async def bad_cache(t):
        return {"status":"down","latency_ms": 7, "error":"unavailable"}
    monkeypatch.setattr(rh, '_probe_db', ok_db, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', ok_img, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', bad_cache, raising=True)
    resp = await rh.ready()
    assert resp.status_code == 503
    body = json.loads(resp.body)
    assert body.get("components", {}).get("cache", {}).get("status") == "down"

@pytest.mark.asyncio
async def test_ready_time_budget_respected(monkeypatch):
    rh._last_ready.update({"ts": 0.0, "body": None, "status": 503})
    # Simulate hang; probe functions will exceed per-probe timeout if not wrapped properly
    async def slow_probe(t):
        await asyncio.sleep(t + 0.5)
        return {"status":"up","latency_ms": 999}
    monkeypatch.setattr(rh, '_probe_db', slow_probe, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', slow_probe, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', slow_probe, raising=True)
    resp = await rh.ready()
    # Should return quickly with all timeouts treated as down
    assert resp.status_code == 503
    body = json.loads(resp.body)
    assert body.get("status") == "down"

@pytest.mark.asyncio
async def test_ready_timestamp_and_format(monkeypatch):
    async def ok_probe(t):
        return {"status":"up","latency_ms": 1}
    monkeypatch.setattr(rh, '_probe_db', ok_probe, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', ok_probe, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', ok_probe, raising=True)
    resp = await rh.ready()
    body = json.loads(resp.body)
    assert body.get("checked_at", "").endswith("Z")

@pytest.mark.asyncio
async def test_ready_short_cache_behavior(monkeypatch):
    async def ok_probe(t):
        return {"status":"up","latency_ms": 1}
    monkeypatch.setattr(rh, '_probe_db', ok_probe, raising=True)
    monkeypatch.setattr(rh, '_probe_image_backend', ok_probe, raising=True)
    monkeypatch.setattr(rh, '_probe_cache', ok_probe, raising=True)
    # First call populates cache
    resp1 = await rh.ready()
    body1 = json.loads(resp1.body)
    # Second call within TTL should reuse
    resp2 = await rh.ready()
    body2 = json.loads(resp2.body)
    assert body1 == body2
