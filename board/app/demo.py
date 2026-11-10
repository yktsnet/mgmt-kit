"""デモの架空の在籍者と採用枠と、候補者の選考の段階。名前は usage のダミーの名簿と同じにして、usage と突き合わせられるようにする。

scripts/make_samples.py も、評価や候補者のダミーを作るときにここを使う。
"""

from dataclasses import dataclass

DOMAIN = "example.com"

STAFF = [
    "alice-walker", "emma-hughes", "ben-carter", "henry-ward", "chloe-evans",
    "felix-grant", "daniel-brooks", "grace-turner", "isla-morgan", "jack-foster",
]
# 3人の Reviewer がそれぞれ3人ずつを評価する。alice-walker は Reviewer がいない
EVALUATORS = {
    "emma-hughes": "alice-walker", "ben-carter": "alice-walker", "daniel-brooks": "alice-walker",
    "chloe-evans": "emma-hughes", "felix-grant": "emma-hughes", "grace-turner": "emma-hughes",
    "henry-ward": "daniel-brooks", "isla-morgan": "daniel-brooks", "jack-foster": "daniel-brooks",
}
MANAGERS = {"alice-walker"}
# 名前の頭文字の動物。デモで人を見分けやすくする
ANIMALS = {
    "alice-walker": "🐊", "emma-hughes": "🐘", "ben-carter": "🐻", "henry-ward": "🦔", "chloe-evans": "🐱",
    "felix-grant": "🦊", "daniel-brooks": "🐬", "grace-turner": "🦒", "isla-morgan": "🦎", "jack-foster": "🐆",
}
# 面接官を務める人に、採用を見られるようにする。Manager は付けなくても見られる
HIRING = {"emma-hughes", "daniel-brooks", "grace-turner"}

# 候補者が通った選考の段階。最後がいまの段階で、応募のままの人は入れない
CANDIDATE_STAGES = {
    "liam-price": ["書類選考", "一次面接", "最終面接"],
    "mia-collins": ["書類選考", "一次面接", "最終面接", "内定"],
    "noah-reed": ["書類選考", "一次面接"],
    "olivia-hart": ["書類選考"],
    "sophie-lane": ["書類選考", "一次面接", "不採用"],
}

# (枠, 人数, 参照ペルソナ, A〜E)。None は求めない軸
REQUISITIONS = [
    ("リード", 1, "L4", [4, 4, None, 3, None]),
    ("開発", 2, "L3", [3, 3, None, 3, 2]),
]


@dataclass(frozen=True)
class DemoPerson:
    email: str
    name: str
    evaluator: str
    role: str
    hiring: bool


def email(name: str) -> str:
    return f"{name}@{DOMAIN}"


def people() -> list[DemoPerson]:
    return [
        DemoPerson(email(n), f"{ANIMALS[n]} {n.replace('-', ' ').title()}", email(EVALUATORS[n]) if n in EVALUATORS else "", "manager" if n in MANAGERS else "member", n in HIRING)
        for n in STAFF
    ]
