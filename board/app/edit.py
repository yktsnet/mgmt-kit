"""設定の画面で直した値を、元のシートへ書き戻す。

書き戻す前に、画面が読んだあとでシートが直されていないかを更新日時で確かめる。直されていたら書かない。
シート1枚をまるごと書き直すので、board が読まない列や行は消える。
"""

import sqlite3

from .definition import DEFINITION_HEADER, Item, parse_definition
from .parse import AXES, SheetError, parse_requisitions
from .people import PEOPLE_HEADER, parse_people
from .sources import FileRef, Source
from .sync import DEFINITION, PEOPLE, REQUISITIONS

REQ_HEADER = ["枠", "人数", "参照ペルソナ", *AXES]


class Conflict(Exception):
    pass


def _ref(source: Source, db: sqlite3.Connection, path: str) -> FileRef:
    ref = next((r for r in source.list() if r.path == path), None)
    if not ref:
        raise SheetError(f"{path} not found")
    known = db.execute("SELECT modified FROM files WHERE id = ?", (ref.id,)).fetchone()
    if not known or known["modified"] != ref.modified:
        raise Conflict(f"{path} was changed after the screen read it")
    return ref


# ---- 定義


def _items(db: sqlite3.Connection, version: int) -> list[Item]:
    rows = db.execute(
        "SELECT * FROM definition_items WHERE version = ? ORDER BY axis, level, key", (version,)
    ).fetchall()
    return [Item(r["axis"], r["level"], r["key"], r["text"], r["evidence"]) for r in rows]


def _write_version(source: Source, ref: FileRef, version: int, items: list[Item]) -> None:
    rows = [DEFINITION_HEADER] + [[x.axis, f"L{x.level}", x.key, x.text, x.evidence] for x in items]
    # 書く前に、読むときと同じ決まりで確かめる
    parse_definition({f"v{version}": rows})
    source.write(ref, f"v{version}", rows)


def save_item(source: Source, db: sqlite3.Connection, version: int, axis: str, level: int, key: str | None, text: str, evidence: str) -> None:
    """細目を直す。key が無ければ、そのマスの次の文字で足す。"""
    ref = _ref(source, db, DEFINITION)
    items = _items(db, version)
    text = text.strip()
    if not text:
        raise SheetError("判定文 is empty")
    if key is None:
        used = {x.key for x in items if x.axis == axis and x.level == level}
        key = next(c for c in "abcdefghijklmnopqrstuvwxyz" if c not in used)
        items.append(Item(axis, level, key, text, evidence.strip()))
    else:
        items = [Item(x.axis, x.level, x.key, text, evidence.strip()) if (x.axis, x.level, x.key) == (axis, level, key) else x for x in items]
    _write_version(source, ref, version, items)


def delete_item(source: Source, db: sqlite3.Connection, version: int, axis: str, level: int, key: str) -> None:
    ref = _ref(source, db, DEFINITION)
    items = [x for x in _items(db, version) if (x.axis, x.level, x.key) != (axis, level, key)]
    _write_version(source, ref, version, items)


def new_version(source: Source, db: sqlite3.Connection) -> int:
    """最新の版を複製して、次の版を作る。"""
    ref = _ref(source, db, DEFINITION)
    latest = db.execute("SELECT max(version) FROM definition_items").fetchone()[0]
    if latest is None:
        raise SheetError("no definition to copy")
    _write_version(source, ref, latest + 1, _items(db, latest))
    return latest + 1


# ---- 担当


def set_evaluator(source: Source, db: sqlite3.Connection, email: str, evaluator: str) -> None:
    ref = _ref(source, db, PEOPLE)
    people = db.execute("SELECT * FROM people ORDER BY rowid").fetchall()
    if not any(p["email"] == email for p in people):
        raise SheetError(f"{email} is not in 在籍者")
    rows = [PEOPLE_HEADER] + [
        [p["email"], p["name"], (evaluator if p["email"] == email else p["evaluator"]) or None] for p in people
    ]
    parse_people({"在籍者": rows})
    source.write(ref, "在籍者", rows)


# ---- 採用の枠


def set_requisition(source: Source, db: sqlite3.Connection, name: str, count: int, target: dict[str, int | None]) -> None:
    ref = _ref(source, db, REQUISITIONS)
    rows = [REQ_HEADER]
    found = False
    for r in db.execute("SELECT * FROM requisitions ORDER BY rowid").fetchall():
        t = dict(db.execute("SELECT axis, value FROM requisition_targets WHERE name = ?", (r["name"],)).fetchall())
        if r["name"] == name:
            found = True
            rows.append([name, count, r["persona"], *[target.get(a) for a in AXES]])
        else:
            rows.append([r["name"], r["count"], r["persona"], *[t.get(a) for a in AXES]])
    if not found:
        raise SheetError(f"枠 {name!r} not found")
    parse_requisitions({"求める人材": rows})
    source.write(ref, "求める人材", rows)
