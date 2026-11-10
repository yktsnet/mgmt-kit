import datetime as dt
import os
import shutil
import time
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.parse import SheetError, parse_candidate, parse_requisitions, to_date, to_score
from app.sources import FileRef
from app.sources.xlsx_folder import XlsxFolderSource
from app.store import connect
from app.sync import sync

SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "drive"


@pytest.fixture
def drive(tmp_path: Path) -> Path:
    root = tmp_path / "drive"
    shutil.copytree(SAMPLES, root)
    return root


@pytest.fixture
def db():
    return connect(":memory:")


def touch_later(path: Path) -> None:
    # 更新日時を確実に進める。ファイルシステムによっては秒より細かく記録しない
    t = time.time() + 10
    os.utime(path, (t, t))


def edit(path: Path, sheet: str, cell: str, value) -> None:
    wb = load_workbook(path)
    wb[sheet][cell] = value
    wb.save(path)
    touch_later(path)


def test_samples_load(drive, db):
    result = sync(XlsxFolderSource(drive), db)
    assert result.errors == {}
    assert db.execute("SELECT count(*) FROM candidates").fetchone()[0] == 6
    row = db.execute("SELECT * FROM candidates WHERE email = 'liam-price@example.com'").fetchone()
    assert (row["stage"], row["applied"], row["requisition"]) == ("最終面接", "2026-03-02", "リード")


def test_latest_interview_wins_per_axis(drive, db):
    sync(XlsxFolderSource(drive), db)
    scores = dict(db.execute("SELECT axis, value FROM scores WHERE email = 'liam-price@example.com'").fetchall())
    # 1回目 A4 B3 D3、2回目 B4 C2 E3。B は2回目、A と D は1回目の値が残る
    assert scores == {"A": 4, "B": 4, "C": 2, "D": 3, "E": 3}


def test_unobserved_axis_is_absent(drive, db):
    sync(XlsxFolderSource(drive), db)
    axes = {r[0] for r in db.execute("SELECT axis FROM scores WHERE email = 'noah-reed@example.com'")}
    assert "C" not in axes


def test_only_changed_files_are_read(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    edit(drive / "candidates" / "noah-reed.xlsx", "候補者", "B4", "最終面接")
    result = sync(src, db)
    assert result.read == ["candidates/noah-reed"]
    assert db.execute("SELECT stage FROM candidates WHERE email = 'noah-reed@example.com'").fetchone()[0] == "最終面接"


def test_nothing_read_when_unchanged(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    assert sync(src, db).read == []


def test_removed_file_drops_candidate_and_scores(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    (drive / "candidates" / "liam-price.xlsx").unlink()
    result = sync(src, db)
    assert len(result.removed) == 1
    assert db.execute("SELECT count(*) FROM candidates WHERE email = 'liam-price@example.com'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM scores WHERE email = 'liam-price@example.com'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM interviews WHERE email = 'liam-price@example.com'").fetchone()[0] == 0


def test_bad_file_is_reported_and_others_still_load(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    edit(drive / "candidates" / "noah-reed.xlsx", "面接", "C2", 7)
    result = sync(src, db)
    assert "candidates/noah-reed" in result.errors
    assert db.execute("SELECT count(*) FROM candidates").fetchone()[0] == 5
    err = db.execute("SELECT error FROM files WHERE path = 'candidates/noah-reed'").fetchone()[0]
    assert "1-5" in err


def test_fixed_file_is_read_again(drive, db):
    src = XlsxFolderSource(drive)
    path = drive / "candidates" / "noah-reed.xlsx"
    edit(path, "面接", "C2", 7)
    sync(src, db)
    edit(path, "面接", "C2", 3)
    result = sync(src, db)
    assert result.errors == {}
    assert db.execute("SELECT error FROM files WHERE path = 'candidates/noah-reed'").fetchone()[0] is None


def test_duplicate_email_keeps_newer_file(drive, db):
    src = XlsxFolderSource(drive)
    older = drive / "candidates" / "noah-reed.xlsx"
    newer = drive / "candidates" / "noah-reed-copy.xlsx"
    shutil.copy(older, newer)
    edit(newer, "候補者", "B4", "内定")
    sync(src, db)
    assert db.execute("SELECT stage FROM candidates WHERE email = 'noah-reed@example.com'").fetchone()[0] == "内定"
    # 何も変えずにもう一度回しても、古いほうに戻らない
    sync(src, db)
    assert db.execute("SELECT stage FROM candidates WHERE email = 'noah-reed@example.com'").fetchone()[0] == "内定"
    # 新しいほうを消すと、古いほうが戻る
    newer.unlink()
    sync(src, db)
    assert db.execute("SELECT stage FROM candidates WHERE email = 'noah-reed@example.com'").fetchone()[0] == "一次面接"


def test_files_outside_layout_are_ignored(drive, db):
    shutil.copy(drive / "candidates" / "noah-reed.xlsx", drive / "memo.xlsx")
    (drive / "candidates" / "~$noah-reed.xlsx").write_bytes(b"lock")
    result = sync(XlsxFolderSource(drive), db)
    assert "memo" not in result.read
    assert result.errors == {}


def test_duplicate_requisition_is_an_error():
    book = {"求める人材": [["枠", "人数", "A"], ["開発", 1, 3], ["開発", 2, 4]]}
    with pytest.raises(SheetError, match="duplicate"):
        parse_requisitions(book)


def test_headers_are_read_by_label_not_position():
    book = {
        "候補者": [["メモ", "並べ替えた"], ["メール", "X@Example.com"], ["氏名", "X"], ["段階", "応募"]],
        "面接": [["所見", "E", "日付", "A"], ["ok", 2, "2026-04-01", 5]],
    }
    c = parse_candidate(book)
    assert c.email == "x@example.com"
    assert c.scores() == {"A": 5, "E": 2}


@pytest.mark.parametrize("v,ok", [(3, 3), (3.0, 3), ("4", 4), (None, None), ("", None)])
def test_score_accepts(v, ok):
    assert to_score(v, "t") == ok


@pytest.mark.parametrize("v", [0, 6, 3.5, "high"])
def test_score_rejects(v):
    with pytest.raises(SheetError):
        to_score(v, "t")


@pytest.mark.parametrize(
    "v,want",
    [
        (dt.datetime(2026, 3, 2), dt.date(2026, 3, 2)),
        ("2026/03/02", dt.date(2026, 3, 2)),
        # Sheets の日付の通し番号
        ({"serial_date": 46083}, dt.date(2026, 3, 2)),
        (None, None),
    ],
)
def test_to_date(v, want):
    assert to_date(v) == want


def test_xlsx_ref_has_no_extension(drive):
    refs = XlsxFolderSource(drive).list()
    assert FileRef in {type(r) for r in refs}
    assert "candidates/noah-reed" in {r.path for r in refs}
