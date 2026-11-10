"""誰が何を見られるか。一覧・1人のページ・現在地・API は、どれもここの決まりで絞る。

- Manager はすべてを見られる
- Member は、自分が Reviewer として担当する人の評価・記録と、Approved になった自分の評価だけを見られる
- 採用（候補者・面接の所見）は、設定で採用を付けた人と Manager が見られる
- 設定は Manager だけが見られ、直せる
- タブは見られるものがある人にだけ出す。採用も担当も無い Member には現在地だけが出る
"""

import sqlite3

from .workflow import APPROVED, state_of


def is_manager(me: sqlite3.Row | None) -> bool:
    return me is not None and me["role"] == "manager"


def reviews_of(db: sqlite3.Connection, me: sqlite3.Row, email: str) -> bool:
    """me が email の Reviewer か。"""
    return db.execute("SELECT 1 FROM people WHERE email = ? AND evaluator = ?", (email, me["email"])).fetchone() is not None


def can_see_review(db: sqlite3.Connection, me: sqlite3.Row | None, email: str, period: str | None) -> bool:
    if me is None:
        return False
    if is_manager(me) or reviews_of(db, me, email):
        return True
    if email != me["email"] or not period:
        return False
    st = state_of(db, email, period)
    return st is not None and st["state"] == APPROVED


def has_reviews(db: sqlite3.Connection, me: sqlite3.Row | None) -> bool:
    """評価のタブを出すか。見られる評価が1件も無い人には出さない。"""
    if me is None:
        return False
    if is_manager(me) or db.execute("SELECT 1 FROM people WHERE evaluator = ?", (me["email"],)).fetchone():
        return True
    return db.execute("SELECT 1 FROM review_states WHERE email = ? AND state = ?", (me["email"], APPROVED)).fetchone() is not None


def can_see_records(db: sqlite3.Connection, me: sqlite3.Row | None, email: str) -> bool:
    """評価の記録（メモと状態の切り替え）。本人には、Approved になっても見せない。"""
    return me is not None and (is_manager(me) or reviews_of(db, me, email))


def can_see_person(db: sqlite3.Connection, me: sqlite3.Row | None, email: str) -> bool:
    """現在地にその人の行を出すか。本人の行は利用状況のために出し、評価は can_see_review で別に絞る。"""
    return me is not None and (is_manager(me) or email == me["email"] or reviews_of(db, me, email))


def can_hire(me: sqlite3.Row | None) -> bool:
    return me is not None and (is_manager(me) or bool(me["hiring"]))
