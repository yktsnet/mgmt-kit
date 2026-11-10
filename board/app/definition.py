"""設定の「定義」のシートを読む。5軸×5段階の各マスを細目に分け、版ごとに持つ。

形の正本は docs/sheets.md の「定義」にある。
"""

import re
import sqlite3
from dataclasses import dataclass

from .parse import AXES, SheetError, _table, _text
from .sources import Book

LEVELS = (1, 2, 3, 4, 5)
VERSION = re.compile(r"v(\d+)")


@dataclass(frozen=True)
class Item:
    axis: str
    level: int
    key: str
    text: str
    evidence: str

    @property
    def id(self) -> str:
        return f"{self.axis}-L{self.level}-{self.key}"


def parse_definition(book: Book) -> dict[int, list[Item]]:
    """版のシート（v1, v2, …）ごとに細目を返す。名前が vN でないシートは読まない。"""
    out = {}
    for title, rows in book.items():
        m = VERSION.fullmatch(title.strip())
        if not m:
            continue
        out[int(m.group(1))] = _version(title, rows)
    if not out:
        raise SheetError("定義: no version sheet (v1, v2, ...)")
    return out


def _version(title: str, rows: list) -> list[Item]:
    items, seen = [], set()
    for i, r in enumerate(_table(rows), start=2):
        axis = _text(r.get("軸")).upper()
        level_text = _text(r.get("段階")).upper().removeprefix("L")
        key = _text(r.get("細目")).lower()
        text = _text(r.get("判定文"))
        if not text:
            continue
        where = f"定義 {title} row {i}"
        if axis not in AXES:
            raise SheetError(f"{where}: 軸 must be A-E, got {axis!r}")
        if not level_text.isdigit() or int(level_text) not in LEVELS:
            raise SheetError(f"{where}: 段階 must be L1-L5, got {r.get('段階')!r}")
        if not re.fullmatch(r"[a-z]", key):
            raise SheetError(f"{where}: 細目 must be one letter a-z, got {key!r}")
        item = Item(axis, int(level_text), key, text, _text(r.get("読むもの")))
        if item.id in seen:
            raise SheetError(f"{where}: duplicate {item.id}")
        seen.add(item.id)
        items.append(item)
    missing = [f"{a}-L{lv}" for a in AXES for lv in LEVELS if not any(x.axis == a and x.level == lv for x in items)]
    if missing:
        raise SheetError(f"定義 {title}: cells without 細目: {', '.join(missing)}")
    return items


def store_definition(db: sqlite3.Connection, file_id: str, versions: dict[int, list[Item]]) -> None:
    db.execute("DELETE FROM definition_items")
    db.executemany(
        "INSERT INTO definition_items (version, axis, level, key, text, evidence, file_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(v, x.axis, x.level, x.key, x.text, x.evidence, file_id) for v, items in versions.items() for x in items],
    )


def latest_version(db: sqlite3.Connection) -> int | None:
    return db.execute("SELECT max(version) FROM definition_items").fetchone()[0]


# ---- ladder.md から初版を作る


def split_statement(text: str) -> list[str]:
    """判定文を句点ごとに細目へ分ける。初版を作るときだけ使い、分け方はあとで人が設定で直す。"""
    return [s.strip() + "。" for s in text.split("。") if s.strip()]


def from_ladder_md(text: str) -> list[Item]:
    items = []
    axis = None
    for line in text.splitlines():
        m = re.match(r"##\s+([A-E])\s", line)
        if m:
            axis = m.group(1)
            continue
        if line.startswith("## "):
            axis = None
            continue
        m = re.match(r"\|\s*L([1-5])\s*\|(.+?)\|(.+?)\|\s*$", line)
        if axis and m:
            level, statement, evidence = int(m.group(1)), m.group(2).strip(), m.group(3).strip()
            for i, part in enumerate(split_statement(statement)):
                items.append(Item(axis, level, "abcdefghijklmnopqrstuvwxyz"[i], part, evidence))
    return items
