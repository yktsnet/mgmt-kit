#!/usr/bin/env python3
"""data/ の日ごとの集計から、README.md の全体の節と、members/ の個人ごとのページを作り直す。"""

import datetime as dt
import json
import re
import sys
from html import escape
from pathlib import Path

# 集計のディレクトリから直接実行するので、共通の部品がある親を import の探索先に足す
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from chart import SERIES, nice_max, spread, svg  # noqa: E402

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
CHART_DIR = ROOT / "charts"
MEMBER_DIR = ROOT / "members"
README = ROOT / "README.md"
ACCOUNTS = ROOT / "github.json"
MEMBER_DAYS = 28
# 平均の線をならす幅。平日だけを並べるので、5で1週間になる
SMOOTH_DAYS = 5
# 平均を出す最少の人数。2人だと、平均と自分の値から相手の値が割り出せる
AVERAGE_MIN = 3
EFFORTS = ["low", "medium", "high", "xhigh", "max"]
MODEL_FAMILIES = ["opus", "sonnet", "haiku", "fable"]
# 起動して設定を確かめただけの日を、使った日に数えない
MIN_USED_TOKENS = 100_000
QUERY_SOURCES = {"main": "メイン", "subagent": "サブエージェント", "auxiliary": "補助"}
WEEKDAY_NAMES = "月火水木金土日"

ENTRYPOINTS = {
    "cli": "ターミナル",
    "claude-vscode": "VS Code 拡張",
    "claude-desktop": "デスクトップアプリ",
    "claude-in-slack": "Slack",
    "sdk-cli": "スクリプトからの実行",
    "sdk-ts": "Agent SDK",
    "sdk-py": "Agent SDK",
    "none": "不明",
}


def load() -> list[dict]:
    return [cli_time_only(json.loads(p.read_text())) for p in sorted(DATA_DIR.glob("*.json"))]


def cli_time_only(day: dict) -> dict:
    # collect.py が人の操作時間を除く前に取った日は、合計に含んでいるので種類別の記録から出し直す
    for v in day["members"].values():
        if "cli" in v.get("active_by_type", {}):
            v["active_seconds"] = v["active_by_type"]["cli"]
    return day


def name(email: str) -> str:
    return email.split("@")[0]


def date_of(day: dict) -> dt.date:
    return dt.date.fromisoformat(day["date"])


def label_of(date: dt.date) -> str:
    return f"{date:%m/%d}（{WEEKDAY_NAMES[date.weekday()]}）"


def compact(n: float) -> str:
    for unit, size in (("M", 1e6), ("k", 1e3)):
        if n >= size:
            return f"{n / size:.1f}".removesuffix(".0") + unit
    return f"{n:.0f}"


def minutes(seconds: float) -> str:
    return f"{seconds / 60:.0f}分"


def value(day: dict, email: str, key: str) -> float:
    return day["members"].get(email, {}).get(key, 0)


def series_class(members: list[str], email: str) -> str:
    i = members.index(email)
    # 9人目以降に色を作り足すと見分けられないので、灰色にまとめて名前で区別する
    return f"s{i}" if i < len(SERIES) else "other"


def average(days: list[dt.date], by_date: dict[dt.date, dict], members: list[str], key: str) -> list[float]:
    """日ごとの全員の平均を、直前 SMOOTH_DAYS 日の移動平均でならす。1人ずつの値は日ごとの揺れが大きく、傾きが読めない。"""
    daily = [sum(value(by_date[d], m, key) for m in members) / len(members) if d in by_date and members else 0 for d in days]
    out = []
    for i in range(len(daily)):
        window = daily[max(0, i - SMOOTH_DAYS + 1): i + 1]
        out.append(sum(window) / len(window))
    return out


