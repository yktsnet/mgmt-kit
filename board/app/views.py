"""画面に出す値を SQLite から組み立てる。HTML は知らない。"""

import datetime as dt
import sqlite3
from dataclasses import dataclass

from .parse import AXES

LEVELS_DESC = (5, 4, 3, 2, 1)


@dataclass
class DefinitionView:
    versions: list[int]
    version: int | None
    # (段階, 軸) → 細目の並び
    cells: dict[tuple[int, str], list[sqlite3.Row]]
    count: int
    # 評価が使っている版は直せない
    in_use: bool


def definition(db: sqlite3.Connection, version: int | None) -> DefinitionView:
    versions = [r[0] for r in db.execute("SELECT DISTINCT version FROM definition_items ORDER BY version")]
    if version not in versions:
        version = versions[-1] if versions else None
    cells: dict[tuple[int, str], list[sqlite3.Row]] = {(lv, a): [] for lv in LEVELS_DESC for a in AXES}
    rows = db.execute("SELECT * FROM definition_items WHERE version = ? ORDER BY axis, level, key", (version,)).fetchall()
    for r in rows:
        cells[(r["level"], r["axis"])].append(r)
    return DefinitionView(versions, version, cells, len(rows), version is not None and db.execute("SELECT 1 FROM reviews WHERE version = ? LIMIT 1", (version,)).fetchone() is not None)


@dataclass
class Assignment:
    evaluator: sqlite3.Row | None
    people: list[sqlite3.Row]


def assignments(db: sqlite3.Connection) -> list[Assignment]:
    """担当ごとに、評価する人を並べる。未割り当ての人は最後にまとめる。"""
    people = db.execute("SELECT * FROM people ORDER BY name").fetchall()
    by_email = {p["email"]: p for p in people}
    groups: dict[str | None, list[sqlite3.Row]] = {}
    for p in people:
        groups.setdefault(p["evaluator"], []).append(p)
    out = [Assignment(by_email.get(ev), ps) for ev, ps in sorted(((k, v) for k, v in groups.items() if k), key=lambda kv: by_email[kv[0]]["name"])]
    if None in groups:
        out.append(Assignment(None, groups[None]))
    return out


def requisitions(db: sqlite3.Connection) -> list[tuple[sqlite3.Row, list[int | None]]]:
    out = []
    for r in db.execute("SELECT * FROM requisitions ORDER BY rowid"):
        t = dict(db.execute("SELECT axis, value FROM requisition_targets WHERE name = ?", (r["name"],)).fetchall())
        out.append((r, [t.get(a) for a in AXES]))
    return out


