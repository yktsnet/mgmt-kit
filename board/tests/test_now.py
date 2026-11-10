import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app
from app.views import next_axis
from app.review import AxisResult

BOARD = Path(__file__).resolve().parent.parent


def make(tmp_path, monkeypatch, who="alice-walker"):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": f"{who}@example.com"})
    return c


@pytest.fixture
def client(tmp_path, monkeypatch):
    return make(tmp_path, monkeypatch)


def test_next_axis_is_lowest_decided_axis():
    levels = {"A": AxisResult(3, False), "B": AxisResult(1, False), "C": AxisResult(None, False), "D": AxisResult(None, True)}
    assert next_axis(levels) == "B"
    # 同じ低さなら A から
    assert next_axis({"A": AxisResult(2, False), "E": AxisResult(2, False)}) == "A"
    assert next_axis({}) is None


def test_page_shows_md_equivalent_charts_and_tables(client):
    html = client.get("/now").text
    for h in ("次に上げる1軸", "日ごとのトークン量", "日ごとの commit", "量と成果", "使い方"):
        assert f"<h2>{h}</h2>" in html
    assert html.count("<svg") == 2
    # MD と同じく、トークン量の多い順（ダミーでは ben-carter が先頭）
    assert html.index('href="/now/ben-carter@example.com"') < html.index('href="/now/alice-walker@example.com"')
    assert "<code>issue-draft</code>（" in html
    assert "（未決定）" in html
    assert "B が L1 のまま L2 に届かない人が 2 人いる" in html


def test_member_page_links_review_and_shows_trend(client):
    html = client.get("/now/ben-carter@example.com").text
    assert 'href="/reviews/2026-H2/ben-carter@example.com"' in html
    assert "<svg" in html and "<h2>日ごと</h2>" in html
    assert client.get("/now/nobody@example.com").status_code == 404


def test_reviewer_sets_next_axis_and_it_is_recorded(tmp_path, monkeypatch):
    c = make(tmp_path, monkeypatch, who="alice-walker")
    r = c.post("/api/growth/2026-H2/ben-carter@example.com", json={"axis": "D"})
    assert r.status_code == 200, r.text
    html = c.get("/now").text
    assert "D 検証・品質保証" in html
    assert "次に上げる軸を D にした" in c.get("/reviews/2026-H2/ben-carter@example.com").text


def test_others_cannot_set_next_axis(tmp_path, monkeypatch):
    c = make(tmp_path, monkeypatch, who="jack-foster")
    assert c.post("/api/growth/2026-H2/ben-carter@example.com", json={"axis": "D"}).status_code == 400
