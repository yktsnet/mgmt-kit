"""設定（Ladder の定義と版、在籍者と Reviewer と役割と採用を見られるか、採用枠）を直す。設定はアプリが持ち、Drive には置かない。

直す前に、読むときと同じ決まりで確かめる。決まりに合わなければ SheetError を出す。
"""

import sqlite3
from pathlib import Path

from .definition import DEFINITION_HEADER, Item, from_ladder_md, parse_definition
from .parse import AXES, SheetError, parse_requisitions
from .people import PEOPLE_HEADER, parse_people

ROLES = ("member", "manager")
REQ_HEADER = ["枠", "人数", "参照ペルソナ", *AXES]


# ---- 定義


def _items(db: sqlite3.Connection, version: int) -> list[Item]:
    rows = db.execute("SELECT * FROM definition_items WHERE version = ? ORDER BY axis, level, key", (version,)).fetchall()
    return [Item(r["axis"], r["level"], r["key"], r["text"], r["evidence"]) for r in rows]


def _check_unused(db: sqlite3.Connection, version: int) -> None:
    # 評価や面接が使った版を直すと、その判定の前提があとから変わる
    if version_in_use(db, version):
        raise SheetError(f"v{version} は評価か面接に使われているので直せない。New version を作ってから直す")


def _replace_version(db: sqlite3.Connection, version: int, items: list[Item]) -> None:
    rows = [DEFINITION_HEADER] + [[x.axis, f"L{x.level}", x.key, x.text, x.evidence] for x in items]
    parse_definition({f"v{version}": rows})
    with db:
        db.execute("DELETE FROM definition_items WHERE version = ?", (version,))
        db.executemany(
            "INSERT INTO definition_items (version, axis, level, key, text, evidence) VALUES (?, ?, ?, ?, ?, ?)",
            [(version, x.axis, x.level, x.key, x.text, x.evidence) for x in items],
        )


def save_item(db: sqlite3.Connection, version: int, axis: str, level: int, key: str | None, text: str, evidence: str) -> None:
    """細目を直す。key が無ければ、そのマスの次の文字で足す。"""
    _check_unused(db, version)
    text = text.strip()
    if not text:
        raise SheetError("判定文が空になっている")
    items = _items(db, version)
    if key is None:
        used = {x.key for x in items if x.axis == axis and x.level == level}
        key = next(c for c in "abcdefghijklmnopqrstuvwxyz" if c not in used)
        items.append(Item(axis, level, key, text, evidence.strip()))
    else:
        items = [Item(x.axis, x.level, x.key, text, evidence.strip()) if (x.axis, x.level, x.key) == (axis, level, key) else x for x in items]
    _replace_version(db, version, items)


def delete_item(db: sqlite3.Connection, version: int, axis: str, level: int, key: str) -> None:
    _check_unused(db, version)
    _replace_version(db, version, [x for x in _items(db, version) if (x.axis, x.level, x.key) != (axis, level, key)])


def new_version(db: sqlite3.Connection) -> int:
    """最新の版を複製して、次の版を作る。"""
    latest = db.execute("SELECT max(version) FROM definition_items").fetchone()[0]
    if latest is None:
        raise SheetError("複製する定義が無い")
    _replace_version(db, latest + 1, _items(db, latest))
    return latest + 1


def version_in_use(db: sqlite3.Connection, version: int) -> bool:
    return db.execute(
        "SELECT 1 FROM reviews WHERE version = ? UNION ALL SELECT 1 FROM candidates WHERE version = ? LIMIT 1", (version, version)
    ).fetchone() is not None


# ---- 在籍者


def _people_rows(db: sqlite3.Connection) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM people ORDER BY rowid").fetchall()


