"""候補者のシートを読み、面接の細目の判定から候補者の軸の段階を出す。選考の段階と記録はアプリが持つ。

シートの形の正本は docs/sheets.md の「候補者」、段階の決め方は評価と同じ（review.py）、
候補者に当てる手順は ladder/docs/hiring.md にある。
"""

import datetime as dt
import re
import sqlite3
from dataclasses import dataclass, field

from .parse import SheetError, _sheet, _table, _text, to_date
from .review import AxisResult, parse_verdicts, parse_version, results_of
from .sources import Book
from .workflow import now

STAGES = ("応募", "書類選考", "一次面接", "最終面接", "内定", "入社", "不採用", "辞退")
FIRST = STAGES[0]
CLOSED = ("入社", "不採用", "辞退")
INTERVIEW_SHEET = re.compile(r"面接\s*(\d+)")
INTERVIEWS_HEADER = ["回", "日付", "面接官", "所見"]


@dataclass
class Interview:
    seq: int
    date: dt.date | None
    interviewer: str
    note: str
    # "A-L3-a" → (判定, 根拠)
    verdicts: dict[str, tuple[str, str]] = field(default_factory=dict)


@dataclass
class Candidate:
    email: str
    name: str
    requisition: str
    version: int
    applied: dt.date | None
    source: str
    interviews: list[Interview] = field(default_factory=list)


def parse_candidate(book: Book) -> Candidate:
    profile = {}
    for row in _sheet(book, "候補者"):
        if row and _text(row[0]):
            profile[_text(row[0])] = row[1] if len(row) > 1 else None
    email = _text(profile.get("メール")).lower()
    if not email:
        raise SheetError("候補者: メール is empty")
    try:
        version = parse_version(profile.get("版"))
    except SheetError as e:
        raise SheetError(f"候補者: {e}") from None

    interviews: dict[int, Interview] = {}
    for i, r in enumerate(_table(book.get("面接", [])), start=2):
        seq_text = _text(r.get("回"))
        if not seq_text:
            continue
        try:
            seq = int(float(seq_text))
        except ValueError:
            raise SheetError(f"面接 row {i}: 回 must be 1, 2, ..., got {seq_text!r}") from None
        if seq in interviews:
            raise SheetError(f"面接 row {i}: duplicate 回 {seq}")
        interviews[seq] = Interview(seq, to_date(r.get("日付")), _text(r.get("面接官")).lower(), _text(r.get("所見")))
    # 面接1・面接2… のシートに、評価のシートと同じ形で細目ごとの判定を書く
    for title, rows in book.items():
        m = INTERVIEW_SHEET.fullmatch(title.strip())
        if not m:
            continue
        seq = int(m.group(1))
        verdicts = parse_verdicts(rows, title.strip())
        # テンプレートの空の「面接1」は、まだ面接していないことを表す
        if verdicts or seq in interviews:
            interviews.setdefault(seq, Interview(seq, None, "", "")).verdicts = verdicts

    return Candidate(
        email=email,
        name=_text(profile.get("氏名")) or email,
        requisition=_text(profile.get("応募枠")),
        version=version,
        applied=to_date(profile.get("応募日")),
        source=_text(profile.get("経路")),
        interviews=[interviews[k] for k in sorted(interviews)],
    )


def store_candidate(db: sqlite3.Connection, file_id: str, modified: str, c: Candidate) -> None:
    newer = db.execute(
        "SELECT 1 FROM candidates JOIN files ON files.id = candidates.file_id "
        "WHERE candidates.email = ? AND files.id != ? AND files.modified > ?",
        (c.email, file_id, modified),
    ).fetchone()
    if newer:
        return
    db.execute("DELETE FROM candidates WHERE email = ?", (c.email,))
    db.execute(
        "INSERT INTO candidates (email, file_id, name, requisition, version, applied, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (c.email, file_id, c.name, c.requisition, c.version, c.applied and c.applied.isoformat(), c.source),
    )
    for iv in c.interviews:
        db.execute(
            "INSERT INTO interviews (email, seq, date, interviewer, note) VALUES (?, ?, ?, ?, ?)",
            (c.email, iv.seq, iv.date and iv.date.isoformat(), iv.interviewer, iv.note),
        )
        db.executemany(
            "INSERT INTO interview_verdicts (email, seq, item, verdict, note) VALUES (?, ?, ?, ?, ?)",
            [(c.email, iv.seq, item, v, note) for item, (v, note) in iv.verdicts.items()],
        )


