#!/usr/bin/env python3
"""usage/ の集計に、架空の10人と8リポのダミーデータを置き、表とグラフを作り直す。"""

import datetime as dt
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "usage" / "tools" / "usage"
CC = ROOT / "claude-code"
GA = ROOT / "github-actions"
LAST = dt.date(2026, 4, 24)
# どの表とグラフも直近4週を描くので、データも4週分だけ作る
DAYS = 28
DOMAIN = "example.com"
# 1日に読むトークンのほとんどはキャッシュの読み込みで単価が低いので、費用1ドルあたりのトークンを大きく置く
TOKENS_PER_USD = 1_600_000

# README.md の「あるべき姿」と崩れ方の型が見えるように、人ごとの傾向を置く。
# (名前, GitHub, 平日1日の費用の目安, 使う日の割合, 主な Effort, 主なモデル,
#  使った日1日のスキルの回数, Issue を立てる度合い, commit のうち PR になる割合)
MEMBERS = [
    # あるべき姿：型に乗り、量も足りている
    ("alice-walker", "alicew", 260, 0.95, ["medium", "high", "xhigh", "low"], ["opus 5.5", "sonnet 5.5", "haiku 5.5"], 2.5, 8, 0.45),
    ("emma-hughes", "emmah", 110, 0.95, ["medium", "high", "low"], ["opus 5.5", "sonnet 5.5"], 2.0, 4, 0.4),
    # 量は多いが型に乗っていない
    ("ben-carter", "bencarter", 240, 0.95, ["high"], ["opus 5.5"], 0.3, 0, 0.02),
    ("henry-ward", None, 150, 0.9, ["high", "medium"], ["opus 5.5", "sonnet 5.5"], 0.5, 0, 0.1),
    ("chloe-evans", "chloe-e", 95, 0.9, ["high"], ["opus 5.5"], 0.3, 1, 0.1),
    ("felix-grant", "fgrant", 90, 0.9, ["medium"], ["opus 5.5"], 0.15, 0, 0.05),
    # 中ほど
    ("daniel-brooks", "dbrooks", 80, 0.9, ["medium", "high"], ["opus 5.5", "haiku 4.5"], 1.0, 2, 0.3),
    # 型に乗っているが量が少ない
    ("grace-turner", "gturner", 25, 0.85, ["medium", "high"], ["opus 5.5", "sonnet 5.5"], 1.5, 3, 0.4),
    ("isla-morgan", "islam", 15, 0.75, ["low", "medium"], ["sonnet 5.5"], 1.2, 2, 0.4),
    # どちらも少ない
    ("jack-foster", "jfoster", 25, 0.1, ["medium"], ["opus 5.5"], 0.0, 0, 0.1),
]
# 人ごとの (サブエージェントに任せる割合, 1会話あたりの費用)。会話を長く続ける人ほど1会話の費用が大きい
STYLE = {
    "alice-walker": (0.35, 6), "ben-carter": (0.1, 7), "chloe-evans": (0.1, 30), "daniel-brooks": (0.25, 6),
    "emma-hughes": (0.3, 5), "felix-grant": (0.05, 18), "grace-turner": (0.2, 3), "henry-ward": (0.3, 8),
    "isla-morgan": (0.15, 2), "jack-foster": (0.2, 4),
}
# 週に1日しか使わない人
RARE = "jack-foster"
# sdlc-kit の flow-team と doc-style などのスキルを、使われる重みで持つ
SKILLS = {"issue-work": 5, "issue-draft": 2, "rework-review": 2, "jp-writing": 1, "md-writing": 1,
          "daily-report": 1, "guarantee-audit": 0.5, "grasp": 0.3}
# alice-walker が作り、ほかのメンバーも使っている自作のスキル
CUSTOM_SKILL = ("api-scaffold", {"alice-walker": 2, "emma-hughes": 1, "daniel-brooks": 1, "grace-turner": 1})
MODEL_IDS = {
    "opus 5.5": "claude-opus-5-5", "sonnet 5.5": "claude-sonnet-5-5", "haiku 5.5": "claude-haiku-5-5",
    "haiku 4.5": "claude-haiku-4-5-20251001", "opus 4.8": "claude-opus-4-8",
}
ENTRYPOINTS = ["cli", "claude-vscode", "claude-desktop"]

# (リポ, ワークフロー, きっかけ, 平日1日の回数, 1回の分数)
WORKFLOWS = [
    ("web-app", "CI", "pull_request", 14, 4),
    ("web-app", "CI", "push", 4, 4),
    ("web-app", "e2e", "pull_request", 6, 9),
    ("api-server", "CI", "pull_request", 10, 3),
    ("api-server", "Deploy", "push", 2, 6),
    ("mobile-app", "Build", "pull_request", 3, 7),
    ("admin-console", "CI", "pull_request", 5, 2),
    ("data-pipeline", "nightly", "schedule", 1, 18),
    ("data-pipeline", "issue-triage", "issues", 4, 2),
    ("infra", "terraform-plan", "pull_request", 2, 3),
    ("docs-site", "Deploy", "push", 2, 2),
    ("design-system", "gitleaks", "pull_request", 4, 1),
    ("design-system", "Delete merged branch", "pull_request", 4, 1),
]


def weekdays(first: dt.date, last: dt.date) -> list[dt.date]:
    days = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)]
    return [d for d in days if d.weekday() < 5]


