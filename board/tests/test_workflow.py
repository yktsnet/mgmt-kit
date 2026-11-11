from pathlib import Path

import pytest

from app.parse import SheetError
from app.settings import seed
from app.store import connect
from app.workflow import act, add_memo, allowed, records, state_of

LADDER_MD = Path(__file__).resolve().parent.parent.parent / "ladder" / "docs" / "ladder.md"
P = "2026-H2"
GRACE = "grace-turner@example.com"  # Reviewer は emma-hughes


@pytest.fixture
def db():
    d = connect(":memory:")
    seed(d, LADDER_MD, demo=True)
    return d


def me(db, name):
    return db.execute("SELECT * FROM people WHERE email = ?", (f"{name}@example.com",)).fetchone()


def test_reviewer_submits_and_manager_approves(db):
    emma, alice = me(db, "emma-hughes"), me(db, "alice-walker")
    assert allowed(db, emma, GRACE, P, ready=True) == ["submit"]
    act(db, emma, GRACE, P, "submit", ready=True)
    assert state_of(db, GRACE, P)["state"] == "submitted"
    assert allowed(db, emma, GRACE, P, ready=True) == ["reopen"]
    assert allowed(db, alice, GRACE, P, ready=True) == ["approve", "reopen"]
    act(db, alice, GRACE, P, "approve", ready=True)
    # Approved を戻せるのは Manager だけ
    assert allowed(db, emma, GRACE, P, ready=True) == []
    act(db, alice, GRACE, P, "reopen", ready=True)
    assert state_of(db, GRACE, P)["state"] == "draft"
    assert [r["body"] for r in records(db, GRACE, P)] == ["Reopen", "Approve", "Submit"]


def test_submit_needs_complete_verdicts(db):
    with pytest.raises(SheetError, match="途中"):
        act(db, me(db, "emma-hughes"), GRACE, P, "submit", ready=False)


def test_others_cannot_act(db):
    jack = me(db, "jack-foster")
    assert allowed(db, jack, GRACE, P, ready=True) == []
    with pytest.raises(SheetError, match="権限"):
        act(db, jack, GRACE, P, "submit", ready=True)


def test_reviewer_cannot_approve(db):
    emma = me(db, "emma-hughes")
    act(db, emma, GRACE, P, "submit", ready=True)
    with pytest.raises(SheetError):
        act(db, emma, GRACE, P, "approve", ready=True)


def test_memo_is_appended_and_empty_is_refused(db):
    emma = me(db, "emma-hughes")
    add_memo(db, emma, GRACE, P, "次は D を見る")
    with pytest.raises(SheetError):
        add_memo(db, emma, GRACE, P, "  ")
    (r,) = records(db, GRACE, P)
    assert (r["kind"], r["body"], r["by_name"]) == ("memo", "次は D を見る", "🐘 Emma Hughes")


def test_state_change_and_memo_are_recorded_with_time(db):
    import datetime as dt

    emma = me(db, "emma-hughes")
    act(db, emma, GRACE, P, "submit", ready=True)
    add_memo(db, emma, GRACE, P, "メモ")
    rs = records(db, GRACE, P)
    assert {r["kind"] for r in rs} == {"state", "memo"}
    for r in rs:
        assert dt.datetime.fromisoformat(r["at"])