def latest_verdicts(db: sqlite3.Connection, email: str) -> dict[str, sqlite3.Row]:
    """細目ごとに、判定の入っている最も新しい面接の行。面接で聞かなかった細目は前の面接の判定が残る。"""
    out = {}
    for r in db.execute("SELECT * FROM interview_verdicts WHERE email = ? ORDER BY seq", (email,)):
        out[r["item"]] = r
    return out


def results(db: sqlite3.Connection, email: str, version: int) -> tuple[dict[str, AxisResult], int, int]:
    verdicts = {k: r["verdict"] for k, r in latest_verdicts(db, email).items()}
    return results_of(db, version, verdicts)


# ---- 選考の段階と記録


def stage_of(db: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM candidate_stages WHERE email = ?", (email,)).fetchone()


def current_stage(db: sqlite3.Connection, email: str) -> str:
    row = stage_of(db, email)
    return row["stage"] if row else FIRST


def _reopen_to(db: sqlite3.Connection, email: str) -> str:
    """不採用・辞退の前にいた段階。記録が無ければ最初の段階に戻す。"""
    for r in db.execute("SELECT body FROM candidate_records WHERE email = ? AND kind = 'stage' ORDER BY at DESC, id DESC", (email,)):
        if r["body"] not in CLOSED:
            return r["body"]
    return FIRST


def moves(db: sqlite3.Connection, email: str) -> list[str]:
    """いまの段階から移れる段階。順に1つ進めるか、不採用・辞退で閉じる。閉じたものは前の段階に戻せる。"""
    stage = current_stage(db, email)
    if stage == "入社":
        return []
    if stage in CLOSED:
        return [_reopen_to(db, email)]
    i = STAGES.index(stage)
    nxt = [STAGES[i + 1]]
    # 内定のあとは、こちらから不採用にすることは無い
    return nxt + (["辞退"] if stage == "内定" else ["不採用", "辞退"])


def set_stage(db: sqlite3.Connection, me: sqlite3.Row, email: str, stage: str) -> str:
    if stage not in moves(db, email):
        raise SheetError(f"{current_stage(db, email)} から {stage} には移れない")
    at = now()
    with db:
        db.execute(
            "INSERT INTO candidate_stages (email, stage, at, by) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(email) DO UPDATE SET stage = excluded.stage, at = excluded.at, by = excluded.by",
            (email, stage, at, me["email"]),
        )
        db.execute(
            "INSERT INTO candidate_records (email, at, by, kind, body) VALUES (?, ?, ?, 'stage', ?)",
            (email, at, me["email"], stage),
        )
    return stage


def add_memo(db: sqlite3.Connection, me: sqlite3.Row, email: str, body: str) -> None:
    body = body.strip()
    if not body:
        raise SheetError("メモが空になっている")
    with db:
        db.execute(
            "INSERT INTO candidate_records (email, at, by, kind, body) VALUES (?, ?, ?, 'memo', ?)",
            (email, now(), me["email"], body),
        )


def records(db: sqlite3.Connection, email: str) -> list[sqlite3.Row]:
    return db.execute(
        "SELECT r.*, p.name AS by_name FROM candidate_records r LEFT JOIN people p ON p.email = r.by "
        "WHERE r.email = ? ORDER BY r.at DESC, r.id DESC",
        (email,),
    ).fetchall()
