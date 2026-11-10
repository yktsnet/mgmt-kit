import json
import shutil
from pathlib import Path

import pytest

from app.ladder import sync_ladder
from app.store import connect
from app.usage import WINDOW_DAYS, summarize, sync_usage

BOARD = Path(__file__).resolve().parent.parent
USAGE = BOARD.parent / "usage" / "tools" / "usage" / "claude-code"


@pytest.fixture
def usage(tmp_path: Path) -> Path:
    d = tmp_path / "claude-code"
    (d / "data").mkdir(parents=True)
    (d / "github.json").write_text(json.dumps({"ann": "ann-gh"}))
    for day, cost, skills in [("2026-04-01", 10, {"a": 1}), ("2026-04-10", 5, {"a": 2, "b": 1}), ("2026-04-14", 1, {})]:
        (d / "data" / f"{day}.json").write_text(json.dumps({
            "date": day,
            "members": {"Ann@example.com": {"cost_usd": cost, "sessions": 1, "commits": 2, "skills": skills}},
            "issues": {"ann-gh": {"opened": 3, "closed": 1}},
        }))
    return d


def test_window_counts_back_from_the_last_day(usage):
    since, until, rows = summarize(usage / "data", {"ann": "ann-gh"})
    assert (since, until) == ("2026-04-01", "2026-04-14")
    assert WINDOW_DAYS == 14
    ann = rows["ann@example.com"]
    assert (ann["cost_usd"], ann["active_days"], ann["commits"], ann["skills"], ann["issues_opened"]) == (16, 3, 6, 4, 9)


def test_days_before_the_window_are_left_out(usage):
    (usage / "data" / "2026-03-31.json").write_text(json.dumps({"date": "2026-03-31", "members": {"ann@example.com": {"cost_usd": 100}}}))
    _, _, rows = summarize(usage / "data")
    assert rows["ann@example.com"]["cost_usd"] == 16


def test_sync_skips_when_unchanged(usage):
    db = connect(":memory:")
    assert sync_usage(usage, db) is True
    assert sync_usage(usage, db) is False
    assert db.execute("SELECT cost_usd FROM usage WHERE email = 'ann@example.com'").fetchone()[0] == 16


def test_repo_sample_joins_with_ladder_staff():
    db = connect(":memory:")
    sync_ladder(BOARD / "samples" / "ladder", None, "example.com", db)
    sync_usage(USAGE, db)
    joined = db.execute("SELECT count(*) FROM staff JOIN usage USING (email)").fetchone()[0]
    assert joined == 10
