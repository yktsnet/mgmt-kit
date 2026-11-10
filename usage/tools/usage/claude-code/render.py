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
SEATS = ROOT / "seats.json"
ACCOUNTS = ROOT / "github.json"
MEMBER_DAYS = 28
TOP_SKILLS = 3
# 利用上限は7日ごとに戻るので、seat は7日ごとの費用で見る。1週だけ休んだ人を誤って下げないよう、2週のうち多い方で決める
SEAT_WEEKS = 2
# 2週の平日のうち使った日が2日以下（週1日以下）なら、seat が要らない
REMOVE_MAX_DAYS = 2
# Premium の7日間の上限を費用に直した値と、それに対する Standard の上限の割合。根拠は docs/seats.md の「上限の置き方」
PREMIUM_WEEKLY_USD = 1500
STANDARD_SHARE = 0.2
EFFORTS = ["low", "medium", "high", "xhigh", "max"]
MODEL_FAMILIES = ["opus", "sonnet", "haiku", "fable"]
# 起動して設定を確かめただけの日を、使った日に数えない
MIN_USED_TOKENS = 100_000
SEAT_NAMES = {"standard": "Standard", "premium": "Premium", None: "未設定"}
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
    return [json.loads(p.read_text()) for p in sorted(DATA_DIR.glob("*.json"))]


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


