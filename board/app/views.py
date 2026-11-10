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