def team_chart(days: list[dt.date], by_date: dict[dt.date, dict], members: list[str], key: str, fmt,
               average_of: list[str] | None = None) -> str:
    """members の線と、average_of（省略すると members）の平均の線を引く。"""
    # GitHub は画像を本文の幅まで縮めるが、広げはしない。ファイルツリーを開いた画面の本文の幅に合わせ、
    # 文字が縮まずに読める大きさで描く
    width, left, right, top, plot_h = 880, 64, 190, 24, 300
    plot_w = width - left - right
    height = top + plot_h + 44
    pool = average_of if average_of is not None else members
    avg = average(days, by_date, pool, key) if len(pool) >= AVERAGE_MIN else []
    peak = nice_max(max([*(value(by_date[d], m, key) for d in days if d in by_date for m in members), *avg], default=0))
    step = plot_w / max(len(days) - 1, 1)

    def y_of(v: float) -> float:
        return top + plot_h * (1 - v / peak)

    body = []
    for frac in (0, 0.25, 0.5, 0.75, 1):
        y = top + plot_h * (1 - frac)
        body += [
            f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}"/>',
            f'<text class="muted" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{fmt(peak * frac)}</text>',
        ]
    for i, d in enumerate(days):
        label = f"{d.month}/{d.day}" if i == 0 or d.month != days[i - 1].month else f"{d.day}"
        body.append(f'<text class="muted" x="{left + i * step:.1f}" y="{top + plot_h + 22}" text-anchor="middle">{label}</text>')
    ends = []
    for m in members:
        cls = series_class(members, m)
        pts = [(left + i * step, y_of(value(by_date[d], m, key) if d in by_date else 0)) for i, d in enumerate(days)]
        body.append(f'<polyline class="line {cls}" style="fill: none" points="'
                    + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
        body += [f'<circle class="dot {cls}" cx="{x:.1f}" cy="{y:.1f}" r="4"/>' for x, y in pts]
        ends.append((escape(name(m)), f"line {cls}", "label", pts[-1][1]))
    if avg:
        pts = [(left + i * step, y_of(v)) for i, v in enumerate(avg)]
        body.append('<polyline class="avg" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
        ends.append((f"{SMOOTH_DAYS}日平均", "avg", "avg-label", pts[-1][1]))
    label_ys = spread([y for *_, y in ends], 18, top, top + plot_h)
    for (text, line_cls, text_cls, _), ly in zip(ends, label_ys):
        x = left + plot_w + 12
        body += [
            f'<line class="{line_cls}" x1="{x}" y1="{ly:.1f}" x2="{x + 10}" y2="{ly:.1f}"/>',
            f'<text class="{text_cls}" x="{x + 16}" y="{ly + 4:.1f}">{text}</text>',
        ]
    return svg(width, height, body)


def with_minutes(day: dict) -> dict:
    # 目盛りを分の切りのよい値にするため、秒ではなく分で持つ
    members = {m: {**v, "active_minutes": v.get("active_seconds", 0) / 60} for m, v in day["members"].items()}
    return {**day, "members": members}


def member_chart(days: list[dt.date], by_date: dict[dt.date, dict], email: str) -> str:
    by_date = {d: with_minutes(day) for d, day in by_date.items()}
    panels = [
        ("トークン量", [("tokens", "s0", None)], compact),
        ("利用時間（並行した会話の分は足し合わせる）", [("active_minutes", "s0", None)], lambda v: f"{v:g}分"),
        ("commit と PR", [("commits", "s0", "commit"), ("pull_requests", "s1", "PR")], compact),
    ]
    left, plot_w, panel_h, plot_h = 56, 640, 168, 92
    width, height = left + plot_w + 24, panel_h * len(panels) + 8
    slot = plot_w / len(days)
    body = []
    for p, (title, keys, fmt) in enumerate(panels):
        y0 = p * panel_h + 28
        top = y0 + 14
        base = top + plot_h
        peak = nice_max(max((by_date[d]["members"].get(email, {}).get(k) or 0
                             for d in days if d in by_date for k, _, _ in keys), default=0))
        body.append(f'<text class="label" x="{left}" y="{y0}">{title}</text>')
        legend_x = left + plot_w
        for key, cls, label in reversed(keys):
            if label:
                legend_x -= 8 * len(label) + 30
                body += [
                    f'<rect class="{cls}" x="{legend_x}" y="{y0 - 10}" width="10" height="10" rx="2"/>',
                    f'<text class="muted" x="{legend_x + 14}" y="{y0}">{label}</text>',
                ]
        for frac in (0, 0.5, 1):
            y = base - plot_h * frac
            body += [
                f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}"/>',
                f'<text class="muted" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">{fmt(peak * frac) if frac else "0"}</text>',
            ]
        bar_w = min((slot - 4) / len(keys) - (2 if len(keys) > 1 else 0), 14)
        for i, d in enumerate(days):
            if d not in by_date:
                continue
            group_w = bar_w * len(keys) + 2 * (len(keys) - 1)
            x = left + i * slot + (slot - group_w) / 2
            for key, cls, _ in keys:
                v = by_date[d]["members"].get(email, {}).get(key) or 0
                h = plot_h * v / peak
                if h > 0:
                    h = max(h, 2)
                    r = min(2, h / 2, bar_w / 2)
                    # 値の側の端だけを丸め、基線の側は直角に保つ
                    body.append(
                        f'<path class="{cls}" d="M{x:.1f},{base} v-{h - r:.1f} q0,-{r:.1f} {r:.1f},-{r:.1f} '
                        f'h{bar_w - 2 * r:.1f} q{r:.1f},0 {r:.1f},{r:.1f} v{h - r:.1f} z"/>'
                    )
                x += bar_w + 2
        # 段ごとに日付を入れ、どのバーが何日かをその段の中で読めるようにする
        for i, d in enumerate(days):
            label = f"{d.month}/{d.day}" if i == 0 or d.month != days[i - 1].month else f"{d.day}"
            x = left + (i + 0.5) * slot
            body += [
                f'<text class="muted" x="{x:.1f}" y="{base + 16}" text-anchor="middle">{label}</text>',
                f'<text class="muted" x="{x:.1f}" y="{base + 30}" text-anchor="middle">{WEEKDAY_NAMES[d.weekday()]}</text>',
            ]
    return svg(width, height, body)


def ratio(num: float, den: float) -> str:
    return f"{num / den:.0%}" if den else "-"


def issue_counts(days: list[dt.date], by_date: dict[dt.date, dict], login: str | None) -> tuple[int, int] | None:
    """期間に立てた Issue と閉じられた Issue の数。対応表に無い人と、取り始める前の期間は None にする。"""
    counted = [by_date[d]["issues"] for d in days if d in by_date and "issues" in by_date[d]]
    if login is None or not counted:
        return None
    return (sum(c.get(login, {}).get("opened", 0) for c in counted),
            sum(c.get(login, {}).get("closed", 0) for c in counted))


def issue_cell(counts: tuple[int, int] | None, i: int) -> str:
    return "-" if counts is None else str(counts[i])


def usage(days: list[dt.date], by_date: dict[dt.date, dict], email: str) -> dict:
    """期間を通した量・成果・使い方。内訳は後から取り始めたので、使い方は内訳のある日だけで出す。"""
    rows = [by_date[d]["members"][email] for d in days if d in by_date and email in by_date[d]["members"]]
    used = [r for r in rows if r.get("tokens", 0) >= MIN_USED_TOKENS]
    detailed = [r for r in rows if "cost_by_model" in r]
    u = {key: sum(r.get(key, 0) for r in rows) for key in (
        "tokens", "active_seconds", "sessions", "cost_usd", "commits", "pull_requests", "lines_added", "lines_removed")}
    u.update({"used_days": len(used), "detailed_days": len(detailed)})

    def family(model: str) -> str:
        # claude-opus-5-5 を opus 5.5 にする。古いバージョンが残っていれば別の種類として見える
        parts = model.lower().removeprefix("claude-").split("-")
        name = next((p for p in parts if p in MODEL_FAMILIES), None)
        if name is None:
            return model
        # 日付の付いた名前（-20250929 など）の日付は版に含めない
        version = [p for p in parts if p.isdigit() and len(p) <= 2]
        return f"{name} {'.'.join(version)}" if version else name

    cost = [c for r in detailed for c in r["cost_by_model"]]
    whole = sum(c["cost_usd"] for c in cost)
    main = [c for c in cost if c["query_source"] == "main"]
    skills: dict[str, int] = {}
    skill_days = [r["skills"] for r in rows if r.get("skills") is not None]
    for day in skill_days:
        for skill, n in day.items():
            skills[skill] = skills.get(skill, 0) + n
    u.update({
        "subagent": (sum(c["cost_usd"] for c in cost if c["query_source"] == "subagent"), whole),
        # 使い分けは良し悪しではなく、使ったかどうかを種類で数える
        "efforts": [e for e in EFFORTS if any(c["effort"] == e for c in main)],
        # サブエージェントと補助の処理は、Claude Code が自動でモデルを選ぶことがあるので数えない
        "families": sorted({family(c["model"]) for c in main}),
        "models": cost,
        # 取り始める前の期間は None にして、使っていない（0）と区別する
        "skills": skills if skill_days else None,
    })
    return u


def kinds(names: list[str]) -> str:
    return f"{len(names)}（{', '.join(names)}）" if names else "0"


def skill_total(u: dict) -> str:
    return "未取得" if u["skills"] is None else f"{sum(u['skills'].values())}回"


def skills_table(days: list[dt.date], by_date: dict[dt.date, dict], email: str) -> str:
    skills = usage(days, by_date, email)["skills"]
    if skills is None:
        return "スキルの記録が届いていない。送信設定がログを送るようになると出る。"
    whole = sum(skills.values())
    if not whole:
        return "期間中にスキルを使っていない。"
    lines = ["| スキル | 回数 | 割合 |", "|---|--:|--:|"]
    for skill, n in sorted(skills.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `{skill}` | {n} | {n / whole:.0%} |")
    return "\n".join(lines)


def num(v: float) -> str:
    return f"{v:.1f}".removesuffix(".0")


def team_average(stats: dict[str, dict]) -> dict | None:
    """全員の1人あたりの平均。Issue・スキル・使い方の内訳は、取れている人だけで割る。AVERAGE_MIN 人に満たなければ None。"""
    us = list(stats.values())
    if len(us) < AVERAGE_MIN:
        return None
    mean = lambda vals: sum(vals) / len(vals) if vals else None  # noqa: E731
    issues = [u["issues"] for u in us if u.get("issues") is not None]
    skills = [sum(u["skills"].values()) for u in us if u["skills"] is not None]
    detailed = [u for u in us if u["detailed_days"]]
    avg = {k: mean([u[k] for u in us]) or 0 for k in (
        "tokens", "active_seconds", "sessions", "commits", "pull_requests", "lines_added", "lines_removed")}
    avg.update({
        "issues": (mean([i[0] for i in issues]), mean([i[1] for i in issues])) if issues else None,
        "skills": mean(skills),
        # 割合は人ごとの割合の平均ではなく、全員の合計で割る
        "subagent": (sum(u["subagent"][0] for u in detailed), sum(u["subagent"][1] for u in detailed)) if detailed else None,
    })
    return avg


def average_cells(avg: dict | None) -> dict[str, str] | None:
    """平均の行の、表の列ごとの文字。MD と board で同じものを使う。"""
    if avg is None:
        return None
    return {
        "skills": "未取得" if avg["skills"] is None else f"{num(avg['skills'])}回",
        "commits": num(avg["commits"]),
        "pull_requests": num(avg["pull_requests"]),
        "lines_added": num(avg["lines_added"]),
        "lines_removed": num(avg["lines_removed"]),
        "issues_opened": "-" if avg["issues"] is None else num(avg["issues"][0]),
        "issues_closed": "-" if avg["issues"] is None else num(avg["issues"][1]),
        "minutes": minutes(avg["active_seconds"]),
        "tokens": compact(avg["tokens"]),
        "per_session": compact(avg["tokens"] / avg["sessions"]) if avg["sessions"] else "-",
        "subagent": "-" if avg["subagent"] is None else ratio(*avg["subagent"]),
    }


def amount_table(stats: dict[str, dict]) -> str:
    lines = [
        "| メンバー | 利用時間 | トークン量 | commit | PR | 追加した行 | 削除した行 | 立てた Issue | 閉じた Issue |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for m, u in stats.items():
        lines.append(
            f"| [{name(m)}](members/{name(m)}.md) | {minutes(u['active_seconds'])} "
            f"| {compact(u['tokens'])} | {u['commits']} | {u['pull_requests']} "
            f"| {u['lines_added']} | {u['lines_removed']} "
            f"| {issue_cell(u['issues'], 0)} | {issue_cell(u['issues'], 1)} |"
        )
    if a := average_cells(team_average(stats)):
        lines.append(f"| **平均** | {a['minutes']} | {a['tokens']} | {a['commits']} | {a['pull_requests']} "
                     f"| {a['lines_added']} | {a['lines_removed']} | {a['issues_opened']} | {a['issues_closed']} |")
    return "\n".join(lines)


def usage_table(stats: dict[str, dict]) -> str:
    lines = [
        "| メンバー | スキル | サブエージェントに任せた割合 | Effort | モデル | 1会話あたりのトークン量 |",
        "|---|--:|--:|---|---|--:|",
    ]
    for m, u in stats.items():
        if not u["detailed_days"]:
            continue
        lines.append(
            f"| {name(m)} | {skill_total(u)} | {ratio(*u['subagent'])} | {kinds(u['efforts'])} "
            f"| {kinds(u['families'])} | {compact(u['tokens'] / u['sessions']) if u['sessions'] else '-'} |"
        )
    if len(lines) == 2:
        return "内訳のデータがまだ無い。"
    if a := average_cells(team_average(stats)):
        lines.append(f"| **平均** | {a['skills']} | {a['subagent']} | - | - | {a['per_session']} |")
    return "\n".join(lines)


def models_table(days: list[dt.date], by_date: dict[dt.date, dict], email: str) -> str:
    u = usage(days, by_date, email)
    if not u["detailed_days"]:
        return "内訳のデータがまだ無い。"
    groups: dict[tuple, float] = {}
    # 補助の処理は Claude Code が自動で行い、本人の使い方を表さないので出さない
    for c in u["models"]:
        if c["query_source"] != "auxiliary":
            k = (c["model"], c["effort"], c["query_source"])
            groups[k] = groups.get(k, 0) + c["cost_usd"]
    whole = sum(groups.values())
    shown = [(k, v) for k, v in sorted(groups.items(), key=lambda kv: -kv[1]) if whole and v / whole >= 0.005]
    if not shown:
        return "費用の記録が無い。"
    lines = [
        f"モデル別の記録がある{u['detailed_days']}日分の、費用に占める割合。1% に満たない組み合わせは出さない。"
        "Effort は応答にかける思考量の設定である。区分は、本人とやり取りする会話（メイン）か、そこから仕事を任された別の Claude（サブエージェント）かを表す。",
        "",
        "| モデル | Effort | 区分 | 費用の割合 |",
        "|---|---|---|--:|",
    ]
    for (model, effort, qs), v in shown:
        effort = "-" if effort == "none" else effort
        lines.append(f"| `{model}` | {effort} | {QUERY_SOURCES.get(qs, qs)} | {v / whole:.0%} |")
    return "\n".join(lines)


def daily_table(days: list[dt.date], by_date: dict[dt.date, dict], email: str, login: str | None) -> str:
    lines = [
        "| 日付 | トークン量 | 利用時間 | 会話の数 | commit | PR | 追加した行 | 削除した行 | 立てた Issue | 閉じた Issue |",
        "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for d in reversed(days):
        if d not in by_date:
            continue
        v = by_date[d]["members"].get(email, {})
        issues = issue_counts([d], by_date, login)
        lines.append(
            f"| {label_of(d)} | {compact(v.get('tokens', 0))} | {minutes(v.get('active_seconds', 0))} "
            f"| {v.get('sessions', 0)} | {v.get('commits', 0)} | {v.get('pull_requests', 0)} "
            f"| {v.get('lines_added', 0)} | {v.get('lines_removed', 0)} "
            f"| {issue_cell(issues, 0)} | {issue_cell(issues, 1)} |"
        )
    return "\n".join(lines)


def entrypoint_table(days: list[dt.date], by_date: dict[dt.date, dict], email: str) -> str:
    # 内訳は後から取り始めたので、持っている日だけで割合を出す
    counted = [by_date[d] for d in days if d in by_date and email in by_date[d]["members"]
               and "entrypoints" in by_date[d]["members"][email]]
    totals: dict[str, float] = {}
    for day in counted:
        for ep, seconds in day["members"][email]["entrypoints"].items():
            totals[ep] = totals.get(ep, 0) + seconds
    whole = sum(totals.values())
    if not whole:
        return "内訳のデータがまだ無い。"
    lines = [
        f"{counted[0]['date']} 〜 {counted[-1]['date']} の利用時間を、Claude Code を起動した場所別に分けた内訳（記録がある日のみ）。",
        "",
        "| 使った場所 | 利用時間 | 割合 |",
        "|---|--:|--:|",
    ]
    for ep, seconds in sorted(totals.items(), key=lambda kv: -kv[1]):
        label = ENTRYPOINTS.get(ep, ep)
        lines.append(f"| {label}（`{ep}`） | {minutes(seconds)} | {seconds / whole:.0%} |")
    return "\n".join(lines)


def member_page(email: str, days: list[dt.date], by_date: dict[dt.date, dict], login: str | None) -> str:
    who = name(email)
    return "\n".join([
        "<!-- render.py が毎日作り直す。手で直しても次の実行で消える -->",
        f"# {who} の Claude Code の利用状況",
        "",
        f"[全体](../README.md) へ戻る。各項目が何を数えているかは "
        f"[指標の定義](../docs/metrics.md) にある。",
        "",
        f"## 毎日の推移（{days[0]} 〜 {days[-1]}）",
        "",
        "土日は表にも図にも出さない。縦軸は本人の値に合わせてあり、ほかの人のページとは目盛りが違う。",
        "",
        f"![{who} の毎日の推移](../charts/members/{who}.svg)",
        "",
        daily_table(days, by_date, email, login),
        "",
        "## スキル",
        "",
        skills_table(days, by_date, email),
        "",
        "## モデルと Effort",
        "",
        models_table(days, by_date, email),
        "",
        "## 使った場所",
        "",
        entrypoint_table(days, by_date, email),
        "",
    ])


def period(days: list[dict]) -> tuple[dict[dt.date, dict], list[dt.date]]:
    """日付ごとの集計と、図と表に出す平日。board もこの決め方で並べる。"""
    by_date = {date_of(d): d for d in days}
    last = date_of(days[-1])
    # 送信設定が届く前の日は全員が空になる。使わなかった日と見分けられないので、期間に入れない
    first = next((date_of(d) for d in days
                  if any(v.get("tokens", 0) >= MIN_USED_TOKENS for v in d["members"].values())), last)
    start = max(first, last - dt.timedelta(days=MEMBER_DAYS - 1))
    span = [start + dt.timedelta(days=i) for i in range((last - start).days + 1)]
    return by_date, [d for d in span if d.weekday() < 5]


def main() -> None:
    days = load()
    if not days:
        print("No data yet. Nothing to render.")
        return
    by_date, span = period(days)
    if not span:
        print("No weekday data yet. Nothing to render.")
        return
    members = sorted({m for d in span if d in by_date for m in by_date[d]["members"]})
    accounts = json.loads(ACCOUNTS.read_text()) if ACCOUNTS.exists() else {}

    (CHART_DIR / "members").mkdir(parents=True, exist_ok=True)
    MEMBER_DIR.mkdir(exist_ok=True)
    # 期間から外れた人のページを残すと、古い数字が最新に見える
    for stale in [*MEMBER_DIR.glob("*.md"), *(CHART_DIR / "members").glob("*.svg")]:
        if stale.stem not in {name(m) for m in members}:
            stale.unlink()

    for m in members:
        (CHART_DIR / "members" / f"{name(m)}.svg").write_text(member_chart(span, by_date, m))
        (MEMBER_DIR / f"{name(m)}.md").write_text(member_page(m, span, by_date, accounts.get(name(m))))

    stats = {m: {**usage(span, by_date, m), "issues": issue_counts(span, by_date, accounts.get(name(m)))} for m in members}
    stats = dict(sorted(stats.items(), key=lambda kv: -kv[1]["tokens"]))
    if members:
        (CHART_DIR / "team-daily.svg").write_text(team_chart(span, by_date, members, "tokens", compact))
        (CHART_DIR / "team-commits.svg").write_text(team_chart(span, by_date, members, "commits", lambda v: f"{v:g}"))
    report = "\n".join([
        f"最終更新：{days[-1]['date']} 分まで",
        "",
        f"図と表はどれも {span[0]} 〜 {span[-1]} の平日の分で、期間のトークン量の多い順に並べる。",
        f"図の破線は全員の1人あたりの{SMOOTH_DAYS}日平均（直前{SMOOTH_DAYS}平日の移動平均）、表の「平均」は全員の1人あたりの平均である。"
        f"どちらも{AVERAGE_MIN}人に満たないときは出さない。",
        "",
        "### 日ごとのトークン量",
        "",
        "![メンバー別の日ごとのトークン量](charts/team-daily.svg)",
        "",
        "### 日ごとの commit",
        "",
        "上のトークン量と同じ日付で並べる。トークン量が増えた時期に commit も増えているかを見比べる。",
        "",
        "![メンバー別の日ごとの commit](charts/team-commits.svg)",
        "",
        "### 量と成果",
        "",
        "どれも期間の合計である。",
        "",
        amount_table(stats),
        "",
        "### 使い方",
        "",
        usage_table(stats),
    ])
    text = README.read_text()
    text = re.sub(r"(<!-- report:start -->\n).*?(<!-- report:end -->)", lambda m: m[1] + report + "\n" + m[2], text, flags=re.S)
    README.write_text(text)
    print(f"Rendered {len(members)} members from {len(days)} days")


if __name__ == "__main__":
    main()
