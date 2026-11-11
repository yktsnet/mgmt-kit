import json
import shutil
from pathlib import Path

import pytest

from app.demo import DOMAIN, STAFF
from app.store import connect
from app.usage import WINDOW_DAYS, summarize, sync_usage
from app.usage_report import _render, team

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


def test_repo_sample_emails_match_demo_staff():
    db = connect(":memory:")
    sync_usage(USAGE, db)
    assert {r[0] for r in db.execute("SELECT email FROM usage")} == {f"{n}@{DOMAIN}" for n in STAFF}


def test_active_time_counts_only_cli_when_recorded():
    r = _render(USAGE)
    day = {"date": "2026-04-01", "members": {
        "a@example.com": {"active_seconds": 900, "active_by_type": {"cli": 300, "user": 600}},
        "b@example.com": {"active_seconds": 500},
    }}
    out = r.cli_time_only(day)["members"]
    assert out["a@example.com"]["active_seconds"] == 300
    # 種類別の記録が無い日は、合計をそのまま使う
    assert out["b@example.com"]["active_seconds"] == 500


def test_render_load_counts_only_cli_time(tmp_path: Path, monkeypatch):
    r = _render(USAGE)
    (tmp_path / "2026-04-01.json").write_text(json.dumps({"date": "2026-04-01", "members": {
        "ann@example.com": {"active_seconds": 900, "active_by_type": {"cli": 300, "user": 600}},
    }}))
    monkeypatch.setattr(r, "DATA_DIR", tmp_path)
    assert r.load()[0]["members"]["ann@example.com"]["active_seconds"] == 300


def test_summary_counts_only_cli_time(usage):
    (usage / "data" / "2026-04-14.json").write_text(json.dumps({"date": "2026-04-14", "members": {
        "ann@example.com": {"active_seconds": 900, "active_by_type": {"cli": 300, "user": 600}},
    }}))
    _, _, rows = summarize(usage / "data")
    assert rows["ann@example.com"]["active_seconds"] == 300


def test_board_rows_count_only_cli_time(tmp_path: Path):
    d = tmp_path / "usage" / "claude-code"
    (d / "data").mkdir(parents=True)
    shutil.copy(USAGE / "render.py", d / "render.py")
    shutil.copy(USAGE.parent / "chart.py", d.parent / "chart.py")
    (d / "data" / "2026-04-01.json").write_text(json.dumps({"date": "2026-04-01", "members": {
        "ann@example.com": {"tokens": 200_000, "sessions": 1, "active_seconds": 900, "active_by_type": {"cli": 300, "user": 600}},
    }}))
    rows = team(d)["rows"]
    assert rows[0]["minutes"] == "5分"
