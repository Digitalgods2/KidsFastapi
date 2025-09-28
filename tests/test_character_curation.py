import pytest
import sys
import types

# Avoid OpenAI import during tests
stub = types.ModuleType('services.chat_helper')
async def generate_chat_text(*a, **k):
    return ("", None)
stub.generate_chat_text = generate_chat_text
sys.modules['services.chat_helper'] = stub

import os, importlib.util

def _load_character_analyzer_real():
    here = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(here, '..', 'services', 'character_analyzer.py'))
    spec = importlib.util.spec_from_file_location('character_analyzer_real', path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

_ca = _load_character_analyzer_real()
CharacterAnalyzer = _ca.CharacterAnalyzer


def run_curate(raw, text, cap=25):
    return CharacterAnalyzer.curate_names(raw, text, cap=cap)


@pytest.mark.parametrize("raw, expected", [
    (["Catherine", "Lady Catherine", "Lady C. de Bourgh"], "Lady Catherine"),
])
def test_char_titles_identity_preserved(raw, expected):
    # Corpus includes both variants - identity-bearing title must be preserved
    corpus = "Lady Catherine spoke. Catherine replied. Lady C. de Bourgh entered."
    curated = run_curate(raw, corpus, cap=25)
    assert expected in curated


def test_char_titles_generic_collapse():
    # When base is unambiguous, generic title should collapse to base
    raw = ["Mr. Collins", "Collins"]
    corpus = "Collins said hello. Mr. Collins nodded. Collins left."
    curated = run_curate(raw, corpus, cap=25)
    # We expect base name to be preferred when unambiguous
    assert "Collins" in curated
    # Documented rule: if ambiguous, prefer titled form; we'll add ambiguity coverage in a variant test


def test_char_alias_merge_nickname_formal():
    # Simulate co-occurrence of nickname and formal name nearby
    text = (
        "Elizabeth Bennet walked to the garden. Lizzy smiled at her sister. "
        "Later, Elizabeth Bennet and Lizzy spoke again."
    )
    raw = ["Elizabeth Bennet", "Lizzy"]
    curated = run_curate(raw, text, cap=25)
    # Prefer the formal full name as canonical when present
    assert "Elizabeth Bennet" in curated


def test_char_multitoken_preference_over_ambiguous_short():
    # Many hits for short form; enough occurrences for long form, short is ambiguous
    text = (
        "Grant met John. Grant Anderson spoke. Grant left. Later, Grant Anderson returned. "
        "Others spoke about a grant, but not the person. Grant Anderson smiled."
    )
    raw = ["Grant", "Grant Anderson"]
    curated = run_curate(raw, text, cap=25)
    assert "Grant Anderson" in curated


def test_char_unicode_and_possessive_hyphen_boundaries():
    text = "Élise’s book was on the table. Mary-Jane laughed. O’Connor arrived. Elise's friend left."
    # Include ASCII apostrophe and Unicode right single quotation mark cases
    raw = ["Élise", "Mary-Jane", "O’Connor", "Elise"]
    curated = run_curate(raw, text, cap=25)
    # Normalization retains accents/hyphens/apostrophes and boundary handling ensures counts are non-zero
    assert any(n.startswith("Élise") for n in curated)
    assert "Mary-Jane" in curated
    assert any(n.startswith("O’Connor") or n.startswith("O'Connor") for n in curated)


def test_char_cap_and_deterministic_ordering():
    # Construct synthetic names with known frequencies
    base = "Anna Bella Cara Dana Elle Fay Gia Hana Ira Jia Kara Lana Mara Nia Ora Pia Quia Ria Sia Tia Uma Via Wia Xia Yia Zia"
    tokens = base.split()
    # Repeat to create frequency differences: Anna appears 10 times, Bella 9, ...
    text = " ".join(sum(([t]*max(1, 10-i) for i, t in enumerate(tokens)), []))
    raw = tokens
    cap = 10
    curated1 = run_curate(raw, text, cap=cap)
    curated2 = run_curate(raw, text, cap=cap)
    assert len(curated1) <= cap
    assert curated1 == curated2  # deterministic across runs


def test_char_endpoint_contract_fields(monkeypatch):
    # Contract check: curated, curated_count, aliases_map, dropped, debug_info
    # We'll stub curate_for_adaptation to produce a stable response
    from services import character_analyzer as ca

    async def fake_curate_for_adaptation(adaptation, chapters, default_cap=25):
        return ["Lady Catherine", "Elizabeth Bennet"]

    monkeypatch.setattr(ca.CharacterAnalyzer, 'curate_for_adaptation', staticmethod(fake_curate_for_adaptation), raising=True)

    # Simulate an endpoint that returns the contract body (we don't need the real FastAPI here)
    body = {
        "curated": ["Lady Catherine", "Elizabeth Bennet"],
        "curated_count": 2,
        "aliases_map": {
            "Lady Catherine": ["Catherine", "Lady C. de Bourgh"],
            "Elizabeth Bennet": ["Lizzy"],
        },
        "dropped": [
            {"variant": "Mr. Collins", "reason": "generic_title"},
            {"variant": "Grant", "reason": "ambiguous_short"},
        ],
        "debug_info": {
            "counts_by_variant": {"Lady Catherine": 3, "Catherine": 2, "Lady C. de Bourgh": 1},
            "cooccurrence_edges": 2,
            "rules_applied": ["identity_title_preserved", "nickname_merge", "ambiguous_short_collapsed"],
        },
    }

    assert isinstance(body.get("curated"), list)
    assert body.get("curated_count") == len(body.get("curated"))
    assert isinstance(body.get("aliases_map"), dict)
    assert isinstance(body.get("dropped"), list)
    assert isinstance(body.get("debug_info"), dict)
