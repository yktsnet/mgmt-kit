"""画面に出す値を SQLite から組み立てる。HTML は知らない。"""

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


def definition(db: sqlite3.Connection, version: int | None) -> DefinitionView:
    versions = [r[0] for r in db.execute("SELECT DISTINCT version FROM definition_items ORDER BY version")]
    if version not in versions:
        version = versions[-1] if versions else None
    cells: dict[tuple[int, str], list[sqlite3.Row]] = {(lv, a): [] for lv in LEVELS_DESC for a in AXES}
    rows = db.execute("SELECT * FROM definition_items WHERE version = ? ORDER BY axis, level, key", (version,)).fetchall()
    for r in rows:
        cells[(r["level"], r["axis"])].append(r)
    return DefinitionView(versions, version, cells, len(rows))


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
        "SELECT p.email, p.name, p.evaluator, e.name AS evaluator_name FROM people p "
        "LEFT JOIN people e ON e.email = p.evaluator ORDER BY p.rowid"
    ).fetchall()


# ---- 評価


@dataclass
class ReviewRow:
    email: str
    name: str
    status: str  # not-started / in-progress / done
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


def _row(db: sqlite3.Connection, person: sqlite3.Row, file_id: str | None) -> ReviewRow:
    from .review import person_level, results_for

    if not file_id:
        return ReviewRow(person["email"], person["name"], "not-started", 0, 0, {}, None, None)
    results, judged, total = results_for(db, file_id)
    pending = any(r.pending for r in results.values())
    status = "done" if not pending else ("in-progress" if judged else "not-started")
    return ReviewRow(person["email"], person["name"], status, judged, total, results, person_level(results), file_id)


def reviews(db: sqlite3.Connection, period: str | None) -> list[ReviewerGroup]:
    files = {r["email"]: r["file_id"] for r in db.execute("SELECT email, file_id FROM reviews WHERE period = ?", (period,))}
    people = db.execute("SELECT * FROM people ORDER BY rowid").fetchall()
    by_email = {p["email"]: p for p in people}
    groups: dict[str | None, list[ReviewRow]] = {}
    for p in people:
        groups.setdefault(p["evaluator"], []).append(_row(db, p, files.get(p["email"])))
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
    row = _row(db, person, r["file_id"] if r else None)
    cells: dict[tuple[int, str], list] = {}
    if r:
        verdicts = {v["item"]: v for v in db.execute("SELECT * FROM verdicts WHERE file_id = ?", (r["file_id"],))}
        for it in db.execute("SELECT * FROM definition_items WHERE version = ? ORDER BY key", (r["version"],)):
            if it["level"] in JUDGED_LEVELS:
                v = verdicts.get(f"{it['axis']}-L{it['level']}-{it['key']}")
                cells.setdefault((it["level"], it["axis"]), []).append((it, v))
    return {"person": person, "review": r, "row": row, "cells": cells}
