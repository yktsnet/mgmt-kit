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


def test_charts_and_tables_show_team_average(client):
    html = client.get("/now").text
    assert html.count('<polyline class="avg"') == 2
    assert html.count('<tr class="average">') == 2


def test_member_sees_average_of_everyone_but_only_own_lines(tmp_path, monkeypatch):
    html = make(tmp_path, monkeypatch, "ben-carter").get("/now").text
    assert html.count('<tr class="average">') == 2 and html.count('<polyline class="avg"') == 2
    assert ">emma-hughes<" not in html and ">ben-carter<" in html


def test_average_is_smoothed_and_needs_three_people():
    from app import config as cfg
    from app.usage_report import _render

    r = _render(cfg.load().usage_dir)
    import datetime as dt

    days = [dt.date(2026, 4, i) for i in range(6, 11)]
    by_date = {d: {"members": {"a": {"tokens": v}, "b": {"tokens": 0}, "c": {"tokens": 0}}} for d, v in zip(days, (30, 0, 30, 0, 30))}
    # 日ごとの平均は 10, 0, 10, 0, 10。直前の日までと合わせてならす
    assert r.average(days, by_date, ["a", "b", "c"], "tokens") == [10, 5, 20 / 3, 5, 6]
    assert 'class="avg"' not in r.team_chart(days, by_date, ["a", "b"], "tokens", str)
    assert 'class="avg"' in r.team_chart(days, by_date, ["a"], "tokens", str, average_of=["a", "b", "c"])
    assert r.team_average({"a": {}, "b": {}}) is None
