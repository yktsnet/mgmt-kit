"""Claude Code の利用状況の図と表を、usage の render.py の関数で作る。

MD（usage/tools/usage/claude-code/README.md）と同じ関数を呼ぶので、集計の決まりは render.py にだけある。
board は並べ方だけを持つ。
"""

import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def _render(usage_dir: Path):
    path = usage_dir / "render.py"
    if not path.is_file():
        return None
    # render.py は親のディレクトリの chart.py を import する
    sys.path.insert(0, str(usage_dir.parent))
    spec = importlib.util.spec_from_file_location("usage_render", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _days(usage_dir: Path) -> list[dict]:
    out = []
    for p in sorted((usage_dir / "data").glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def team(usage_dir: Path) -> dict | None:
    """全員の図と、量と成果・使い方の表の行。トークン量の多い順に並べる（MD と同じ）。"""
    r = _render(usage_dir)
    days = _days(usage_dir)
    if not r or not days:
        return None
    by_date, span, _ = r.period(days)
    if not span:
        return None
    accounts = json.loads((usage_dir / "github.json").read_text()) if (usage_dir / "github.json").is_file() else {}
    members = sorted({m for d in span if d in by_date for m in by_date[d]["members"]})
    rows = []
    for m in members:
        u = r.usage(span, by_date, m)
        issues = r.issue_counts(span, by_date, accounts.get(r.name(m)))
        top = sorted((u["skills"] or {}).items(), key=lambda kv: (-kv[1], kv[0]))[: r.TOP_SKILLS]
        sub, whole = u["subagent"]
        rows.append({
            "email": m,
            "name": r.name(m),
            "tokens": u["tokens"],
            "minutes": r.minutes(u["active_seconds"]),
            "tokens_label": r.compact(u["tokens"]),
            "commits": u["commits"],
            "pull_requests": u["pull_requests"],
            "lines_added": u["lines_added"],
            "lines_removed": u["lines_removed"],
            "issues": issues,
            "skills": r.skill_total(u),
            "top_skills": top,
            "subagent": r.ratio(sub, whole),
            "efforts": r.kinds(u["efforts"]),
            "families": r.kinds(u["families"]),
            "per_session": r.compact(u["tokens"] / u["sessions"]) if u["sessions"] else "-",
        })
    rows.sort(key=lambda x: -x["tokens"])
    return {
        "since": span[0].isoformat(),
        "until": span[-1].isoformat(),
        "tokens_chart": r.team_chart(span, by_date, members, "tokens", r.compact),
        "commits_chart": r.team_chart(span, by_date, members, "commits", lambda v: f"{v:g}"),
        "rows": rows,
    }


def member(usage_dir: Path, email: str) -> dict | None:
    """1人の毎日の推移の図と、日ごとの行。"""
    r = _render(usage_dir)
    days = _days(usage_dir)
    if not r or not days:
        return None
    by_date, span, _ = r.period(days)
    if not any(email in by_date.get(d, {}).get("members", {}) for d in span):
        return None
    daily = []
    for d in reversed(span):
        v = by_date.get(d, {}).get("members", {}).get(email, {})
        daily.append({
            "label": r.label_of(d),
            "tokens": r.compact(v.get("tokens", 0)),
            "minutes": r.minutes(v.get("active_seconds", 0)),
            "sessions": v.get("sessions", 0),
            "commits": v.get("commits", 0),
            "pull_requests": v.get("pull_requests", 0),
            "skills": sum((v.get("skills") or {}).values()),
        })
    return {"since": span[0].isoformat(), "until": span[-1].isoformat(), "chart": r.member_chart(span, by_date, email), "daily": daily}
