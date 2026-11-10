import pytest

from app.parse import SheetError
from app.people import parse_people

H = ["メール", "氏名", "担当"]


def book(*rows):
    return {"在籍者": [H, *rows]}


def test_people_and_evaluators():
    people = parse_people(book(["A@x.com", "A", ""], ["b@x.com", "", "a@x.com"]))
    assert [(p.email, p.name, p.evaluator) for p in people] == [("a@x.com", "A", ""), ("b@x.com", "b", "a@x.com")]


@pytest.mark.parametrize(
    "rows,msg",
    [
        ([["a@x.com", "A", ""], ["a@x.com", "A2", ""]], "duplicate"),
        ([["a@x.com", "A", "a@x.com"]], "someone else"),
        ([["a@x.com", "A", "z@x.com"]], "not in"),
    ],
)
def test_bad_people(rows, msg):
    with pytest.raises(SheetError, match=msg):
        parse_people(book(*rows))
