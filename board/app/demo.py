"""デモの架空の在籍者と採用枠。名前は usage のダミーの名簿と同じにして、usage と突き合わせられるようにする。

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


def email(name: str) -> str:
    return f"{name}@{DOMAIN}"


def people() -> list[DemoPerson]:
    return [
        DemoPerson(email(n), n.replace("-", " ").title(), email(EVALUATORS[n]) if n in EVALUATORS else "", "manager" if n in MANAGERS else "member")
        for n in STAFF
    ]
