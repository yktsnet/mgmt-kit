"""評価のシートを読み、細目ごとの判定から軸の段階と本人の段階を出す。

形の正本は docs/sheets.md の「評価」、段階の決め方は ladder/docs/ladder.md にある。
"""

import sqlite3
from dataclasses import dataclass, field

from .definition import Item
from .parse import AXES, SheetError, _sheet, _table, _text
from .sources import Book

PASS, FAIL, UNOBSERVED = "○", "×", "未観測"
VERDICTS = (PASS, FAIL, UNOBSERVED)
# 手で打つときの書き方の揺れを受ける
ALIASES = {"o": PASS, "○": PASS, "〇": PASS, "x": FAIL, "×": FAIL, "✕": FAIL, "未観測": UNOBSERVED, "-": UNOBSERVED}
REVIEW_HEADER = ["軸", "段階", "細目", "判定文", "判定", "根拠"]
# L1 は下限で、できない状態を書いてあるので判定しない
JUDGED_LEVELS = (2, 3, 4, 5)


@dataclass
class Review:
    email: str
    period: str
    version: int
    reviewer: str
    # "A-L3-a" → (判定, 根拠)。判定の空欄は入れない
    verdicts: dict[str, tuple[str, str]] = field(default_factory=dict)


def parse_review(book: Book) -> Review:
    meta = {}
    for row in _sheet(book, "対象"):
        if row and _text(row[0]):
            meta[_text(row[0])] = row[1] if len(row) > 1 else None
    email = _text(meta.get("メール")).lower()
    if not email:
        raise SheetError("対象: メール is empty")
    version_text = _text(meta.get("版")).lower().removeprefix("v")
    if not version_text.isdigit():
        raise SheetError(f"対象: 版 must be v1, v2, ..., got {meta.get('版')!r}")
    review = Review(email, _text(meta.get("期")), int(version_text), _text(meta.get("Reviewer")).lower())

    for i, r in enumerate(_table(_sheet(book, "評価")), start=2):
        raw = _text(r.get("判定"))
        if not raw:
            continue
        verdict = ALIASES.get(raw.lower())
        if not verdict:
            raise SheetError(f"評価 row {i}: 判定 must be ○, × or 未観測, got {raw!r}")
        item_id = f"{_text(r.get('軸')).upper()}-L{_text(r.get('段階')).upper().removeprefix('L')}-{_text(r.get('細目')).lower()}"
        review.verdicts[item_id] = (verdict, _text(r.get("根拠")))
    return review


@dataclass
class AxisResult:
    # 段階。未観測なら None
    level: int | None
    # 判定の空欄が残っていて、段階がまだ決まらない
    pending: bool


def axis_result(items: list[Item], verdicts: dict[str, str], axis: str) -> AxisResult:
    """L2 から順に、マスの細目がすべて ○ なら上がる。× があれば手前で止まる。

    × と空欄が同じマスにあれば、× で止まる（上のマスは判定しなくても段階が決まる）。
    L2 に未観測があれば、その軸は未観測とする。
    """
    level = 1
    for lv in JUDGED_LEVELS:
        cell = [verdicts.get(x.id) for x in items if x.axis == axis and x.level == lv]
        if not cell:
            continue
        if FAIL in cell:
            return AxisResult(level, False)
        if None in cell:
            return AxisResult(None, True)
        if UNOBSERVED in cell:
            return AxisResult(None if lv == 2 else level, False)
        level = lv
    return AxisResult(level, False)


def person_level(results: dict[str, AxisResult]) -> int | None:
    """本人の段階は A と B の低いほう。どちらかが未観測か途中なら決まらない。"""
    a, b = results["A"], results["B"]
    if a.pending or b.pending or a.level is None or b.level is None:
        return None
    return min(a.level, b.level)


def template_rows(items: list[Item]) -> list[list]:
    """評価のシートの「評価」の中身。判定するのは L2〜L5 の細目だけ。"""
    rows = [REVIEW_HEADER]
    for x in sorted(items, key=lambda x: (x.axis, x.level, x.key)):
        if x.level in JUDGED_LEVELS:
            rows.append([x.axis, f"L{x.level}", x.key, x.text, None, None])
    return rows


def store_review(db: sqlite3.Connection, file_id: str, review: Review) -> None:
    db.execute("DELETE FROM reviews WHERE file_id = ?", (file_id,))
    db.execute(
        "INSERT INTO reviews (file_id, email, period, version, reviewer) VALUES (?, ?, ?, ?, ?)",
        (file_id, review.email, review.period, review.version, review.reviewer or None),
    )
    db.executemany(
        "INSERT INTO verdicts (file_id, item, verdict, note) VALUES (?, ?, ?, ?)",
        [(file_id, item, v, note) for item, (v, note) in review.verdicts.items()],
    )


def results_for(db: sqlite3.Connection, file_id: str) -> tuple[dict[str, AxisResult], int, int]:
    """評価1件の、軸ごとの結果と、判定した細目の数と、判定する細目の数。"""
    r = db.execute("SELECT version FROM reviews WHERE file_id = ?", (file_id,)).fetchone()
    rows = db.execute("SELECT * FROM definition_items WHERE version = ?", (r["version"],)).fetchall()
    if not rows:
        raise SheetError(f"definition v{r['version']} not found")
    items = [Item(x["axis"], x["level"], x["key"], x["text"], x["evidence"]) for x in rows]
    verdicts = dict(db.execute("SELECT item, verdict FROM verdicts WHERE file_id = ?", (file_id,)).fetchall())
    judged_ids = {x.id for x in items if x.level in JUDGED_LEVELS}
    return {a: axis_result(items, verdicts, a) for a in AXES}, len(judged_ids & verdicts.keys()), len(judged_ids)
