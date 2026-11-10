import datetime as dt
import os
import shutil
import sqlite3
import time
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.hiring import parse_candidate, results
from app.parse import SheetError, parse_requisitions, to_date, to_score
from app.settings import seed
from app.sources import FileRef
from app.sources.xlsx_folder import XlsxFolderSource
from app.store import connect
from app.sync import sync

SAMPLES = Path(__file__).resolve().parent.parent / "samples" / "drive"
LADDER_MD = Path(__file__).resolve().parent.parent.parent / "ladder" / "docs" / "ladder.md"


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


def levels(db, email):
    version = db.execute("SELECT version FROM candidates WHERE email = ?", (email,)).fetchone()[0]
    res, _, _ = results(db, email, version)
    return {a: (None if r.pending else r.level) for a, r in res.items()}


def test_samples_load(drive, db):
    result = sync(XlsxFolderSource(drive), db)
    assert result.errors == {}
    assert db.execute("SELECT count(*) FROM candidates").fetchone()[0] == 6
    row = db.execute("SELECT * FROM candidates WHERE email = 'liam-price@example.com'").fetchone()
    assert (row["version"], row["applied"], row["requisition"]) == (1, "2026-03-02", "リード")
    iv = db.execute("SELECT * FROM interviews WHERE email = 'liam-price@example.com' ORDER BY seq").fetchall()
    assert [(r["seq"], r["interviewer"]) for r in iv] == [(1, "alice-walker@example.com"), (2, "emma-hughes@example.com")]


def test_latest_interview_wins_per_item(drive, db):
    seed(db, LADDER_MD, demo=False)
    sync(XlsxFolderSource(drive), db)
    # 1回目 A4 B3 D3、2回目 B4 C2 E3。B は2回目、A と D は1回目の判定が残る
    assert levels(db, "liam-price@example.com") == {"A": 4, "B": 4, "C": 2, "D": 3, "E": 3}


def test_axis_not_asked_is_pending_and_unobserved_is_none(drive, db):
    seed(db, LADDER_MD, demo=False)
    sync(XlsxFolderSource(drive), db)
    noah, _, _ = results(db, "noah-reed@example.com", 1)
    assert noah["C"].pending
    sophie, _, _ = results(db, "sophie-lane@example.com", 1)
    assert (sophie["C"].level, sophie["C"].pending) == (None, False)
    assert sophie["A"].level == 1


