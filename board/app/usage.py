"""usage の日ごとの JSON を読み、在籍者ごとに直近の投入の量と作業の量を合計する。

Actions が作る MD は人が読むための表なので読まない。JSON の書式の正本は
usage/tools/usage/claude-code/collect.py にある。
"""

import datetime as dt
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

# usage が seat を決めるときと同じ幅にする
WINDOW_DAYS = 14
FIELDS = ("cost_usd", "active_seconds", "sessions", "commits", "pull_requests", "lines_added")


def _signature(files: list[Path]) -> str:
    return f"{len(files)}:{max((p.stat().st_mtime for p in files), default=0)}"


def summarize(data_dir: Path, github: dict[str, str] | None = None) -> tuple[str, str, dict[str, dict]]:
    """データの最後の日から WINDOW_DAYS 日を合計する。今日からではなく最後の日から数える。"""
    days = []
    for p in sorted(data_dir.glob("*.json")):
        try:
            days.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    if not days:
        return "", "", {}
    until = max(dt.date.fromisoformat(d["date"]) for d in days)
    since = until - dt.timedelta(days=WINDOW_DAYS - 1)
    login_of = {v: k for k, v in (github or {}).items()}

    out: dict[str, dict] = defaultdict(lambda: {f: 0 for f in (*FIELDS, "active_days", "skills", "issues_opened")})
    for d in days:
        if not since <= dt.date.fromisoformat(d["date"]) <= until:
            continue
        for email, m in d.get("members", {}).items():
            row = out[email.lower()]
            for f in FIELDS:
                row[f] += m.get(f, 0) or 0
            row["active_days"] += 1 if m.get("sessions") else 0
            row["skills"] += sum((m.get("skills") or {}).values())
        for login, counts in (d.get("issues") or {}).items():
            name = login_of.get(login)
            if not name:
                continue
            # issues は GitHub のアカウントで数えてあるので、名簿から名前に戻し、members のメールに合わせる
            email = next((e for e in out if e.split("@")[0] == name), None)
            if email:
                out[email]["issues_opened"] += counts.get("opened", 0)
    return since.isoformat(), until.isoformat(), dict(out)


def sync_usage(usage_dir: Path, db: sqlite3.Connection) -> bool:
    """データが変わっていれば集計し直す。読み直したら True。"""
    data_dir = usage_dir / "data"
    files = sorted(data_dir.glob("*.json")) if data_dir.is_dir() else []
    sig = _signature(files)
    key = f"usage:{usage_dir}"
    row = db.execute("SELECT modified FROM files WHERE id = ?", (key,)).fetchone()
    if row and row["modified"] == sig:
        return False
    gh = usage_dir / "github.json"
    github = json.loads(gh.read_text(encoding="utf-8")) if gh.is_file() else {}
    since, until, rows = summarize(data_dir, github)
    with db:
        db.execute(
            "INSERT INTO files (id, path, modified, kind, error) VALUES (?, ?, ?, 'usage', NULL) "
            "ON CONFLICT(id) DO UPDATE SET modified = excluded.modified",
            (key, str(usage_dir), sig),
        )
        db.execute("DELETE FROM usage")
        db.executemany(
            "INSERT INTO usage (email, since, until, active_days, cost_usd, active_seconds, sessions, commits, "
            "pull_requests, lines_added, skills, issues_opened) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (e, since, until, r["active_days"], round(r["cost_usd"], 2), r["active_seconds"], r["sessions"],
                 r["commits"], r["pull_requests"], r["lines_added"], r["skills"], r["issues_opened"])
                for e, r in rows.items()
            ],
        )
    return True
