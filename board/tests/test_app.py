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
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    c.drive = drive
    return c





def test_settings_shows_definition_assignments_and_requisitions(client):
    html = client.get("/settings").text
    assert "性能・運用・移行の欠落を要件に対して指摘できる。" in html
    assert "Unassigned" in html and "Alice Walker" in html
    assert "リード" in html
    # 読む表示と編集の部品は、区画の Edit で切り替える
    assert 'data-action="edit"' in html and 'class="btn link add edit-only"' in html


def test_version_used_by_reviews_is_locked_until_new_version(client):
    html = client.get("/settings").text
    assert "評価か面接に使われている版" in html
    assert client.post("/api/definition/item", json={"version": 1, "axis": "A", "level": 3, "key": "a", "text": "x"}).status_code == 400
    assert client.post("/api/definition/version").json()["result"] == 2
    r = client.post("/api/definition/item", json={"version": 2, "axis": "A", "level": 3, "key": "a", "text": "v2 で直した細目。"})
    assert r.status_code == 200, r.text
    assert "v2 で直した細目。" in client.get("/settings").text
    assert "v2 で直した細目。" not in client.get("/settings?v=1").text


def test_role_and_reviewer_change(client):
    assert client.post("/api/people", json={"email": "jack-foster@example.com", "role": "manager"}).status_code == 200
    assert client.post("/api/people", json={"email": "jack-foster@example.com", "evaluator": "alice-walker@example.com"}).status_code == 200
    html = client.get("/settings").text
    assert "Manager" in html
    assert client.post("/api/people", json={"email": "jack-foster@example.com", "evaluator": "jack-foster@example.com"}).status_code == 400
