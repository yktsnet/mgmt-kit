#!/usr/bin/env python3
"""board のシートのテンプレートと、架空の候補者・評価・採点結果のダミーを作り直す。設定（在籍者・採用枠・定義）はアプリが持つので、ここでは作らない。"""

import datetime as dt
import shutil
from pathlib import Path

import sys

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

BOARD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BOARD))
LADDER_MD = BOARD.parent / "ladder" / "docs" / "ladder.md"
from app.demo import EVALUATORS  # noqa: E402
TEMPLATES = BOARD / "templates"
DRIVE = BOARD / "samples" / "drive"
LADDER = BOARD / "samples" / "ladder"
PERIOD = "2026-01〜2026-03"
AXES = ["A", "B", "C", "D", "E"]
STAGES = ["応募", "書類選考", "一次面接", "最終面接", "内定", "入社", "不採用", "辞退"]
DOMAIN = "example.com"

PROFILE_LABELS = ["氏名", "メール", "応募枠", "段階", "応募日", "経路"]
INTERVIEW_HEADER = ["日付", "面接官", *AXES, "所見"]
REQ_HEADER = ["枠", "人数", "参照ペルソナ", *AXES]

# 段階ごとに面接の記録の量が変わるよう、選考の各段階に1人以上を置く。
# (名前, 応募枠, 段階, 応募日, 経路, [(面接日, 面接官, A〜E, 所見)])
CANDIDATES = [
    ("liam-price", "リード", "最終面接", "2026-03-02", "紹介", [
        ("2026-03-12", "alice-walker", [4, 3, None, 3, None], "要件の詰め方が具体的"),
        ("2026-03-26", "emma-hughes", [None, 4, 2, None, 3], "型を自分で直した経験がある"),
    ]),
    ("mia-collins", "開発", "内定", "2026-02-16", "求人媒体", [
        ("2026-02-26", "daniel-brooks", [3, 3, None, 2, 2], ""),
        ("2026-03-09", "alice-walker", [3, 3, 2, 3, None], "検証の設計を説明できる"),
    ]),
    ("noah-reed", "開発", "一次面接", "2026-03-20", "採用サイト", [
        ("2026-04-02", "grace-turner", [2, 3, None, 2, 3], "基盤は強い。上流は未経験"),
    ]),
    ("olivia-hart", "開発", "書類選考", "2026-04-08", "求人媒体", []),
    ("ethan-shaw", "リード", "応募", "2026-04-15", "採用サイト", []),
    ("sophie-lane", "開発", "不採用", "2026-02-02", "求人媒体", [
        ("2026-02-12", "daniel-brooks", [1, 2, None, 1, 2], "型に沿って書く経験が無い"),
    ]),
]


# 在籍者の採点結果。名前は usage のダミーの名簿と同じにして、usage と突き合わせられるようにする。
# usage の README の「あるべき姿」と崩れ方の型に合わせ、型に乗っていない人は B を低くする。None は未観測
STAFF = [
    ("alice-walker", [4, 4, 3, 4, 3]),
    ("emma-hughes", [3, 4, 2, 3, 3]),
    ("ben-carter", [3, 1, 4, 2, 3]),
    ("henry-ward", [2, 2, 3, None, 2]),
    ("chloe-evans", [3, 2, 2, 2, None]),
    ("felix-grant", [2, 1, 3, 1, 2]),
    ("daniel-brooks", [3, 3, 2, 2, 2]),
    ("grace-turner", [2, 3, 1, 3, 3]),
    ("isla-morgan", [2, 2, None, 2, 1]),
    ("jack-foster", [1, 1, 2, None, 1]),
]
AXIS_NAMES = ["A 上流・提案", "B 型の運用", "C ドメイン", "D 検証", "E 基盤"]


def scoresheet(name: str, scores: list) -> str:
    cells = ["未観測" if v is None else f"L{v}" for v in scores]
    level = min(v for v in scores[:2] if v is not None)
    weakest = min((v, i) for i, v in enumerate(scores[:2]))[1]
    return (
        f"# 採点 — {name} / {PERIOD}\n\n"
        "## 点\n\n"
        f"| {' | '.join(AXIS_NAMES)} |\n"
        f"|{'---|' * len(AXIS_NAMES)}\n"
        f"| {' | '.join(cells)} |\n\n"
        "## 段階\n\n"
        f"**L{level}**（A と B の低いほう）\n\n"
        "## 次に上げる1軸\n\n"
        f"**{AXIS_NAMES[weakest]}**\n"
    )


def stage_validation(cell: str) -> DataValidation:
    dv = DataValidation(type="list", formula1='"' + ",".join(STAGES) + '"', allow_blank=True)
    dv.add(cell)
    return dv


def score_validation(ref: str) -> DataValidation:
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=True)
    dv.add(ref)
    return dv