def errors(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute("SELECT path, error FROM files WHERE error IS NOT NULL ORDER BY path").fetchall()


def people(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT p.email, p.name, p.evaluator, p.role, e.name AS evaluator_name FROM people p "
        "LEFT JOIN people e ON e.email = p.evaluator ORDER BY p.rowid"
    ).fetchall()


# ---- 評価


@dataclass
class ReviewRow:
    email: str
    name: str
    # 判定の埋まり方：not-started / in-progress / ready（段階が出そろった）
    status: str
    # アプリが持つ状態：draft / submitted / approved
    state: str
    judged: int
    total: int
    levels: dict[str, "object"]
    level: int | None
    file_id: str | None


@dataclass
class ReviewerGroup:
    reviewer: sqlite3.Row | None
    rows: list[ReviewRow]


def periods(db: sqlite3.Connection) -> list[str]:
    return [r[0] for r in db.execute("SELECT DISTINCT period FROM reviews ORDER BY period")]


def _row(db: sqlite3.Connection, person: sqlite3.Row, file_id: str | None, period: str | None = None) -> ReviewRow:
    from .review import person_level, results_for

    from .workflow import DRAFT, state_of

    st = state_of(db, person["email"], period) if period else None
    state = st["state"] if st else DRAFT
    if not file_id:
        return ReviewRow(person["email"], person["name"], "not-started", state, 0, 0, {}, None, None)
    results, judged, total = results_for(db, file_id)
    pending = any(r.pending for r in results.values())
    status = "ready" if not pending else ("in-progress" if judged else "not-started")
    return ReviewRow(person["email"], person["name"], status, state, judged, total, results, person_level(results), file_id)


def reviews(db: sqlite3.Connection, period: str | None) -> list[ReviewerGroup]:
    files = {r["email"]: r["file_id"] for r in db.execute("SELECT email, file_id FROM reviews WHERE period = ?", (period,))}
    people = db.execute("SELECT * FROM people ORDER BY rowid").fetchall()
    by_email = {p["email"]: p for p in people}
    groups: dict[str | None, list[ReviewRow]] = {}
    for p in people:
        groups.setdefault(p["evaluator"], []).append(_row(db, p, files.get(p["email"]), period))
    out = [ReviewerGroup(by_email.get(ev), rows) for ev, rows in groups.items() if ev]
    out.sort(key=lambda g: g.reviewer["name"] if g.reviewer else "")
    if None in groups:
        out.append(ReviewerGroup(None, groups[None]))
    return out


def review_detail(db: sqlite3.Connection, period: str, email: str):
    from .review import JUDGED_LEVELS

    person = db.execute(
        "SELECT p.*, e.name AS evaluator_name FROM people p LEFT JOIN people e ON e.email = p.evaluator WHERE p.email = ?", (email,)
    ).fetchone()
    if not person:
        return None
    r = db.execute("SELECT * FROM reviews WHERE period = ? AND email = ?", (period, email)).fetchone()
    row = _row(db, person, r["file_id"] if r else None, period)
    sheet = db.execute("SELECT modified, modified_by FROM files WHERE id = ?", (r["file_id"],)).fetchone() if r else None
    cells: dict[tuple[int, str], list] = {}
    if r:
        verdicts = {v["item"]: v for v in db.execute("SELECT * FROM verdicts WHERE file_id = ?", (r["file_id"],))}
        for it in db.execute("SELECT * FROM definition_items WHERE version = ? ORDER BY key", (r["version"],)):
            if it["level"] in JUDGED_LEVELS:
                v = verdicts.get(f"{it['axis']}-L{it['level']}-{it['key']}")
                cells.setdefault((it["level"], it["axis"]), []).append((it, v))
    from .workflow import records, state_of

    st = state_of(db, email, period)
    # Submit したあとでシートが直されたら、出した内容と画面の判定がずれている
    edited_after = bool(st and sheet and st["state"] != "draft" and sheet["modified"] > st["at"])
    return {"person": person, "review": r, "row": row, "cells": cells, "sheet": sheet, "state": st, "edited_after": edited_after, "records": records(db, email, period)}


# ---- 現在地


@dataclass
class NowRow:
    email: str
    name: str
    period: str | None
    level: int | None
    levels: dict
    suggested: str | None
    chosen: str | None
    chosen_by: str | None
    # 次に上げる軸を決める役。まだ決めていないときに名前を出す
    reviewer_name: str | None


def next_axis(levels: dict) -> str | None:
    """最も低い軸。未観測と途中の軸は選ばない。同じ低さなら A から順に選ぶ。"""
    from .parse import AXES

    decided = [(r.level, a) for a in AXES if (r := levels.get(a)) and not r.pending and r.level is not None]
    return min(decided)[1] if decided else None


def now(db: sqlite3.Connection) -> tuple[list[NowRow], list[tuple[str, list[str]]]]:
    """在籍者ごとの次に上げる1軸と、L2 で止まっている人たち。利用状況の図と表は usage_report が作る。"""
    people = db.execute("SELECT * FROM people ORDER BY rowid").fetchall()
    names = {p["email"]: p["name"] for p in people}

    rows, stops = [], {}
    for p in people:
        rv = db.execute("SELECT * FROM reviews WHERE email = ? ORDER BY period DESC LIMIT 1", (p["email"],)).fetchone()
        levels, level, period = {}, None, None
        if rv:
            r = _row(db, p, rv["file_id"], rv["period"])
            levels, level, period = r.levels, r.level, rv["period"]
            # L2 の判定文は型が強制するものだけで書いてあるので、L2 で止まるのは型の欠陥を指す（ladder/docs/scoring.md）。
            # L3 から上で止まるのは、上の段階ほど届きにくいだけなので数えない
            for a, res in levels.items():
                if not res.pending and res.level == 1:
                    stops.setdefault(a, []).append(p["name"])
        plan = db.execute(
            "SELECT g.axis, q.name AS by_name FROM growth_plans g LEFT JOIN people q ON q.email = g.by WHERE g.email = ? AND g.period = ?",
            (p["email"], period),
        ).fetchone() if period else None
        rows.append(NowRow(
            p["email"], p["name"], period, level, levels, next_axis(levels),
            plan["axis"] if plan else None, plan["by_name"] if plan else None,
            names.get(p["evaluator"]),
        ))
    together = sorted(((a, names) for a, names in stops.items() if len(names) >= 2), key=lambda x: (-len(x[1]), x[0]))
    return rows, together
