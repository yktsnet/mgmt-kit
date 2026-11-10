"""読み込み口が返したシートを、見出しの文字で読んで候補者にする。

候補者のシートの形の正本は docs/sheets.md にある。parse_requisitions は、設定の採用枠を直すときの確かめに使う。
"""

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from .sources import Book

AXES = ("A", "B", "C", "D", "E")
STAGES = ("応募", "書類選考", "一次面接", "最終面接", "内定", "入社", "不採用", "辞退")
SHEETS_EPOCH = dt.date(1899, 12, 30)


class SheetError(ValueError):
    pass


@dataclass
class Interview:
    date: dt.date | None
    interviewer: str
    scores: dict[str, int]
    note: str


@dataclass
class Candidate:
    email: str
    name: str
    requisition: str
    stage: str
    applied: dt.date | None
    source: str
    interviews: list[Interview] = field(default_factory=list)

    def scores(self) -> dict[str, int]:
        """軸ごとに、点の入っている最も新しい面接の値。点の無い軸は入れない（未観測）。"""
        out: dict[str, int] = {}
        for iv in sorted(self.interviews, key=lambda i: i.date or dt.date.min):
            out.update(iv.scores)
        return out


@dataclass
class Requisition:
    name: str
    count: int
    persona: str
    target: dict[str, int]


def to_date(v: Any) -> dt.date | None:
    if v is None or v == "":
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, dict) and "serial_date" in v:
        return SHEETS_EPOCH + dt.timedelta(days=int(v["serial_date"]))
    try:
        return dt.date.fromisoformat(str(v).strip().replace("/", "-"))
    except ValueError as e:
        raise SheetError(f"not a date: {v!r}") from e


def to_score(v: Any, where: str) -> int | None:
    if v is None or v == "":
        return None
    try:
        f = float(str(v).strip())
    except ValueError as e:
        raise SheetError(f"{where}: score must be 1-5, got {v!r}") from e
    if not f.is_integer() or not 1 <= f <= 5:
        raise SheetError(f"{where}: score must be 1-5, got {v!r}")
    return int(f)


def _text(v: Any) -> str:
    return "" if v is None else str(v).strip()


def _sheet(book: Book, name: str) -> list[list[Any]]:
    if name not in book:
        raise SheetError(f"missing sheet: {name}")
    return book[name]


def _table(rows: list[list[Any]]) -> list[dict[str, Any]]:
    """1行目を見出しとして、残りの行を見出し → 値の辞書にする。空の行は飛ばす。"""
    if not rows:
        return []
    header = [_text(h) for h in rows[0]]
    out = []
    for row in rows[1:]:
        if all(_text(v) == "" for v in row):
            continue
        out.append({h: (row[i] if i < len(row) else None) for i, h in enumerate(header) if h})
    return out


def parse_candidate(book: Book) -> Candidate:
    profile = {}
    for row in _sheet(book, "候補者"):
        if row and _text(row[0]):
            profile[_text(row[0])] = row[1] if len(row) > 1 else None
    email = _text(profile.get("メール")).lower()
    if not email:
        raise SheetError("候補者: メール is empty")
    stage = _text(profile.get("段階"))
    if stage and stage not in STAGES:
        raise SheetError(f"候補者: unknown 段階 {stage!r}")

    interviews = []
    for i, r in enumerate(_table(book.get("面接", [])), start=2):
        scores = {a: s for a in AXES if (s := to_score(r.get(a), f"面接 row {i} {a}")) is not None}
        interviews.append(Interview(to_date(r.get("日付")), _text(r.get("面接官")).lower(), scores, _text(r.get("所見"))))

    return Candidate(
        email=email,
        name=_text(profile.get("氏名")) or email,
        requisition=_text(profile.get("応募枠")),
        stage=stage,
        applied=to_date(profile.get("応募日")),
        source=_text(profile.get("経路")),
        interviews=interviews,
    )


def parse_requisitions(book: Book) -> list[Requisition]:
    out = []
    for i, r in enumerate(_table(_sheet(book, "求める人材")), start=2):
        name = _text(r.get("枠"))
        if not name:
            continue
        if any(x.name == name for x in out):
            raise SheetError(f"求める人材 row {i}: duplicate 枠 {name!r}")
        target = {a: s for a in AXES if (s := to_score(r.get(a), f"求める人材 row {i} {a}")) is not None}
        count = r.get("人数")
        out.append(Requisition(name, int(count) if count not in (None, "") else 0, _text(r.get("参照ペルソナ")), target))
    return out
