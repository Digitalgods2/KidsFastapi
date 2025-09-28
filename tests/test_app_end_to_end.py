import os
import json
import re
import asyncio
from fastapi.testclient import TestClient

import main
import database_fixed as database

client = TestClient(main.app)


def seed_book_and_adaptation():
    # Ensure a basic book exists; if none, create one via DB helpers
    # Use existing book if available
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    books = loop.run_until_complete(database.get_all_books())
    if not books:
        # Minimal insertion path: use import_book_to_db_low if available
        text = """Chapter 1\nOnce upon a time...\n\nChapter 2\nMore story...\n"""
        upload_path = os.path.abspath("uploads/test_seed.txt")
        os.makedirs(os.path.dirname(upload_path), exist_ok=True)
        with open(upload_path, 'w') as f:
            f.write(text)
        book_id = loop.run_until_complete(database.import_book_to_db_low(
            title="Test Book",
            author="Tester",
            source_type="upload",
            path=upload_path,
            character_reference=json.dumps({"word_count": len(text.split()), "chapter_count": 2}),
        ))
        assert book_id is not None
        books = loop.run_until_complete(database.get_all_books())
    book_id = books[0]["book_id"]

    # Ensure an adaptation exists
    adaps = loop.run_until_complete(database.get_adaptations_for_book(book_id))
    if not adaps:
        adaptation_id = loop.run_until_complete(database.create_adaptation(
            book_id=book_id,
            target_age_group="7-9",
            transformation_style="Simplified",
            overall_theme_tone="Adventure",
            key_characters_to_preserve="",
            chapter_structure_choice="Auto-segment by word count",
        ))
    else:
        adaptation_id = adaps[0]["adaptation_id"]
    return book_id, adaptation_id


def test_debug_db():
    r = client.get("/_debug/db")
    assert r.status_code == 200
    data = r.json()
    for key in ["database_url", "absolute_path", "exists"]:
        assert key in data


def test_adaptations_status():
    _, adaptation_id = seed_book_and_adaptation()
    r = client.get(f"/adaptations/{adaptation_id}/status")
    assert r.status_code == 200
    data = r.json()
    for key in ["stage", "total_chapters", "chapters_with_images"]:
        assert key in data


def test_process_chapters_htmx():
    _, adaptation_id = seed_book_and_adaptation()
    headers = {"HX-Request": "true"}
    r = client.post(f"/adaptations/{adaptation_id}/process_chapters", params={"mode": "auto"}, headers=headers)
    assert r.status_code == 200
    html = r.text
    assert 'id="chapters_table"' in html
    # crude check for >0 rows
    assert html.count('<tr') > 1


def test_images_status_alias():
    # optional but run it: verify alias works and returns expected keys
    _, adaptation_id = seed_book_and_adaptation()
    r = client.get(f"/images/adaptation/{adaptation_id}/status")
    assert r.status_code == 200
    data = r.json()
    for key in ["total_chapters", "chapters_with_images", "completion_percentage"]:
        assert key in data
