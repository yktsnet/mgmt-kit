from pathlib import Path

import pytest

from app.definition import from_ladder_md, latest_version, parse_definition, split_statement
from app.parse import AXES, SheetError
from app.store import connect

BOARD = Path(__file__).resolve().parent.parent
LADDER_MD = BOARD.parent / "ladder" / "docs" / "ladder.md"
HEADER = ["軸", "段階", "細目", "判定文", "Evidence"]


def full(version_rows=None):
    rows = [HEADER] + [[a, f"L{lv}", "a", f"{a}{lv}", ""] for a in AXES for lv in range(1, 6)]
    return rows + (version_rows or [])


def test_split_statement_by_period():
    assert split_statement("一つ目。二つ目。") == ["一つ目。", "二つ目。"]


def test_ladder_md_covers_every_cell():
    items = from_ladder_md(LADDER_MD.read_text(encoding="utf-8"))
    cells = {(x.axis, x.level) for x in items}
    assert cells == {(a, lv) for a in AXES for lv in range(1, 6)}
    a3 = [x.text for x in items if x.axis == "A" and x.level == 3]
    assert a3[0] == "性能・運用・移行の欠落を要件に対して指摘できる。"
    assert len(a3) == 2


def test_versions_are_kept_apart():
    v = parse_definition({"v1": full(), "v2": full([["A", "L3", "b", "足した細目", ""]]), "メモ": [["x"]]})
    assert sorted(v) == [1, 2]
    assert len(v[2]) == len(v[1]) + 1


@pytest.mark.parametrize(
    "row,msg",
    [
        (["F", "L1", "b", "x", ""], "軸"),
        (["A", "L6", "b", "x", ""], "段階"),
        (["A", "L1", "ab", "x", ""], "細目"),
        (["A", "L1", "a", "重なり", ""], "duplicate"),
    ],
)
def test_bad_rows(row, msg):
    with pytest.raises(SheetError, match=msg):
        parse_definition({"v1": full([row])})


def test_cell_without_items_is_an_error():
    rows = [r for r in full() if r[:2] != ["C", "L4"]]
    with pytest.raises(SheetError, match="C-L4"):
        parse_definition({"v1": rows})


def test_seed_builds_v1_from_ladder_md_once():
    from app.settings import seed

    db = connect(":memory:")
    seed(db, LADDER_MD, demo=False)
    assert latest_version(db) == 1
    n = db.execute("SELECT count(*) FROM definition_items").fetchone()[0]
    assert n == len(from_ladder_md(LADDER_MD.read_text(encoding="utf-8")))
    seed(db, LADDER_MD, demo=False)
    assert db.execute("SELECT count(*) FROM definition_items").fetchone()[0] == n
    assert db.execute("SELECT count(*) FROM people").fetchone()[0] == 0


def test_old_evidence_header_is_still_read():
    rows = [["軸", "段階", "細目", "判定文", "読むもの"]] + [[a, f"L{lv}", "a", "x", "前の見出し"] for a in AXES for lv in range(1, 6)]
    assert parse_definition({"v1": rows})[1][0].evidence == "前の見出し"
