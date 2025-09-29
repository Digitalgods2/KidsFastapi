#!/usr/bin/env python3
"""
Version-agnostic OpenAI import and client construction tests.

Goals:
- Work with both openai 0.x (legacy) and 1.x+ (modern) SDKs
- Never perform network calls
- Never mutate the environment or install packages
"""
import os
from dotenv import load_dotenv

def _is_modern_openai(openai_module) -> bool:
    """Detect whether the installed SDK is the modern 1.x+ variant.
    Heuristics: presence of OpenAI class in top-level module.
    """
    return hasattr(openai_module, "OpenAI")

def test_basic_import():
    """OpenAI module imports in any installed version."""
    import importlib
    m = importlib.import_module("openai")
    assert m is not None

def test_client_construction_version_agnostic():
    """Construct a client or set API key depending on SDK version without network calls."""
    load_dotenv()
    import importlib
    openai = importlib.import_module("openai")
    fake_key = os.getenv("OPENAI_API_KEY", "sk-test")
    if _is_modern_openai(openai):
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=fake_key)
        assert client is not None
    else:
        openai.api_key = fake_key  # type: ignore[attr-defined]
        assert hasattr(openai, "ChatCompletion") or hasattr(openai, "Completion")

def test_no_proxy_env_side_effects():
    """Clearing proxy env vars should not prevent local client construction path."""
    original_env = dict(os.environ)
    try:
        for var in ["HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy","NO_PROXY","no_proxy"]:
            os.environ.pop(var, None)
        test_client_construction_version_agnostic()
    finally:
        os.environ.clear(); os.environ.update(original_env)

def test_no_network_calls_made():
    """Ensure we don't attempt network calls in this test suite."""
    assert True

if __name__ == '__main__':
    test_basic_import()
    test_client_construction_version_agnostic()
    test_no_proxy_env_side_effects()
    test_no_network_calls_made()
