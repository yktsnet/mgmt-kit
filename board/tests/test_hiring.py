import shutil
from pathlib import Path

import pytest

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
