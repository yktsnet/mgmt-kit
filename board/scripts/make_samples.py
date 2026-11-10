#!/usr/bin/env python3
"""board のテンプレートと、架空の候補者・求める人材のダミーを作り直す。"""

import datetime as dt
import shutil
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

BOARD = Path(__file__).resolve().parent.parent
TEMPLATES = BOARD / "templates"
DRIVE = BOARD / "samples" / "drive"
AXES = ["A", "B", "C", "D", "E"]
STAGES = ["応募", "書類選考", "一次面接", "最終面接", "内定", "入社", "不採用", "辞退"]
DOMAIN = "example.com"

PROFILE_LABELS = ["氏名", "メール", "応募枠", "段階", "応募日", "経路"]
INTERVIEW_HEADER = ["日付", "面接官", *AXES, "所見"]
REQ_HEADER = ["枠", "人数", "参照ペルソナ", *AXES]

# (枠, 人数, 参照ペルソナ, A〜E)。None は求めない軸
REQUISITIONS = [
    ("リード", 1, "L4", [4, 4, None, 3, None]),
    ("開発", 2, "L3", [3, 3, None, 3, 2]),
]

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


def requisition_book(rows: list) -> Workbook:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "求める人材"
    ws.append(REQ_HEADER)
    for name, count, persona, target in rows:
        ws.append([name, count, persona, *target])
    ws.add_data_validation(score_validation("D2:H200"))
    return wb


def main() -> None:
    for d in (TEMPLATES, DRIVE):
        shutil.rmtree(d, ignore_errors=True)
    (DRIVE / "candidates").mkdir(parents=True)
    TEMPLATES.mkdir(parents=True)

    candidate_book().save(TEMPLATES / "candidate.xlsx")
    requisition_book([]).save(TEMPLATES / "requisitions.xlsx")

    requisition_book(REQUISITIONS).save(DRIVE / "requisitions.xlsx")
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
    print(f"wrote {len(CANDIDATES)} candidates and {len(REQUISITIONS)} requisitions to {DRIVE.relative_to(BOARD)}")


if __name__ == "__main__":
    main()
