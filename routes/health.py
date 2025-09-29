from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import asyncio
import time
import config
import database_fixed as database

router = APIRouter()

# Optional short cache to prevent thundering herd
_last_ready = {"ts": 0.0, "body": None, "status": 503}
_READY_CACHE_TTL_S = 1.5


def _utc_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


@router.get("/health")
async def health():
    # Liveness: process is up
    started = getattr(health, "_started", None)
    if started is None:
        started = time.time()
        setattr(health, "_started", started)
    uptime_s = int(max(0, time.time() - started))
    body = {
        "status": "up",
        "version": getattr(config, "APP_VERSION", getattr(config, "__version__", "unknown")) or "unknown",
        "uptime_s": uptime_s,
        "checked_at": _utc_z(datetime.now(timezone.utc)),
    }
    return JSONResponse(body, status_code=200)


async def _probe_db(timeout_s: float):
    t0 = time.perf_counter()
    try:
        async def q():
            # Use a very light query via existing helpers
            await database.get_dashboard_stats()
        await asyncio.wait_for(q(), timeout=timeout_s)
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"up","latency_ms":latency}
    except asyncio.TimeoutError:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"down","latency_ms":latency, "error":"timeout"}
    except Exception:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"down","latency_ms":latency, "error":"unavailable"}


async def _probe_image_backend(timeout_s: float):
    t0 = time.perf_counter()
    try:
        async def ping():
            # Probe by validating backend setting; escalate to auth check if available later
            from services.backends import validate_backend
            name = await database.get_setting("default_image_backend", "dall-e-3")
            ok = validate_backend(name)
            if not ok:
                raise RuntimeError("invalid_backend")
        await asyncio.wait_for(ping(), timeout=timeout_s)
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"up","latency_ms":latency}
    except asyncio.TimeoutError:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"down","latency_ms":latency, "error":"timeout"}
    except PermissionError:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"down","latency_ms":latency, "error":"auth_failed"}
    except Exception as e:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        # Only expose generic error categories to avoid secrets
        err = "auth_failed" if getattr(e, 'status', None) in (401, 403) else "unavailable"
        return {"status":"down","latency_ms":latency, "error": err}


async def _probe_cache(timeout_s: float):
    t0 = time.perf_counter()
    try:
        # Minimal in-process cache probe (placeholder for external cache)
        key = f"ready_probe_{int(time.time()*1000)}"
        store = getattr(_probe_cache, "_store", {})
        store[key] = "1"
        getattr(_probe_cache, "_store", store)
        if store.get(key) != "1":
            raise RuntimeError("cache_miss")
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"up","latency_ms":latency}
    except asyncio.TimeoutError:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"down","latency_ms":latency, "error":"timeout"}
    except Exception:
        latency = int(max(0, (time.perf_counter()-t0)*1000))
        return {"status":"down","latency_ms":latency, "error":"unavailable"}


@router.get("/ready")
async def ready():
    # Optional short cache
    now = time.time()
    if (_last_ready["body"] is not None) and (now - _last_ready["ts"] < _READY_CACHE_TTL_S):
        return JSONResponse(_last_ready["body"], status_code=_last_ready["status"])

    # Probe all in parallel with timeouts; budget ~1s total
    per_probe_timeout = 0.3
    async def _run_with_budget(coro, budget):
        try:
            return await asyncio.wait_for(coro, timeout=budget)
        except asyncio.TimeoutError:
            return {"status":"down","latency_ms": int(budget*1000), "error":"timeout"}
    tasks = [
        _run_with_budget(_probe_db(per_probe_timeout), per_probe_timeout),
        _run_with_budget(_probe_image_backend(per_probe_timeout), per_probe_timeout),
        _run_with_budget(_probe_cache(per_probe_timeout), per_probe_timeout),
    ]
    db_r, img_r, cache_r = await asyncio.gather(*tasks)

    components = {
        "db": db_r,
        "image_backend": img_r,
        "cache": cache_r,
    }
    overall = "up" if all(c.get("status") == "up" for c in components.values()) else "down"
    status_code = 200 if overall == "up" else 503

    body = {
        "status": overall,
        "checked_at": _utc_z(datetime.now(timezone.utc)),
        "components": components,
    }

    # Cache result
    _last_ready["ts"] = now
    _last_ready["body"] = body
    _last_ready["status"] = status_code

    # Structured logs per probe
    from services.logger import get_logger
    log = get_logger("routes.health")
    rid = None
    try:
        for pname, pres in components.items():
            log.info("ready_probe", extra={
                "probe": pname,
                "status": pres.get("status"),
                "latency_ms": max(0, int(pres.get("latency_ms", 0))),
                "error_type": pres.get("error"),
                "checked_at": body["checked_at"],
            })
    except Exception:
        pass

    return JSONResponse(body, status_code=status_code)
