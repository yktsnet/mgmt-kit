"""評価の状態（Draft → Submitted → Approved）と記録。アプリが持ち、日時と誰がしたかを残す。"""

import datetime as dt
import sqlite3

from .parse import SheetError

DRAFT, SUBMITTED, APPROVED = "draft", "submitted", "approved"
# 操作 → (前の状態, 後の状態)
ACTIONS = {
    "submit": ((DRAFT,), SUBMITTED),
    "approve": ((SUBMITTED,), APPROVED),
    "reopen": ((SUBMITTED, APPROVED), DRAFT),
}
LABELS = {"submit": "Submit", "approve": "Approve", "reopen": "Reopen"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def state_of(db: sqlite3.Connection, email: str, period: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM review_states WHERE email = ? AND period = ?", (email, period)).fetchone()


def allowed(db: sqlite3.Connection, me: sqlite3.Row, email: str, period: str, ready: bool) -> list[str]:
    """me ができる操作。Submit は判定が出そろってから、Approve は Manager だけ。"""
    person = db.execute("SELECT evaluator FROM people WHERE email = ?", (email,)).fetchone()
    is_manager = me["role"] == "manager"
    is_reviewer = person is not None and person["evaluator"] == me["email"]
    row = state_of(db, email, period)
    state = row["state"] if row else DRAFT
    out = []
    if state == DRAFT and ready and (is_reviewer or is_manager):
        out.append("submit")
    if state == SUBMITTED and is_manager:
        out.append("approve")
    if (state == SUBMITTED and (is_reviewer or is_manager)) or (state == APPROVED and is_manager):
        out.append("reopen")
    return out


def act(db: sqlite3.Connection, me: sqlite3.Row, email: str, period: str, action: str, ready: bool) -> str:
    if action not in ACTIONS:
        raise SheetError(f"unknown action {action!r}")
    if action not in allowed(db, me, email, period, ready):
        if action == "submit" and not ready:
            raise SheetError("判定が途中なので Submit できない")
        raise SheetError("この操作をする権限が無い")
    _, after = ACTIONS[action]
    at = now()
    with db:
        db.execute(
            "INSERT INTO review_states (email, period, state, at, by) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(email, period) DO UPDATE SET state = excluded.state, at = excluded.at, by = excluded.by",
            (email, period, after, at, me["email"]),
        )
        db.execute(
            "INSERT INTO review_records (email, period, at, by, kind, body) VALUES (?, ?, ?, ?, 'state', ?)",
            (email, period, at, me["email"], LABELS[action]),
        )
    return after


def add_memo(db: sqlite3.Connection, me: sqlite3.Row, email: str, period: str, body: str) -> None:
    body = body.strip()
    if not body:
        raise SheetError("メモが空になっている")
    with db:
        db.execute(
            "INSERT INTO review_records (email, period, at, by, kind, body) VALUES (?, ?, ?, ?, 'memo', ?)",
            (email, period, now(), me["email"], body),
        )


def records(db: sqlite3.Connection, email: str, period: str) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT r.*, p.name AS by_name FROM review_records r LEFT JOIN people p ON p.email = r.by "
        "WHERE r.email = ? AND r.period = ? ORDER BY r.at DESC, r.id DESC",
        (email, period),
    ).fetchall()


def set_next_axis(db: sqlite3.Connection, me: sqlite3.Row, email: str, period: str, axis: str) -> None:
    """次に上げる1軸を決める。その人の Reviewer か Manager だけができ、決めたことは記録に残す。"""
    from .parse import AXES

    if axis not in AXES:
        raise SheetError("軸は A〜E のどれか")
    person = db.execute("SELECT evaluator FROM people WHERE email = ?", (email,)).fetchone()
    if not person or not (me["role"] == "manager" or person["evaluator"] == me["email"]):
        raise SheetError("この操作をする権限が無い")
    at = now()
    with db:
        db.execute(
            "INSERT INTO growth_plans (email, period, axis, at, by) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(email, period) DO UPDATE SET axis = excluded.axis, at = excluded.at, by = excluded.by",
            (email, period, axis, at, me["email"]),
        )
        db.execute(
            "INSERT INTO review_records (email, period, at, by, kind, body) VALUES (?, ?, ?, ?, 'memo', ?)",
            (email, period, at, me["email"], f"次に上げる軸を {axis} にした"),
        )
