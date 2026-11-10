"""在籍者の名簿と、評価する担当（Reviewer）の割り当て。アプリが持ち、parse_people は行の形で受けた名簿を確かめるのに使う。"""

import sqlite3
from dataclasses import dataclass

from .parse import SheetError, _sheet, _table, _text
from .sources import Book

PEOPLE_HEADER = ["メール", "氏名", "担当"]


@dataclass(frozen=True)
class Person:
    email: str
    name: str
    # 評価する担当のメール。空なら未割り当て
    evaluator: str


def parse_people(book: Book) -> list[Person]:
    people: list[Person] = []
    for i, r in enumerate(_table(_sheet(book, "在籍者")), start=2):
        email = _text(r.get("メール")).lower()
        if not email:
            continue
        if any(p.email == email for p in people):
            raise SheetError(f"在籍者 row {i}: duplicate メール {email!r}")
        people.append(Person(email, _text(r.get("氏名")) or email.split("@")[0], _text(r.get("担当")).lower()))
    known = {p.email for p in people}
    for p in people:
        if p.evaluator == p.email:
            raise SheetError(f"在籍者 {p.email}: 担当 must be someone else")
        if p.evaluator and p.evaluator not in known:
            raise SheetError(f"在籍者 {p.email}: 担当 {p.evaluator!r} is not in 在籍者")
    return people