def member_day(rng: random.Random, m: tuple, d: dt.date) -> dict | None:
    name, _, usd, rate, efforts, models, skill_rate, _, pr_ratio = m
    if (d.weekday() != 0) if name == RARE else rng.random() > rate:
        return None
    sub_share, usd_per_session = STYLE[name]
    cost = round(usd * rng.uniform(0.5, 1.5), 4)
    tokens = round(cost * TOKENS_PER_USD * rng.uniform(0.85, 1.15))
    cli = round(cost * rng.uniform(14, 22))
    sessions = max(1, round(cost / (usd_per_session * rng.uniform(0.8, 1.2))))
    commits = rng.randint(0, max(1, round(cost / 9)))
    split = [("main", 0.95 - sub_share), ("subagent", sub_share), ("auxiliary", 0.05)]
    cost_by_model = []
    for qs, share in split:
        if qs == "main":
            for i, e in enumerate(efforts):
                weight = 0.6 if i == 0 else 0.4 / (len(efforts) - 1)
                model = models[0] if i % 2 == 0 or len(models) == 1 else models[1]
                cost_by_model.append({"model": MODEL_IDS[model], "effort": e, "query_source": qs,
                                      "cost_usd": round(cost * share * weight, 4)})
        else:
            model = models[-1] if qs == "auxiliary" else models[0]
            cost_by_model.append({"model": MODEL_IDS[model], "effort": "none" if qs == "auxiliary" else efforts[0],
                                  "query_source": qs, "cost_usd": round(cost * share, 4)})
    weights = dict(SKILLS)
    if name in CUSTOM_SKILL[1]:
        weights[CUSTOM_SKILL[0]] = CUSTOM_SKILL[1][name]
    skills: dict[str, int] = {}
    for _ in range(max(0, round(rng.gauss(skill_rate, skill_rate * 0.6)))):
        s = rng.choices(list(weights), weights=list(weights.values()))[0]
        skills[s] = skills.get(s, 0) + 1
    eps = {"cli": round(cli * 0.7), "claude-vscode": round(cli * 0.3)} if name != "isla-morgan" else {"claude-vscode": cli}
    return {
        "tokens": tokens, "active_seconds": cli, "sessions": sessions, "cost_usd": cost,
        "commits": commits, "pull_requests": sum(rng.random() < pr_ratio for _ in range(commits)),
        "lines_added": commits * rng.randint(20, 160), "lines_removed": commits * rng.randint(2, 20),
        "entrypoints": eps,
        "active_by_type": {"cli": cli, "user": round(cli * 0.6)},
        "tokens_by_type": {"cacheRead": round(tokens * 0.93), "cacheCreation": round(tokens * 0.05),
                           "input": round(tokens * 0.01), "output": round(tokens * 0.01)},
        "cost_by_model": cost_by_model,
        "skills": skills,
    }


def claude_code(rng: random.Random) -> None:
    data = CC / "data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir()
    for d in weekdays(LAST - dt.timedelta(days=DAYS - 1), LAST):
        members, issues = {}, {}
        for m in MEMBERS:
            row = member_day(rng, m, d)
            if row:
                members[f"{m[0]}@{DOMAIN}"] = row
            login, issue_rate = m[1], m[7]
            if login and issue_rate:
                opened = rng.randint(0, issue_rate)
                closed = rng.randint(0, opened + 1)
                if opened or closed:
                    issues[login] = {"opened": opened, "closed": closed}
        day = {"date": d.isoformat(), "members": dict(sorted(members.items())), "issues": dict(sorted(issues.items()))}
        (data / f"{d}.json").write_text(json.dumps(day, ensure_ascii=False, indent=2) + "\n")
    (CC / "github.json").write_text(json.dumps({m[0]: m[1] for m in MEMBERS if m[1]}, indent=2) + "\n")


def github_actions(rng: random.Random) -> None:
    data = GA / "data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir()
    first = LAST - dt.timedelta(days=DAYS - 1)
    for i in range(DAYS):
        d = first + dt.timedelta(days=i)
        repos: dict[str, list] = {}
        for repo, wf, event, runs, per in WORKFLOWS:
            # issues で起動する集計を途中の2週だけ動かし、ワークフロー別の表に増減を持たせる
            if wf == "issue-triage" and not first + dt.timedelta(days=7) <= d < first + dt.timedelta(days=21):
                continue
            # 平日の回数の目安を、月の分数が無料枠を超えて予算に収まる程度に置く
            runs = max(1, round(runs * 0.45))
            n = runs if event == "schedule" else (rng.randint(0, runs * 2) if d.weekday() < 5 else rng.randint(0, 1))
            if n:
                minutes = sum(max(1, round(per * rng.uniform(0.8, 1.3))) for _ in range(n))
                repos.setdefault(repo, []).append({"workflow": wf, "event": event, "runs": n, "minutes": minutes})
        repos = {r: sorted(rows, key=lambda x: (-x["minutes"], x["workflow"], x["event"])) for r, rows in sorted(repos.items())}
        day = {"date": d.isoformat(), "unreadable": [], "repos": repos}
        (data / f"{d}.json").write_text(json.dumps(day, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    rng = random.Random(20261106)
    claude_code(rng)
    github_actions(rng)
    for t in (CC, GA):
        subprocess.run([sys.executable, str(t / "render.py")], check=True)


if __name__ == "__main__":
    main()
