import shutil
from pathlib import Path

import pytest

from app.definition import Item
from app.parse import SheetError
from app.review import AxisResult, axis_result, parse_review, person_level, results_for, template_rows
from app.sources.xlsx_folder import XlsxFolderSource
from app.store import connect
from app.sync import sync

BOARD = Path(__file__).resolve().parent.parent
SAMPLES = BOARD / "samples" / "drive"

# A の各段階に細目を2つずつ
ITEMS = [Item("A", lv, k, f"A{lv}{k}", "") for lv in range(1, 6) for k in "ab"]


def v(**kw):
    return {k.replace("_", "-"): val for k, val in kw.items()}


def test_all_pass_reaches_l5():
    verdicts = {x.id: "○" for x in ITEMS if x.level >= 2}
    assert axis_result(ITEMS, verdicts, "A") == AxisResult(5, False)


def test_fail_stops_below_even_with_blanks():
    verdicts = {"A-L2-a": "○", "A-L2-b": "○", "A-L3-a": "×"}
    assert axis_result(ITEMS, verdicts, "A") == AxisResult(2, False)


def test_blank_cell_is_pending():
    verdicts = {"A-L2-a": "○", "A-L2-b": "○", "A-L3-a": "○"}
    assert axis_result(ITEMS, verdicts, "A") == AxisResult(None, True)


def test_unobserved_at_l2_is_unobserved_axis():
    assert axis_result(ITEMS, {"A-L2-a": "未観測", "A-L2-b": "○"}, "A") == AxisResult(None, False)


def test_unobserved_above_l2_stops_there():
    verdicts = {"A-L2-a": "○", "A-L2-b": "○", "A-L3-a": "未観測", "A-L3-b": "○"}
    assert axis_result(ITEMS, verdicts, "A") == AxisResult(2, False)


def test_fail_at_l2_is_l1():
    assert axis_result(ITEMS, {"A-L2-a": "×"}, "A") == AxisResult(1, False)


def test_person_level_is_lower_of_a_and_b():
    r = {a: AxisResult(3, False) for a in "CDE"}
    assert person_level({**r, "A": AxisResult(4, False), "B": AxisResult(2, False)}) == 2
    assert person_level({**r, "A": AxisResult(4, False), "B": AxisResult(None, True)}) is None
    assert person_level({**r, "A": AxisResult(None, False), "B": AxisResult(2, False)}) is None


def test_template_skips_l1():
    rows = template_rows(ITEMS)
    assert rows[0][4] == "判定"
    assert {r[1] for r in rows[1:]} == {"L2", "L3", "L4", "L5"}


def book(verdict="○"):
    return {
        "対象": [["メール", "X@example.com"], ["期", "2026-H2"], ["版", "v1"], ["Reviewer", "r@example.com"]],
        "評価": [["軸", "段階", "細目", "判定文", "判定", "根拠"], ["A", "L2", "a", "t", verdict, "見た"], ["A", "L2", "b", "t", "", ""]],
    }


def test_parse_review_accepts_typed_variants():
    r = parse_review(book("o"))
    assert (r.email, r.version, r.reviewer) == ("x@example.com", 1, "r@example.com")
    assert r.verdicts == {"A-L2-a": ("○", "見た")}


def test_bad_verdict_is_an_error():
    with pytest.raises(SheetError, match="判定"):
        parse_review(book("たぶん"))


def test_samples_sync_into_levels(tmp_path):
    drive = tmp_path / "drive"
    shutil.copytree(SAMPLES, drive)
    db = connect(":memory:")
    assert sync(XlsxFolderSource(drive), db).errors == {}
    rows = {r["email"]: r["file_id"] for r in db.execute("SELECT email, file_id FROM reviews")}
    assert len(rows) == 7
    # ben-carter は A3 B1 C4 D2 E3
    results, judged, total = results_for(db, rows["ben-carter@example.com"])
    assert {a: r.level for a, r in results.items()} == {"A": 3, "B": 1, "C": 4, "D": 2, "E": 3}
    assert person_level(results) == 1
    # henry-ward の D は未観測
    results, _, _ = results_for(db, rows["henry-ward@example.com"])
    assert results["D"] == AxisResult(None, False)
    # daniel-brooks は C〜E が途中
    results, judged, total = results_for(db, rows["daniel-brooks@example.com"])
    assert results["C"].pending and not results["A"].pending
    assert 0 < judged < total
