import html as htmllib
import json
import re
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
    return c


def test_home_goes_to_reviews(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/reviews"


def test_reviews_grouped_by_reviewer_with_status(client):
    html = client.get("/reviews").text
    assert "3 members · 0 submitted · 0 approved" in html
    assert "Reviewer 未割り当て" in html
    for s in ("Not started", "In progress", "Ready"):
        assert s in html
    assert 'href="/reviews/2026-H2/ben-carter@example.com"' in html


def test_review_detail_shows_levels_and_verdicts(client):
    html = client.get("/reviews/2026-H2/ben-carter@example.com").text
    assert "Reviewer 🐊 Alice Walker" in html
    assert '<span class="big">L1</span>' in html
    assert "item verdict fail" in html and "PR と Issue を読んで確かめた" in html


def test_not_started_has_no_sheet(client):
    html = client.get("/reviews/2026-H2/jack-foster@example.com").text
    assert "評価のシートがまだ無い" in html
    assert client.get("/reviews/2026-H2/nobody@example.com").status_code == 404


def test_submit_and_memo_show_in_record(client):
    base = "/api/reviews/2026-H2/grace-turner@example.com"
    assert client.post(base + "/memo", json={"body": "次は D を見る"}).status_code == 200
    assert client.post(base + "/action", json={"action": "submit"}).status_code == 200
    html = client.get("/reviews/2026-H2/grace-turner@example.com").text
    assert "次は D を見る" in html and 'data-review-action="approve"' in html
    assert "Submitted" in client.get("/reviews").text


def test_submit_refused_while_in_progress(client):
    r = client.post("/api/reviews/2026-H2/felix-grant@example.com/action", json={"action": "submit"})
    assert r.status_code == 400


# ---- 画面の中身

USAGE = BOARD.parent / "usage" / "tools" / "usage" / "claude-code"


def readme_skills(name: str) -> tuple[str, str]:
    """usage の README の「使い方」の表にあるスキルの回数と、README に書かれた期間。board を通さずに期待値を取る。"""
    text = (USAGE / "README.md").read_text(encoding="utf-8")
    count = re.search(rf"^\| {name} \| ([^|]+?) \|", text, re.M).group(1)
    since, until = re.search(r"(\d{4}-\d\d-\d\d) 〜 (\d{4}-\d\d-\d\d) の平日", text).groups()
    return count, f"{since} 〜 {until}"


def items(html: str) -> dict[tuple[int, str, str], str]:
    """Items の細目を (段階, 軸, 記号) ごとに、根拠の欄の文字にする。"""
    out = {}
    grid = html.split('<table class="grid">', 1)[1].split("</table>", 1)[0]
    for lv, row in re.findall(r'<span class="lv">L(\d)</span></td>(.*?)</tr>', grid, re.S):
        for axis, cell in re.findall(r'<td data-axis="([A-E]) [^"]*"[^>]*>(.*?)</td>', row, re.S):
            for key, body in re.findall(r'<span class="key">(\w)</span>(.*?)</div>', cell, re.S):
                out[(int(lv), axis, key)] = " ".join(re.sub(r"<[^>]+>", " ", htmllib.unescape(body)).split())
    return out


def test_reviews_roster_rows(client):
    html = client.get("/reviews").text
    group = html.split("<h2>🐊 Alice Walker</h2>", 1)[1].split("</section>", 1)[0]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", group.split("<tbody>", 1)[1], re.S):
        rows.append([" ".join(re.sub(r"<[^>]+>", " ", c).split()) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)])
    assert rows == [
        ["🐘 Emma Hughes", "Ready", "", "3", "4", "2", "3", "3", "L3"],
        ["🐻 Ben Carter", "Ready", "", "3", "1", "4", "2", "3", "L1"],
        ["🐬 Daniel Brooks", "In progress", "11 / 33", "3", "3", "…", "…", "…", "L3"],
    ]


def test_skill_usage_only_on_b_items_counting_skills(client):
    count, span = readme_skills("emma-hughes")
    got = items(client.get("/reviews/2026-H2/emma-hughes@example.com").text)
    with_usage = {k for k, v in got.items() if "usage" in v.split()}
    assert with_usage == {(2, "B", "a"), (2, "B", "b"), (4, "B", "a"), (4, "B", "b")}
    for k in with_usage:
        assert f"usage スキル {count}（{span}）" in got[k]
    # 段階・軸・細目の文は usage を足しても変わらない
    assert got[(2, "B", "a")].startswith("指示された手順を回し、標準の形の成果物を出せる。")
    assert len(got) == 33


def test_no_skill_usage_without_usage_row(tmp_path, monkeypatch):
    usage = tmp_path / "usage"
    shutil.copytree(USAGE, usage)
    for p in (usage / "data").glob("*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        d["members"].pop("emma-hughes@example.com", None)
        p.write_text(json.dumps(d), encoding="utf-8")
    monkeypatch.setenv("BOARD_USAGE_DIR", str(usage))
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    html = c.get("/reviews/2026-H2/emma-hughes@example.com").text
    assert 'class="ev usage"' not in html
    got = items(html)
    assert len(got) == 33 and "PR と Issue を読んで確かめた" in got[(2, "B", "a")]


def test_member_sees_own_skill_usage_on_approved_review(client):
    base = "/api/reviews/2026-H2/emma-hughes@example.com/action"
    assert client.post(base, json={"action": "submit"}).status_code == 200
    assert client.post(base, json={"action": "approve"}).status_code == 200
    client.post("/auth/logout")
    client.post("/auth/demo", data={"email": "emma-hughes@example.com"})
    html = client.get("/reviews/2026-H2/emma-hughes@example.com").text
    count, span = readme_skills("emma-hughes")
    shown = re.findall(r'<span class="ev usage"><b>usage</b> スキル ([^（]+)（([^）]+)）', html)
    assert shown == [(count, span)] * 4
