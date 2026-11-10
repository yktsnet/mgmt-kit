import os
import shutil
import time
from pathlib import Path

import pytest

from app.ladder import parse_personas, parse_scoresheet, sync_ladder
from app.parse import SheetError
from app.sources.xlsx_folder import XlsxFolderSource
from app.store import connect
from app.sync import sync

BOARD = Path(__file__).resolve().parent.parent
SAMPLES = BOARD / "samples"
PERSONAS = BOARD.parent / "ladder" / "docs" / "personas.md"
TEMPLATE = BOARD.parent / "ladder" / ".claude" / "skills" / "ladder-score" / "reference" / "scoresheet-template.md"


@pytest.fixture
def scores(tmp_path: Path) -> Path:
    d = tmp_path / "ladder"
    shutil.copytree(SAMPLES / "ladder", d)
    return d


def test_parses_the_scoresheet_template():
    # 書式の正本にある見本をそのまま読めること
    text = TEMPLATE.read_text(encoding="utf-8").split("```markdown", 1)[1].split("```", 1)[0]
    s = parse_scoresheet(text)
    assert s.scores == {"A": 3, "B": 4, "D": 2, "E": 2}
    assert s.level == 3


def test_parses_repo_personas():
    p = parse_personas(PERSONAS.read_text(encoding="utf-8"))
    assert sorted(p) == [1, 2, 3, 4, 5]
    assert p[1] == {"A": 1, "B": 1, "C": 3, "D": 1, "E": 1}


def test_bad_title_is_an_error():
    with pytest.raises(SheetError):
        parse_scoresheet("# メモ\n\n## 点\n\n| A |\n|---|\n| L1 |\n")


def test_sync_loads_staff_and_personas(scores):
    db = connect(":memory:")
    assert sync_ladder(scores, PERSONAS, "example.com", db) == {}
    assert db.execute("SELECT count(*) FROM staff").fetchone()[0] == 10
    row = db.execute("SELECT level, period FROM staff WHERE email = 'ben-carter@example.com'").fetchone()
    assert row["level"] == 1
    ben = dict(db.execute("SELECT axis, value FROM scores WHERE email = 'ben-carter@example.com' AND origin = 'ladder'").fetchall())
    assert ben == {"A": 3, "B": 1, "C": 4, "D": 2, "E": 3}
    assert db.execute("SELECT count(DISTINCT level) FROM personas").fetchone()[0] == 5


def test_rescoring_replaces_scores_and_removal_drops_them(scores):
    db = connect(":memory:")
    sync_ladder(scores, PERSONAS, "example.com", db)
    p = scores / "jack-foster.md"
    p.write_text(p.read_text(encoding="utf-8").replace("| L1 | L1 |", "| L2 | L2 |", 1), encoding="utf-8")
    t = time.time() + 10
    os.utime(p, (t, t))
    sync_ladder(scores, PERSONAS, "example.com", db)
    assert db.execute("SELECT value FROM scores WHERE email = 'jack-foster@example.com' AND axis = 'B'").fetchone()[0] == 2
    p.unlink()
    sync_ladder(scores, PERSONAS, "example.com", db)
    assert db.execute("SELECT count(*) FROM scores WHERE email = 'jack-foster@example.com'").fetchone()[0] == 0


def test_sheet_sync_leaves_ladder_rows_alone(scores, tmp_path):
    db = connect(":memory:")
    sync_ladder(scores, PERSONAS, "example.com", db)
    drive = tmp_path / "drive"
    shutil.copytree(SAMPLES / "drive", drive)
    sync(XlsxFolderSource(drive), db)
    assert db.execute("SELECT count(*) FROM staff").fetchone()[0] == 10
