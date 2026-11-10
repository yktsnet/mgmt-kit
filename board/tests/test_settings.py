from pathlib import Path

import pytest

from app.parse import SheetError
from app.settings import delete_item, new_version, save_item, seed, set_person, set_requisition, version_in_use
from app.store import connect

LADDER_MD = Path(__file__).resolve().parent.parent.parent / "ladder" / "docs" / "ladder.md"


@pytest.fixture
def db():
    d = connect(":memory:")
    seed(d, LADDER_MD, demo=True)
    return d


def texts(db, version, axis, level):
    return [r[0] for r in db.execute("SELECT text FROM definition_items WHERE version = ? AND axis = ? AND level = ? ORDER BY key", (version, axis, level))]


def test_save_add_and_delete_items(db):
    save_item(db, 1, "A", 3, "a", "直した判定文。", "設計資料")
    assert texts(db, 1, "A", 3)[0] == "直した判定文。"
    save_item(db, 1, "A", 3, None, "足した細目。", "")
    assert db.execute("SELECT key FROM definition_items WHERE text = '足した細目。'").fetchone()[0] == "c"
    delete_item(db, 1, "A", 3, "c")
    assert "足した細目。" not in texts(db, 1, "A", 3)


def test_last_item_of_a_cell_cannot_be_deleted(db):
    with pytest.raises(SheetError, match="C-L2"):
        delete_item(db, 1, "C", 2, "a")


def test_version_used_by_a_review_is_locked(db):
    db.execute("INSERT INTO files (id, path, modified, kind) VALUES ('f', 'reviews/x/y', 't', 'review')")
    db.execute("INSERT INTO reviews (file_id, email, period, version) VALUES ('f', 'y@example.com', 'x', 1)")
    assert version_in_use(db, 1)
    with pytest.raises(SheetError, match="New version"):
        save_item(db, 1, "A", 3, "a", "x", "")
    assert new_version(db) == 2
    save_item(db, 2, "A", 3, "a", "v2 だけ直す。", "")
    assert texts(db, 1, "A", 3)[0] != "v2 だけ直す。"


def test_people_rules(db):
    set_person(db, "jack-foster@example.com", evaluator="alice-walker@example.com", role="manager")
    row = db.execute("SELECT evaluator, role FROM people WHERE email = 'jack-foster@example.com'").fetchone()
    assert tuple(row) == ("alice-walker@example.com", "manager")
    with pytest.raises(SheetError):
        set_person(db, "jack-foster@example.com", evaluator="jack-foster@example.com")
    with pytest.raises(SheetError):
        set_person(db, "jack-foster@example.com", role="owner")


def test_requisition_rules(db):
    set_requisition(db, "開発", 3, {"A": 3, "B": 4})
    assert db.execute("SELECT count FROM requisitions WHERE name = '開発'").fetchone()[0] == 3
    with pytest.raises(SheetError):
        set_requisition(db, "開発", 1, {"A": 9})
