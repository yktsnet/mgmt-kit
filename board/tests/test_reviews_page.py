import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app

BOARD = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    return TestClient(create_app(config.load()))


def test_home_goes_to_reviews(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/reviews"


def test_reviews_grouped_by_reviewer_with_status(client):
    html = client.get("/reviews").text
    assert "2 / 3 done" in html
    assert "Reviewer 未割り当て" in html
    for s in ("Not started", "In progress", "Done"):
        assert s in html
    assert 'href="/reviews/2026-H2/ben-carter@example.com"' in html


def test_review_detail_shows_levels_and_verdicts(client):
    html = client.get("/reviews/2026-H2/ben-carter@example.com").text
    assert "Reviewer Alice Walker" in html
    assert 'class="lv">L1<' in html
    assert "item verdict fail" in html and "PR と Issue を読んで確かめた" in html


def test_not_started_has_no_sheet(client):
    html = client.get("/reviews/2026-H2/jack-foster@example.com").text
    assert "評価のシートがまだ無い" in html
    assert client.get("/reviews/2026-H2/nobody@example.com").status_code == 404
