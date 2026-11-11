import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app

from app.hiring import current_stage, moves, records, set_stage
from app.parse import SheetError
from app.settings import seed, version_in_use
from app.sources.xlsx_folder import XlsxFolderSource
from app.store import connect
from app.sync import sync
from app.views import openings

BOARD = Path(__file__).resolve().parent.parent
LADDER_MD = BOARD.parent / "ladder" / "docs" / "ladder.md"


@pytest.fixture
def db(tmp_path):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    d = connect(":memory:")
    seed(d, LADDER_MD, demo=True)
    sync(XlsxFolderSource(drive), d)
    return d


def me(db, name="alice-walker"):
    return db.execute("SELECT * FROM people WHERE email = ?", (f"{name}@example.com",)).fetchone()


def test_stage_starts_at_first_and_moves_forward(db):
    ethan = "ethan-shaw@example.com"
    assert current_stage(db, ethan) == "応募"
    assert moves(db, ethan) == ["書類選考", "不採用", "辞退"]
    set_stage(db, me(db), ethan, "書類選考")
    assert current_stage(db, ethan) == "書類選考"
    r = records(db, ethan)[0]
    assert (r["kind"], r["body"], r["by"]) == ("stage", "書類選考", "alice-walker@example.com")


def test_cannot_skip_stages(db):
    with pytest.raises(SheetError):
        set_stage(db, me(db), "ethan-shaw@example.com", "内定")


def test_closed_candidate_can_be_reopened_to_previous_stage(db):
    sophie = "sophie-lane@example.com"
    assert current_stage(db, sophie) == "不採用"
    assert moves(db, sophie) == ["一次面接"]
    set_stage(db, me(db), sophie, "一次面接")
    assert current_stage(db, sophie) == "一次面接"


def test_offer_cannot_be_rejected_and_joined_is_final(db):
    mia = "mia-collins@example.com"
    assert moves(db, mia) == ["入社", "辞退"]
    set_stage(db, me(db), mia, "入社")
    assert moves(db, mia) == []


def test_openings_compare_target_and_count_stages(db):
    dev = next(o for o in openings(db) if o.requisition and o.requisition["name"] == "開発")
    assert dev.target == {"A": 3, "B": 3, "D": 3, "E": 2}
    assert (dev.counts["内定"], dev.counts["一次面接"], dev.counts["不採用"]) == (1, 1, 1)
    noah = next(r for r in dev.rows if r.email == "noah-reed@example.com")
    # A2 D2 は求める 3 に届かない。C は聞いていない
    assert noah.short == ["A", "D"] and noah.ask == ["C"]


def test_candidate_requisition_missing_from_settings_is_listed_apart(db):
    db.execute("UPDATE candidates SET requisition = 'デザイン' WHERE email = 'ethan-shaw@example.com'")
    rest = openings(db)[-1]
    assert rest.requisition is None and [r.email for r in rest.rows] == ["ethan-shaw@example.com"]


def test_version_used_by_candidates_is_locked(db):
    db.execute("DELETE FROM reviews")
    assert version_in_use(db, 1)


# ---- 画面の中身


def page_rows(html: str, title: str) -> list[list[str]]:
    """採用の一覧の、採用枠 title の区画の表の行。セルの文字だけにする。"""
    part = html.split(f"<h2>{title}</h2>", 1)[1].split("</table>", 1)[0].split("<tbody>", 1)[1]
    text = lambda c: " ".join(re.sub(r"<[^>]+>", " ", c).split())  # noqa: E731
    return [[text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)] for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", part, re.S)]


def test_hiring_page_lists_candidates_per_requisition(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    html = c.get("/hiring").text
    assert re.findall(r"<h2>(.*?)</h2>", html) == ["リード", "開発"]
    # 列は 名前・段階・面接・A〜E・届いていない・次に聞く
    assert page_rows(html, "リード") == [
        ["求める高さ", "", "", "L4", "L4", "·", "L3", "·", "", ""],
        ["Ethan Shaw", "応募", "", "…", "…", "…", "…", "…", "", "面接前"],
        ["Liam Price", "最終面接", "2", "4", "4", "2", "3", "3", "-", "-"],
    ]
    dev = page_rows(html, "開発")
    assert [r[:2] for r in dev[1:]] == [["Olivia Hart", "書類選考"], ["Noah Reed", "一次面接"], ["Mia Collins", "内定"], ["Sophie Lane", "不採用"]]
    assert dev[2][3:8] == ["2", "3", "…", "2", "3"] and dev[2][8] == "A D"
    # 狭い画面で畳む列は、面接・届いていない・次に聞くの3つだけ
    head = html.split("<h2>リード</h2>", 1)[1].split("</thead>", 1)[0]
    assert re.findall(r'<th class="[^"]*wide-only[^"]*">(.*?)</th>', head) == ["面接", "届いていない", "次に聞く"]


def test_stage_record_has_time(db):
    import datetime as dt

    set_stage(db, me(db), "ethan-shaw@example.com", "書類選考")
    r = records(db, "ethan-shaw@example.com")[0]
    assert r["kind"] == "stage" and dt.datetime.fromisoformat(r["at"])


def test_unobserved_axis_is_listed_to_ask(db):
    dev = next(o for o in openings(db) if o.requisition and o.requisition["name"] == "開発")
    sophie = next(r for r in dev.rows if r.email == "sophie-lane@example.com")
    assert "C" in sophie.ask


def hiring_client(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    return c


def test_hiring_pages_show_no_usage(tmp_path, monkeypatch):
    c = hiring_client(tmp_path, monkeypatch)
    for path in ("/hiring", "/hiring/liam-price@example.com"):
        html = c.get(path).text
        assert "トークン" not in html and 'class="avg"' not in html and "ev usage" not in html


def test_candidate_page_shows_interviews_verdicts_and_records(tmp_path, monkeypatch):
    c = hiring_client(tmp_path, monkeypatch)
    assert c.post("/api/hiring/liam-price@example.com/memo", json={"body": "候補者のメモ"}).status_code == 200
    html = c.get("/hiring/liam-price@example.com").text
    interviews = html.split("<h2>Interviews</h2>", 1)[1].split("</section>", 1)[0]
    assert len(re.findall(r"<tr>", interviews.split("<tbody>", 1)[1])) == 2
    assert "item verdict pass" in html
    assert "候補者のメモ" in html.split('id="record"', 1)[1]


def test_unknown_candidate_page_is_404(tmp_path, monkeypatch):
    c = hiring_client(tmp_path, monkeypatch)
    assert c.get("/hiring/nobody@example.com").status_code == 404
