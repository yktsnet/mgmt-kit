import html as htmllib
import re
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app
from app.views import next_axis
from app.review import AxisResult

BOARD = Path(__file__).resolve().parent.parent
USAGE_README = BOARD.parent / "usage" / "tools" / "usage" / "claude-code" / "README.md"


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


def md_table(title: str) -> tuple[list[str], dict[str, list[str]]]:
    """usage の README.md の見出し title の下の表を、見出しの列と、名前ごとの行にする。"""
    text = USAGE_README.read_text(encoding="utf-8").split(f"### {title}\n", 1)[1]
    lines = [ln for ln in text.split("\n### ", 1)[0].splitlines() if ln.startswith("|")]
    cells = [[c.strip() for c in ln.strip("|").split("|")] for ln in lines]
    rows = {}
    for row in cells[2:]:
        who = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", row[0]).replace("**平均**", "平均")
        rows[who] = row[1:]
    return cells[0][1:], rows


def html_table(page: str, title: str) -> tuple[list[str], dict[str, list[str]]]:
    """現在地のページの見出し title の下の表を、md_table と同じ形にする。"""
    part = page.split(f"<h2>{title}</h2>", 1)[1].split("</table>", 1)[0]
    text = lambda c: htmllib.unescape(re.sub(r"<[^>]+>", "", c)).strip()  # noqa: E731
    head = [text(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", part, re.S)]
    rows = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", part, re.S):
        tds = [text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if tds:
            rows[tds[0].replace("平均（全員）", "平均")] = tds[1:]
    return head[1:], rows


@pytest.mark.parametrize("title", ["量と成果", "使い方"])
def test_now_tables_match_usage_readme(client, title):
    page = client.get("/now").text
    md_head, md_rows = md_table(title)
    head, rows = html_table(page, title)
    assert head == md_head
    assert rows == md_rows and len(rows) == 11


def test_old_db_without_ladder_tables_opens(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        "CREATE TABLE files (id TEXT PRIMARY KEY, path TEXT NOT NULL, modified TEXT NOT NULL, kind TEXT NOT NULL, error TEXT, modified_by TEXT);"
        "CREATE TABLE scores (email TEXT NOT NULL, origin TEXT NOT NULL, axis TEXT NOT NULL, value INTEGER NOT NULL);"
        "CREATE TABLE staff (email TEXT PRIMARY KEY, file_id TEXT NOT NULL, name TEXT NOT NULL, period TEXT NOT NULL, level INTEGER);"
        "CREATE TABLE personas (level INTEGER NOT NULL, axis TEXT NOT NULL, value INTEGER NOT NULL);"
        "INSERT INTO files VALUES ('ladder/ben-carter.md', 'ladder/ben-carter.md', '1', 'scoresheet', 'bad sheet', NULL);"
        "INSERT INTO staff VALUES ('ben-carter@example.com', 'ladder/ben-carter.md', 'ben-carter', '2026-01', 1);"
    )
    old.commit()
    old.close()
    monkeypatch.setenv("BOARD_DB", str(path))
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    assert c.get("/now").status_code == 200
    db = sqlite3.connect(path)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not tables & {"scores", "staff", "personas"}
    assert db.execute("SELECT count(*) FROM files WHERE kind = 'scoresheet'").fetchone()[0] == 0


@pytest.mark.parametrize("path", ["/reviews", "/now", "/hiring", "/settings"])
def test_demo_pages_open(client, path):
    assert client.get(path).status_code == 200


def next_rows(page: str) -> list[list[str]]:
    part = page.split("<h2>次に上げる1軸</h2>", 1)[1].split("</table>", 1)[0].split("<tbody>", 1)[1]
    text = lambda c: " ".join(htmllib.unescape(re.sub(r"<[^>]+>", " ", c)).split())  # noqa: E731
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", part, re.S):
        # 直すための select は Edit のあいだだけ出るので、読むときの文字だけを取る
        tr = re.sub(r'<select class="edit-only".*?</select>', "", tr, flags=re.S)
        rows.append([text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)])
    return rows


def test_now_sections_for_manager(client):
    page = client.get("/now").text
    assert re.findall(r"<h2>(.*?)</h2>", page) == ["次に上げる1軸", "日ごとのトークン量", "日ごとの commit", "量と成果", "使い方"]
    rows = next_rows(page)
    assert len(rows) == 10
    assert rows[1] == ["🐘 Emma Hughes", "L3", "C ドメイン理解", "C が L2。最も低い軸", "🐊 Alice Walker （未決定）"]
    assert "B が L1 のまま L2 に届かない人が 2 人いる" in page


def test_now_for_member_without_reviewees(tmp_path, monkeypatch):
    page = make(tmp_path, monkeypatch, "henry-ward").get("/now").text
    # 自分の評価は Approved になるまで見られないので、段階も軸も出ない
    assert next_rows(page) == [["🦔 Henry Ward", "-", "評価が出てから", "-", "-"]]
    _, rows = html_table(page, "量と成果")
    assert list(rows) == ["henry-ward", "平均"]
    assert rows["henry-ward"] == md_table("量と成果")[1]["henry-ward"]


def test_no_average_on_screen_with_two_people(tmp_path, monkeypatch):
    import json

    # render.py は親のディレクトリの chart.py を読むので、親ごと写す
    shutil.copytree(USAGE_README.parent.parent, tmp_path / "usage", ignore=shutil.ignore_patterns("__pycache__"))
    usage = tmp_path / "usage" / "claude-code"
    for p in (usage / "data").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        d["members"] = {k: v for k, v in d["members"].items() if k in ("alice-walker@example.com", "ben-carter@example.com")}
        p.write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setenv("BOARD_USAGE_DIR", str(usage))
    html = make(tmp_path, monkeypatch).get("/now").text
    assert "日ごとのトークン量" in html
    assert '<tr class="average">' not in html and 'class="avg"' not in html