def test_only_changed_files_are_read(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    edit(drive / "candidates" / "noah-reed.xlsx", "候補者", "B3", "リード")
    result = sync(src, db)
    assert result.read == ["candidates/noah-reed"]
    assert db.execute("SELECT requisition FROM candidates WHERE email = 'noah-reed@example.com'").fetchone()[0] == "リード"


def test_nothing_read_when_unchanged(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    assert sync(src, db).read == []


def test_removed_file_drops_candidate_and_interviews(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    (drive / "candidates" / "liam-price.xlsx").unlink()
    result = sync(src, db)
    assert len(result.removed) == 1
    assert db.execute("SELECT count(*) FROM candidates WHERE email = 'liam-price@example.com'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM interviews WHERE email = 'liam-price@example.com'").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM interview_verdicts WHERE email = 'liam-price@example.com'").fetchone()[0] == 0


def test_bad_file_is_reported_and_others_still_load(drive, db):
    src = XlsxFolderSource(drive)
    sync(src, db)
    edit(drive / "candidates" / "noah-reed.xlsx", "面接1", "E2", "たぶん")
    result = sync(src, db)
    assert "candidates/noah-reed" in result.errors
    assert db.execute("SELECT count(*) FROM candidates").fetchone()[0] == 5
    err = db.execute("SELECT error FROM files WHERE path = 'candidates/noah-reed'").fetchone()[0]
    assert "面接1 row 2" in err


def test_fixed_file_is_read_again(drive, db):
    src = XlsxFolderSource(drive)
    path = drive / "candidates" / "noah-reed.xlsx"
    edit(path, "面接1", "E2", "たぶん")
    sync(src, db)
    edit(path, "面接1", "E2", "○")
    result = sync(src, db)
    assert result.errors == {}
    assert db.execute("SELECT error FROM files WHERE path = 'candidates/noah-reed'").fetchone()[0] is None


def test_duplicate_email_keeps_newer_file(drive, db):
    src = XlsxFolderSource(drive)
    older = drive / "candidates" / "noah-reed.xlsx"
    newer = drive / "candidates" / "noah-reed-copy.xlsx"
    shutil.copy(older, newer)
    edit(newer, "候補者", "B3", "リード")
    req = "SELECT requisition FROM candidates WHERE email = 'noah-reed@example.com'"
    sync(src, db)
    assert db.execute(req).fetchone()[0] == "リード"
    # 何も変えずにもう一度回しても、古いほうに戻らない
    sync(src, db)
    assert db.execute(req).fetchone()[0] == "リード"
    # 新しいほうを消すと、古いほうが戻る
    newer.unlink()
    sync(src, db)
    assert db.execute(req).fetchone()[0] == "開発"


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
        "候補者": [["メモ", "並べ替えた"], ["メール", "X@Example.com"], ["氏名", "X"], ["版", "v2"]],
        "面接": [["所見", "面接官", "日付", "回"], ["ok", "Y@Example.com", "2026-04-01", 1]],
        "面接1": [["判定", "細目", "段階", "軸"], ["○", "a", "L2", "A"]],
    }
    c = parse_candidate(book)
    assert (c.email, c.version) == ("x@example.com", 2)
    (iv,) = c.interviews
    assert (iv.seq, iv.interviewer, iv.note) == (1, "y@example.com", "ok")
    assert iv.verdicts == {"A-L2-a": ("○", "")}


def test_interview_sheet_without_row_in_list_is_still_read():
    book = {"候補者": [["メール", "x@example.com"], ["版", "v1"]], "面接2": [["軸", "段階", "細目", "判定"], ["B", "L2", "a", "×"]]}
    (iv,) = parse_candidate(book).interviews
    assert (iv.seq, iv.interviewer, iv.verdicts) == (2, "", {"B-L2-a": ("×", "")})


def test_empty_interview_sheet_is_not_an_interview():
    book = {"候補者": [["メール", "x@example.com"], ["版", "v1"]], "面接": [["回", "日付"]], "面接1": [["軸", "段階", "細目", "判定"], ["A", "L2", "a", None]]}
    assert parse_candidate(book).interviews == []


def test_candidate_needs_version():
    with pytest.raises(SheetError, match="版"):
        parse_candidate({"候補者": [["メール", "x@example.com"]]})


def test_stage_in_sheet_is_not_read():
    c = parse_candidate({"候補者": [["メール", "x@example.com"], ["版", "v1"], ["段階", "内定"]]})
    assert not hasattr(c, "stage")


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


def test_old_candidate_tables_are_rebuilt_and_read_again(drive, tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(
        "CREATE TABLE files (id TEXT PRIMARY KEY, path TEXT NOT NULL, modified TEXT NOT NULL, kind TEXT NOT NULL, error TEXT, modified_by TEXT);"
        "CREATE TABLE candidates (email TEXT PRIMARY KEY, file_id TEXT NOT NULL, name TEXT NOT NULL, requisition TEXT NOT NULL, stage TEXT NOT NULL, applied TEXT, source TEXT NOT NULL);"
        "CREATE TABLE people (email TEXT PRIMARY KEY, name TEXT NOT NULL, evaluator TEXT, role TEXT NOT NULL DEFAULT 'member');"
    )
    src = XlsxFolderSource(drive)
    ref = next(r for r in src.list() if r.path == "candidates/noah-reed")
    old.execute("INSERT INTO files VALUES (?, ?, ?, 'candidate', NULL, NULL)", (ref.id, ref.path, ref.modified))
    old.execute("INSERT INTO candidates VALUES ('noah-reed@example.com', ?, 'Noah', '開発', '一次面接', NULL, '')", (ref.id,))
    old.commit()
    old.close()
    db = connect(path)
    assert "version" in {r[1] for r in db.execute("PRAGMA table_info(candidates)")}
    assert "hiring" in {r[1] for r in db.execute("PRAGMA table_info(people)")}
    # 更新日時は変わっていないが、行の無い候補者のファイルとして読み直す
    assert "candidates/noah-reed" in sync(src, db).read