def candidate_book(profile: dict | None = None, interviews: list | None = None) -> Workbook:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "候補者"
    for i, label in enumerate(PROFILE_LABELS, start=1):
        ws.cell(row=i, column=1, value=label)
        if profile:
            value = profile[label]
            ws.cell(row=i, column=2, value=dt.date.fromisoformat(value) if label == "応募日" else value)
    ws.add_data_validation(stage_validation(f"B{PROFILE_LABELS.index('段階') + 1}"))
    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 28

    iv = wb.create_sheet("面接")
    iv.append(INTERVIEW_HEADER)
    for date, who, scores, note in interviews or []:
        iv.append([dt.date.fromisoformat(date), f"{who}@{DOMAIN}", *scores, note])
    iv.add_data_validation(score_validation("C2:G200"))
    iv.column_dimensions["B"].width = 26
    iv.column_dimensions["H"].width = 36
    return wb


PERIOD_ID = "2026-H2"
# 評価のダミー。STAFF の点から判定を作る。途中の人は C〜E を空欄のまま残し、未着手の人はファイルを置かない
REVIEW_DONE = ["emma-hughes", "ben-carter", "chloe-evans", "grace-turner", "henry-ward"]
REVIEW_PARTIAL = ["daniel-brooks", "felix-grant"]


def review_book_template() -> Workbook:
    """評価のテンプレート。Ladder の初版（v1）の細目を並べ、対象の値は空けておく。"""
    from app.definition import from_ladder_md
    from app.review import template_rows

    wb = Workbook()
    meta = wb.active
    assert meta is not None
    meta.title = "対象"
    for label in ("メール", "期", "版", "Reviewer"):
        meta.append([label, "v1" if label == "版" else None])
    ws = wb.create_sheet("評価")
    for row in template_rows(from_ladder_md(LADDER_MD.read_text(encoding="utf-8"))):
        ws.append(row)
    dv = DataValidation(type="list", formula1='"○,×,未観測"', allow_blank=True)
    dv.add("E2:E500")
    ws.add_data_validation(dv)
    return wb


def review_book(name: str, scores: list, partial: bool) -> Workbook:
    from app.definition import from_ladder_md
    from app.review import template_rows

    items = from_ladder_md(LADDER_MD.read_text(encoding="utf-8"))
    wb = Workbook()
    meta = wb.active
    assert meta is not None
    meta.title = "対象"
    ev = EVALUATORS.get(name)
    for row in (["メール", f"{name}@{DOMAIN}"], ["期", PERIOD_ID], ["版", "v1"], ["Reviewer", f"{ev}@{DOMAIN}" if ev else None]):
        meta.append(row)
    meta.column_dimensions["B"].width = 30
    ws = wb.create_sheet("評価")
    by_axis = dict(zip(AXES, scores))
    for row in template_rows(items):
        if row[0] in AXES:
            axis, level = row[0], int(row[1][1:])
            s = by_axis[axis]
            if partial and axis in ("C", "D", "E"):
                pass
            elif s is None:
                row[4] = "未観測" if level == 2 else None
            elif level <= s:
                row[4] = "○"
            elif level == s + 1:
                # 届かなかったマスは、最初の細目だけ × にする。残りは判定しなくても段階が決まる
                row[4] = "×" if row[2] == "a" else None
            if row[4] in ("○", "×"):
                row[5] = "PR と Issue を読んで確かめた"
        ws.append(row)
    dv = DataValidation(type="list", formula1='"○,×,未観測"', allow_blank=True)
    dv.add("E2:E500")
    ws.add_data_validation(dv)
    for col, width in zip("ABCDEF", (6, 6, 6, 64, 8, 36)):
        ws.column_dimensions[col].width = width
    return wb


def main() -> None:
    for d in (TEMPLATES, DRIVE, LADDER):
        shutil.rmtree(d, ignore_errors=True)
    (DRIVE / "candidates").mkdir(parents=True)
    TEMPLATES.mkdir(parents=True)
    LADDER.mkdir(parents=True)
    for name, scores in STAFF:
        (LADDER / f"{name}.md").write_text(scoresheet(name, scores), encoding="utf-8")

    candidate_book().save(TEMPLATES / "candidate.xlsx")
    review_book_template().save(TEMPLATES / "review.xlsx")
    (DRIVE / "reviews" / PERIOD_ID).mkdir(parents=True)
    staff = dict(STAFF)
    for name in REVIEW_DONE + REVIEW_PARTIAL:
        review_book(name, staff[name], name in REVIEW_PARTIAL).save(DRIVE / "reviews" / PERIOD_ID / f"{name}.xlsx")

    for name, req, stage, applied, source, interviews in CANDIDATES:
        profile = {
            "氏名": name.replace("-", " ").title(),
            "メール": f"{name}@{DOMAIN}",
            "応募枠": req,
            "段階": stage,
            "応募日": applied,
            "経路": source,
        }
        candidate_book(profile, interviews).save(DRIVE / "candidates" / f"{name}.xlsx")
    print(f"wrote {len(CANDIDATES)} candidates and {len(REVIEW_DONE + REVIEW_PARTIAL)} reviews to {DRIVE.relative_to(BOARD)}")
    print(f"wrote {len(STAFF)} scoresheets to {LADDER.relative_to(BOARD)}")


if __name__ == "__main__":
    main()
