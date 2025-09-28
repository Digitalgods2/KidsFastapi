import os
import asyncio
import pytest

import sys, types
import database

def make_service():
    # Inject a fake OpenAIService to satisfy import in services.image_generation_service
    mod = types.ModuleType("legacy.services.openai_service")
    class _FakeOpenAIService:
        async def generate_image(self, prompt: str, size: str, quality: str, model: str):
            return "https://example.com/fake.png"
    mod.OpenAIService = _FakeOpenAIService
    sys.modules["legacy.services.openai_service"] = mod
    from services.image_generation_service import ImageGenerationService
    return ImageGenerationService()


class FakeCursor:
    def __init__(self, book_id=123, adaptations=None):
        self.book_id = book_id
        self._last_sql = None
        self._last_params = None
        self._result = None
        self.rowcount = 0
        self._adaptations = adaptations if adaptations is not None else [(1,), (2,)]

    def execute(self, sql, params=None):
        self._last_sql = " ".join(sql.split()) if isinstance(sql, str) else sql
        self._last_params = params
        # import_book flow
        if "SELECT book_id FROM books" in self._last_sql:
            self._result = None
        elif "INSERT INTO books" in self._last_sql and "RETURNING book_id" in self._last_sql:
            self._result = (self.book_id,)
        # delete_book_completely flow
        elif "SELECT title, original_content_path FROM books" in self._last_sql:
            self._result = ("Test Title", None)
        elif "SELECT adaptation_id FROM adaptations" in self._last_sql:
            self._result = self._adaptations
        elif "DELETE FROM chapters" in self._last_sql:
            self.rowcount = 3  # assume 3 rows deleted
        elif "DELETE FROM adaptations" in self._last_sql:
            self.rowcount = len(self._adaptations)
        elif "DELETE FROM books" in self._last_sql:
            self.rowcount = 1
        else:
            self._result = None

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result if isinstance(self._result, list) or isinstance(self._result, tuple) else []

    def close(self):
        pass


class FakeConn:
    def __init__(self, *args, **kwargs):
        self._cursor = FakeCursor()
        self.autocommit = False

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _chdir_tmp(tmp_path, monkeypatch):
    # run tests in isolated temp cwd
    monkeypatch.chdir(tmp_path)
    yield


@pytest.fixture(autouse=True)
def _mock_db_conn(monkeypatch):
    monkeypatch.setattr(database, "get_db_connection", lambda: FakeConn())
    yield


@pytest.mark.asyncio
async def test_import_creates_per_book_folder(tmp_path):
    title = "My Test Book"
    author = "Author"
    content = "Some content"
    source = "upload"

    book_id = await database.import_book(title, author, content, source)

    # Expected per-book folder
    expected_dir = os.path.join("generated_images", str(book_id))
    assert os.path.isdir(expected_dir), "import_book should create generated_images/{book_id}"


@pytest.mark.asyncio
async def test_chapter_image_saved_under_book_folder(monkeypatch):
    # Arrange: fake adaptation lookup returns specific book_id
    async def _fake_details(aid):
        return {"book_id": 123}
    monkeypatch.setattr(database, "get_adaptation_details", _fake_details)

    svc = make_service()

    # Mock downloader to avoid network

    async def fake_save_from_url(image_url: str, filename: str):
        os.makedirs(os.path.join("generated_images","123"), exist_ok=True)
        path = os.path.join("generated_images","123", filename)
        with open(path, "wb") as f:
            f.write(b"fake")
        return path

    monkeypatch.setattr(svc, "_save_image_from_url", fake_save_from_url)

    # Act
    res = await svc.generate_single_image(
        prompt="test",
        chapter_id=1,
        adaptation_id=77,
        api_type="dall-e-3",
    )

    # Assert: EXPECT per-book path (will FAIL until code writes under generated_images/{book_id})
    assert res.get("success") is True
    assert res.get("image_url", "").startswith("/generated_images/123/"), \
        "Chapter image URL should be under /generated_images/{book_id}/"


@pytest.mark.asyncio
async def test_cover_image_saved_under_book_folder(monkeypatch):
    # Arrange: fake generate_single_image returns a local file path
    tmp_file = os.path.join(".", "tmp_cover.png")
    with open(tmp_file, "wb") as f:
        f.write(b"fake")

    svc = make_service()

    async def fake_generate_single_image(**kwargs):
        return {"success": True, "local_path": tmp_file}

    async def _fake_details(aid):
        return {"book_id": 42}

    monkeypatch.setattr(database, "get_adaptation_details", _fake_details)
    monkeypatch.setattr(svc, "generate_single_image", fake_generate_single_image)

    # Act
    result = await svc.generate_cover_image(
        adaptation_id=42,
        title="T",
        author="A",
        theme="Adventure",
        api_type="dall-e-3",
    )

    # Assert: EXPECT per-book URL (will FAIL until code uses generated_images/{book_id})
    assert result.get("success") is True
    assert result.get("cover_url", "").startswith("/generated_images/42/"), \
        "Cover image URL should be under /generated_images/{book_id}/"


@pytest.mark.asyncio
async def test_delete_book_removes_per_book_folder(monkeypatch):
    # Arrange: create a per-book folder with a dummy file
    book_id = 555
    book_dir = os.path.join("generated_images", str(book_id))
    os.makedirs(book_dir, exist_ok=True)
    with open(os.path.join(book_dir, "dummy.png"), "wb") as f:
        f.write(b"x")

    # Fake DB cursor returns one book, some adaptations, and successful deletes
    class _Cursor(FakeCursor):
        def __init__(self):
            super().__init__(book_id=book_id, adaptations=[(11,), (12,)])

    class _Conn(FakeConn):
        def __init__(self):
            self._cursor = _Cursor()

    monkeypatch.setattr(database, "get_db_connection", lambda: _Conn())

    # Act
    ok = await database.delete_book_completely(book_id)

    # Assert: EXPECT folder removed (will FAIL until code deletes generated_images/{book_id})
    assert ok is True
    assert not os.path.exists(book_dir), "delete_book_completely should remove per-book images folder"