def set_person(db: sqlite3.Connection, email: str, evaluator: str | None = None, role: str | None = None, hiring: bool | None = None) -> None:
    people = _people_rows(db)
    if not any(p["email"] == email for p in people):
        raise SheetError(f"{email} は在籍者にいない")
    if role is not None and role not in ROLES:
        raise SheetError(f"役割は {', '.join(ROLES)} のどれか")
    new_evaluator = {p["email"]: p["evaluator"] or "" for p in people}
    if evaluator is not None:
        new_evaluator[email] = evaluator
    parse_people({"在籍者": [PEOPLE_HEADER] + [[p["email"], p["name"], new_evaluator[p["email"]]] for p in people]})
    with db:
        if evaluator is not None:
            db.execute("UPDATE people SET evaluator = ? WHERE email = ?", (evaluator or None, email))
        if role is not None:
            db.execute("UPDATE people SET role = ? WHERE email = ?", (role, email))
        if hiring is not None:
            db.execute("UPDATE people SET hiring = ? WHERE email = ?", (int(hiring), email))


# ---- 採用枠


def set_requisition(db: sqlite3.Connection, name: str, count: int, target: dict[str, int | None]) -> None:
    r = db.execute("SELECT * FROM requisitions WHERE name = ?", (name,)).fetchone()
    if not r:
        raise SheetError(f"採用枠 {name!r} が無い")
    (req,) = parse_requisitions({"求める人材": [REQ_HEADER, [name, count, r["persona"], *[target.get(a) for a in AXES]]]})
    with db:
        db.execute("UPDATE requisitions SET count = ? WHERE name = ?", (req.count, name))
        db.execute("DELETE FROM requisition_targets WHERE name = ?", (name,))
        db.executemany("INSERT INTO requisition_targets (name, axis, value) VALUES (?, ?, ?)", [(name, a, v) for a, v in req.target.items()])


# ---- 最初の中身


def seed(db: sqlite3.Connection, ladder_md: Path, demo: bool) -> None:
    """設定が空のときだけ入れる。定義の初版は ladder.md から作り、デモでは在籍者と採用枠のダミーも入れる。"""
    with db:
        if db.execute("SELECT 1 FROM definition_items LIMIT 1").fetchone() is None and ladder_md.is_file():
            db.executemany(
                "INSERT INTO definition_items (version, axis, level, key, text, evidence) VALUES (1, ?, ?, ?, ?, ?)",
                [(x.axis, x.level, x.key, x.text, x.evidence) for x in from_ladder_md(ladder_md.read_text(encoding="utf-8"))],
            )
        if not demo:
            return
        from . import demo as d

        if db.execute("SELECT 1 FROM people LIMIT 1").fetchone() is None:
            db.executemany(
                "INSERT INTO people (email, name, evaluator, role, hiring) VALUES (?, ?, ?, ?, ?)",
                [(p.email, p.name, p.evaluator or None, p.role, int(p.hiring)) for p in d.people()],
            )
        if db.execute("SELECT 1 FROM requisitions LIMIT 1").fetchone() is None:
            for name, count, persona, target in d.REQUISITIONS:
                db.execute("INSERT INTO requisitions (name, count, persona) VALUES (?, ?, ?)", (name, count, persona))
                db.executemany(
                    "INSERT INTO requisition_targets (name, axis, value) VALUES (?, ?, ?)",
                    [(name, a, v) for a, v in zip(AXES, target) if v is not None],
                )
        if db.execute("SELECT 1 FROM candidate_stages LIMIT 1").fetchone() is None:
            at = "2026-04-20T09:00:00+00:00"
            by = d.email(next(iter(d.MANAGERS)))
            for name, stages in d.CANDIDATE_STAGES.items():
                for stage in stages:
                    db.execute("INSERT INTO candidate_records (email, at, by, kind, body) VALUES (?, ?, ?, 'stage', ?)", (d.email(name), at, by, stage))
                db.execute("INSERT INTO candidate_stages (email, stage, at, by) VALUES (?, ?, ?, ?)", (d.email(name), stages[-1], at, by))