def team_chart(days: list[dt.date], by_date: dict[dt.date, dict], members: list[str], key: str, fmt) -> str:
    # GitHub は画像を本文の幅まで縮めるが、広げはしない。ファイルツリーを開いた画面の本文の幅に合わせ、
    # 文字が縮まずに読める大きさで描く
    width, left, right, top, plot_h = 880, 64, 190, 24, 300
    plot_w = width - left - right
    height = top + plot_h + 44
    peak = nice_max(max((value(by_date[d], m, key) for d in days if d in by_date for m in members), default=0))
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
        ends.append((m, cls, pts[-1][1]))
    label_ys = spread([y for _, _, y in ends], 18, top, top + plot_h)
    for (m, cls, y), ly in zip(ends, label_ys):
        x = left + plot_w + 12
        body += [
            f'<line class="line {cls}" x1="{x}" y1="{ly:.1f}" x2="{x + 10}" y2="{ly:.1f}"/>',
            f'<text class="label" x="{x + 16}" y="{ly + 4:.1f}">{escape(name(m))}</text>',
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


def seat_weeks(by_date: dict[dt.date, dict], email: str, last: dt.date) -> list[tuple[float, int]]:
    """直近の7日ごとの費用と、そのうち使った平日の数。上限は土日の分も数えるので、費用は土日も合わせる。"""
    weeks = []
    for k in range(SEAT_WEEKS):
        days = [last - dt.timedelta(days=7 * k + i) for i in range(7)]
        rows = [(d, by_date[d]["members"][email]) for d in days if d in by_date and email in by_date[d]["members"]]
        weeks.append((sum(r.get("cost_usd", 0) for _, r in rows),
                      sum(1 for d, r in rows if d.weekday() < 5 and r.get("tokens", 0) >= MIN_USED_TOKENS)))
    return weeks


def seat_need(weeks: list[tuple[float, int]] | None, full: bool) -> str | None:
    """要る seat。外してよいなら "none"、Premium の上限まで使うか Standard に収めるかを本人と話すなら "either"、決められないなら None。"""
    if not full or weeks is None or not any(used for _, used in weeks):
        return None
    if sum(used for _, used in weeks) <= REMOVE_MAX_DAYS:
        return "none"
    share = max(cost for cost, _ in weeks) / PREMIUM_WEEKLY_USD
    if share <= STANDARD_SHARE:
        return "standard"
    return "either" if share <= 2 * STANDARD_SHARE else "premium"


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


def standard_table(stats: dict[str, dict]) -> str:
    lines = [
        "| メンバー | スキルの回数 | よく使ったスキル |",
        "|---|--:|---|",
    ]
    for m, u in stats.items():
        skills = u["skills"] or {}
        whole = sum(skills.values())
        top = sorted(skills.items(), key=lambda kv: -kv[1])[:TOP_SKILLS]
        names = "、".join(f"`{s}` {n / whole:.0%}" for s, n in top) if whole else "-"
        lines.append(f"| [{name(m)}](members/{name(m)}.md) | {skill_total(u)} | {names} |")
    return "\n".join(lines)


def work_table(stats: dict[str, dict]) -> str:
    lines = [
        "| メンバー | commit | PR | 追加した行 | 削除した行 | 立てた Issue | 閉じた Issue |",
        "|---|--:|--:|--:|--:|--:|--:|",
    ]
    for m, u in stats.items():
        lines.append(
            f"| {name(m)} | {u['commits']} | {u['pull_requests']} "
            f"| {u['lines_added']} | {u['lines_removed']} "
            f"| {issue_cell(u['issues'], 0)} | {issue_cell(u['issues'], 1)} |"
        )
    return "\n".join(lines)


def input_table(stats: dict[str, dict]) -> str:
    lines = [
        "| メンバー | 利用時間 | トークン量 | 1会話あたりのトークン量 | サブエージェントに任せた割合 | Effort | モデル |",
        "|---|--:|--:|--:|--:|---|---|",
    ]
    for m, u in stats.items():
        # 内訳は後から取り始めたので、内訳の無い人は切り替えの列を空ける
        detail = (f"{ratio(*u['subagent'])} | {kinds(u['efforts'])} | {kinds(u['families'])}"
                  if u["detailed_days"] else "- | - | -")
        lines.append(
            f"| {name(m)} | {minutes(u['active_seconds'])} | {compact(u['tokens'])} "
            f"| {compact(u['tokens'] / u['sessions']) if u['sessions'] else '-'} | {detail} |"
        )
    return "\n".join(lines)


def seat_table(by_date: dict[dt.date, dict], members: list[str], seats: dict, last: dt.date, full: bool) -> str:
    lines = [
        f"直近{SEAT_WEEKS}週（{last - dt.timedelta(days=7 * SEAT_WEEKS - 1)} 〜 {last}、土日を含む）を7日ずつに分け、"
        f"割合の高い方の週で決める。",
        "",
        "| メンバー | いまの seat | Premium の上限に対する割合 | Standard の上限に対する割合 | 要る seat |",
        "|---|---|--:|--:|---|",
    ]
    names = {"none": "要らない", "either": "Review", **SEAT_NAMES}
    # 名簿は表と同じ名前（メールアドレスの @ より前）で引く。記録の無い名簿の人は末尾に並べる
    by_name = {name(m): m for m in members}
    count = {"premium": 0, "standard": 0, "either": 0, None: 0}
    for who in [*by_name, *sorted(set(seats) - set(by_name))]:
        weeks = seat_weeks(by_date, by_name[who], last) if who in by_name else None
        need = seat_need(weeks, full)
        now = seats.get(who)
        now_name = SEAT_NAMES.get(now, now) if who in seats else "名簿に無い"
        if need is None:
            need_name = f"{SEAT_WEEKS}週分たまるまで決めない" if not full and weeks else "記録が届いているかを確かめる"
        else:
            need_name = names[need]
        top = max(c for c, _ in weeks) / PREMIUM_WEEKLY_USD if weeks else None
        share = "- | -" if top is None else f"{top:.0%} | {top / STANDARD_SHARE:.0%}"
        if need != "none":
            count[need] += 1
        lines.append(f"| {who} | {now_name} | {share} | {need_name} |")
    now_count = {k: sum(1 for v in seats.values() if v == k) for k in ("premium", "standard")}
    lines += [
        "",
        f"要る seat の数：Premium {count['premium']}・Standard {count['standard']}・Review {count['either']}"
        + (f"・決められない {count[None]}" if count[None] else "")
        + f"（いまの名簿は Premium {now_count['premium']}・Standard {now_count['standard']}）",
        "",
        f"Premium の上限は Standard の {1 / STANDARD_SHARE:.0f} 倍である。Standard の上限の2倍以内（100% を超え 200% 以下）の人は"
        " Review としている。",
    ]
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


def period(days: list[dict]) -> tuple[dict[dt.date, dict], list[dt.date], bool]:
    """日付ごとの集計、図と表に出す平日、seat を決められるだけの日数があるか。board もこの決め方で並べる。"""
    by_date = {date_of(d): d for d in days}
    last = date_of(days[-1])
    # 送信設定が届く前の日は全員が空になる。使わなかった日と見分けられないので、期間に入れない
    first = next((date_of(d) for d in days
                  if any(v.get("tokens", 0) >= MIN_USED_TOKENS for v in d["members"].values())), last)
    start = max(first, last - dt.timedelta(days=MEMBER_DAYS - 1))
    full = (last - first).days + 1 >= 7 * SEAT_WEEKS
    span = [start + dt.timedelta(days=i) for i in range((last - start).days + 1)]
    return by_date, [d for d in span if d.weekday() < 5], full


def main() -> None:
    days = load()
    if not days:
        print("No data yet. Nothing to render.")
        return
    by_date, span, full = period(days)
    last = date_of(days[-1])
    if not span:
        print("No weekday data yet. Nothing to render.")
        return
    members = sorted({m for d in span if d in by_date for m in by_date[d]["members"]})
    seats = json.loads(SEATS.read_text()) if SEATS.exists() else {}
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
        "",
        "### 標準化されたやり方",
        "",
        "配られたスキルを回しているか。名前を押すと、スキルごとの回数と割合が個人のページに出る。",
        "",
        standard_table(stats),
        "",
        "### 作業の量",
        "",
        "どれも期間の合計である。",
        "",
        "![メンバー別の日ごとの commit](charts/team-commits.svg)",
        "",
        work_table(stats),
        "",
        "### 投入の量",
        "",
        "使う量と、使い方の列を並べる。",
        "",
        "![メンバー別の日ごとのトークン量](charts/team-daily.svg)",
        "",
        input_table(stats),
        "",
        "### seat",
        "",
        seat_table(by_date, list(stats), seats, last, full),
    ])
    text = README.read_text()
    text = re.sub(r"(<!-- report:start -->\n).*?(<!-- report:end -->)", lambda m: m[1] + report + "\n" + m[2], text, flags=re.S)
    README.write_text(text)
    print(f"Rendered {len(members)} members from {len(days)} days")


if __name__ == "__main__":
    main()
