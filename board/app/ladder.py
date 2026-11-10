"""ladder の採点結果と参照ペルソナを読み、在籍者の5軸と段階を SQLite に置く。

採点結果の書式の正本は ladder/.claude/skills/ladder-score/reference/scoresheet-template.md、
参照ペルソナは ladder/docs/personas.md にある。
"""

import datetime as dt
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .parse import AXES, SheetError

LEVEL = re.compile(r"L([1-5])")


@dataclass
class Scoresheet:
    subject: str
    period: str
    level: int | None
    scores: dict[str, int] = field(default_factory=dict)


def _table_after(lines: list[str], start: int) -> tuple[list[str], list[str]]:
    """start 以降で最初に出る Markdown の表の、見出しの行と1行目の値を返す。"""
    rows = []
    for line in lines[start:]:
        s = line.strip()
        if s.startswith("|"):
            rows.append([c.strip() for c in s.strip("|").split("|")])
        elif rows:
            break
        elif s.startswith("#"):
            break
    if len(rows) < 3:
        raise SheetError("score table not found")
    return rows[0], rows[2]


def _axis_values(header: list[str], values: list[str]) -> dict[str, int]:
    out = {}
    for h, v in zip(header, values):
        axis = h.split()[0] if h else ""
        if axis not in AXES:
            continue
        m = LEVEL.search(v) or re.fullmatch(r"([1-5])", v)
        # 「未観測」など点の無い軸は入れない
        if m:
            out[axis] = int(m.group(1))
    return out


def parse_scoresheet(text: str) -> Scoresheet:
    lines = text.splitlines()
    title = next((l for l in lines if l.startswith("# ")), "")
    m = re.match(r"#\s*採点\s*[—-]\s*(.+?)\s*/\s*(.+)$", title)
    if not m:
        raise SheetError("title must be '# 採点 — <対象> / <期間>'")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## 点")
    except StopIteration as e:
        raise SheetError("missing section: ## 点") from e
    header, values = _table_after(lines, start + 1)
    level = None
    for i, l in enumerate(lines):
        if l.strip() == "## 段階":
            lv = next((LEVEL.search(x) for x in lines[i + 1 :] if x.strip()), None)
            level = int(lv.group(1)) if lv else None
            break
    return Scoresheet(m.group(1), m.group(2), level, _axis_values(header, values))


def parse_personas(text: str) -> dict[int, dict[str, int]]:
    lines = text.splitlines()
    out = {}
    for i, l in enumerate(lines):
        m = re.fullmatch(r"##\s*L([1-5])", l.strip())
        if m:
            header, values = _table_after(lines, i + 1)
            out[int(m.group(1))] = _axis_values(header, values)
    return out


def _mtime(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()


def sync_ladder(scores_dir: Path, personas: Path | None, domain: str, db: sqlite3.Connection) -> dict[str, str]:
    """変わった採点結果だけを読み直す。返り値は読めなかったファイルと誤り。"""
    errors: dict[str, str] = {}
    known = {r["id"]: r["modified"] for r in db.execute("SELECT id, modified FROM files WHERE kind IN ('scoresheet', 'personas')")}
    paths = sorted(scores_dir.glob("*.md")) if scores_dir.is_dir() else []
    seen = {str(p) for p in paths} | ({str(personas)} if personas and personas.is_file() else set())

    with db:
        for gone in known.keys() - seen:
            db.execute("DELETE FROM files WHERE id = ?", (gone,))
        db.execute("DELETE FROM staff WHERE file_id NOT IN (SELECT id FROM files)")

        if personas and personas.is_file() and known.get(str(personas)) != _mtime(personas):
            _file(db, personas, "personas", None)
            db.execute("DELETE FROM personas")
            for level, scores in parse_personas(personas.read_text(encoding="utf-8")).items():
                db.executemany("INSERT INTO personas (level, axis, value) VALUES (?, ?, ?)", [(level, a, v) for a, v in scores.items()])

        for p in paths:
            if known.get(str(p)) == _mtime(p):
                continue
            name = p.stem
            email = f"{name}@{domain}".lower()
            db.execute("DELETE FROM staff WHERE file_id = ?", (str(p),))
            try:
                sheet = parse_scoresheet(p.read_text(encoding="utf-8"))
            except SheetError as e:
                _file(db, p, "scoresheet", str(e))
                errors[p.name] = str(e)
                continue
            _file(db, p, "scoresheet", None)
            db.execute("DELETE FROM scores WHERE email = ? AND origin = 'ladder'", (email,))
            db.execute(
                "INSERT INTO staff (email, file_id, name, period, level) VALUES (?, ?, ?, ?, ?)",
                (email, str(p), name, sheet.period, sheet.level),
            )
            db.executemany(
                "INSERT INTO scores (email, origin, axis, value) VALUES (?, 'ladder', ?, ?)",
                [(email, a, v) for a, v in sheet.scores.items()],
            )
        db.execute("DELETE FROM scores WHERE origin = 'ladder' AND email NOT IN (SELECT email FROM staff)")
    return errors


def _file(db: sqlite3.Connection, p: Path, kind: str, error: str | None) -> None:
    db.execute(
        "INSERT INTO files (id, path, modified, kind, error) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET modified = excluded.modified, error = excluded.error",
        (str(p), p.name, _mtime(p), kind, error),
    )
