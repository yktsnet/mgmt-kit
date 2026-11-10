"""役割と担当の組み合わせごとに、見られる・見られないを確かめる。

デモの在籍者：alice-walker は Manager。emma-hughes は chloe-evans・felix-grant・grace-turner の Reviewer で、採用を見られる。
grace-turner は誰の Reviewer でもなく、採用を見られる。ben-carter は誰の Reviewer でもなく、採用を見られない。
"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app

BOARD = Path(__file__).resolve().parent.parent
P = "2026-H2"


@pytest.fixture
def app(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    return create_app(config.load())


def login(app, name: str) -> TestClient:
    c = TestClient(app)
    c.post("/auth/demo", data={"email": f"{name}@example.com"})
    return c


def review(name: str) -> str:
    return f"/reviews/{P}/{name}@example.com"


def approve_grace(app):
    base = f"/api/reviews/{P}/grace-turner@example.com/action"
    assert login(app, "emma-hughes").post(base, json={"action": "submit"}).status_code == 200
    assert login(app, "alice-walker").post(base, json={"action": "approve"}).status_code == 200


# ---- 評価の1人のページ


@pytest.mark.parametrize(
    "viewer,subject,status",
    [
        ("alice-walker", "grace-turner", 200),  # Manager はすべて
        ("alice-walker", "ben-carter", 200),
        ("emma-hughes", "grace-turner", 200),  # 担当する人
        ("emma-hughes", "ben-carter", 403),  # 担当しない人
        ("grace-turner", "grace-turner", 403),  # 自分の評価は Approved まで見られない
        ("ben-carter", "grace-turner", 403),
    ],
)
def test_review_page(app, viewer, subject, status):
    assert login(app, viewer).get(review(subject)).status_code == status


def test_own_review_is_visible_once_approved_without_records(app):
    approve_grace(app)
    html = login(app, "grace-turner").get(review("grace-turner")).text
    assert 'id="record"' not in html
    assert 'id="record"' in login(app, "emma-hughes").get(review("grace-turner")).text


def test_reopened_review_is_hidden_from_self_again(app):
    approve_grace(app)
    login(app, "alice-walker").post(f"/api/reviews/{P}/grace-turner@example.com/action", json={"action": "reopen"})
    assert login(app, "grace-turner").get(review("grace-turner")).status_code == 403


# ---- 評価の一覧


def links(html: str) -> set[str]:
    return {n for n in ("ben-carter", "chloe-evans", "grace-turner", "emma-hughes", "henry-ward") if f"{n}@example.com" in html}


def test_review_list_is_narrowed(app):
    assert links(login(app, "alice-walker").get("/reviews").text) == {"ben-carter", "chloe-evans", "grace-turner", "emma-hughes", "henry-ward"}
    assert links(login(app, "emma-hughes").get("/reviews").text) == {"chloe-evans", "grace-turner"}
    assert links(login(app, "ben-carter").get("/reviews").text) == set()
    approve_grace(app)
    assert links(login(app, "grace-turner").get("/reviews").text) == {"grace-turner"}


def test_unassigned_group_only_for_manager(app):
    assert "Reviewer 未割り当て" in login(app, "alice-walker").get("/reviews").text
    assert "Reviewer 未割り当て" not in login(app, "emma-hughes").get("/reviews").text


# ---- 評価の API


@pytest.mark.parametrize(
    "viewer,subject,status",
    [
        ("alice-walker", "ben-carter", 200),
        ("emma-hughes", "grace-turner", 200),
        ("emma-hughes", "ben-carter", 403),
        ("grace-turner", "grace-turner", 403),  # 本人は記録に書けない
    ],
)
def test_memo_api(app, viewer, subject, status):
    r = login(app, viewer).post(f"/api/reviews/{P}/{subject}@example.com/memo", json={"body": "x"})
    assert r.status_code == status


def test_action_api_refuses_people_who_cannot_see(app):
    r = login(app, "ben-carter").post(f"/api/reviews/{P}/grace-turner@example.com/action", json={"action": "submit"})
    assert r.status_code == 403


def test_growth_api_refuses_member_who_does_not_review(app):
    r = login(app, "ben-carter").post(f"/api/growth/{P}/grace-turner@example.com", json={"axis": "A"})
    assert r.status_code == 400


# ---- 現在地


def now_rows(html: str) -> set[str]:
    return {n for n in ("alice-walker", "ben-carter", "chloe-evans", "grace-turner", "emma-hughes", "henry-ward") if f'data-person="{n}@example.com"' in html}


def test_now_rows_are_narrowed(app):
    assert len(now_rows(login(app, "alice-walker").get("/now").text)) == 6
    assert now_rows(login(app, "emma-hughes").get("/now").text) == {"emma-hughes", "chloe-evans", "grace-turner"}
    assert now_rows(login(app, "ben-carter").get("/now").text) == {"ben-carter"}


def test_usage_tables_on_now_are_narrowed(app):
    html = login(app, "ben-carter").get("/now").text
    assert 'href="/now/ben-carter@example.com"' in html
    assert 'href="/now/emma-hughes@example.com"' not in html


def test_own_level_on_now_waits_for_approval(app):
    c = login(app, "grace-turner")
    assert 'href="/reviews/2026-H2/grace-turner@example.com"' not in c.get("/now").text
    approve_grace(app)
    assert 'href="/reviews/2026-H2/grace-turner@example.com"' in c.get("/now").text


@pytest.mark.parametrize(
    "viewer,subject,status",
    [
        ("alice-walker", "ben-carter", 200),
        ("emma-hughes", "grace-turner", 200),
        ("emma-hughes", "ben-carter", 403),
        ("ben-carter", "ben-carter", 200),
    ],
)
def test_now_member_page(app, viewer, subject, status):
    assert login(app, viewer).get(f"/now/{subject}@example.com").status_code == status


# ---- 採用


@pytest.mark.parametrize("viewer,status", [("alice-walker", 200), ("emma-hughes", 200), ("grace-turner", 200), ("ben-carter", 403)])
def test_hiring_pages(app, viewer, status):
    c = login(app, viewer)
    assert c.get("/hiring").status_code == status
    assert c.get("/hiring/liam-price@example.com").status_code == status
    r = c.post("/api/hiring/noah-reed@example.com/stage", json={"stage": "最終面接"})
    assert r.status_code == status
    assert c.post("/api/hiring/noah-reed@example.com/memo", json={"body": "x"}).status_code == status


def test_hiring_tab_shows_only_for_those_who_can_see(app):
    assert 'href="/hiring"' in login(app, "grace-turner").get("/reviews").text
    assert 'href="/hiring"' not in login(app, "ben-carter").get("/reviews").text


def test_hiring_flag_is_set_in_settings(app):
    ben = login(app, "ben-carter")
    assert ben.get("/hiring").status_code == 403
    assert login(app, "alice-walker").post("/api/people", json={"email": "ben-carter@example.com", "hiring": True}).status_code == 200
    assert ben.get("/hiring").status_code == 200


# ---- 設定


@pytest.mark.parametrize(
    "url,body",
    [
        ("/api/people", {"email": "ben-carter@example.com", "hiring": True}),
        ("/api/requisitions", {"name": "開発", "count": 3, "target": {"A": 3}}),
        ("/api/definition/version", {}),
        ("/api/definition/item", {"version": 1, "axis": "A", "level": 3, "key": "a", "text": "x"}),
        ("/api/definition/item/delete", {"version": 1, "axis": "A", "level": 3, "key": "a"}),
    ],
)
def test_settings_api_is_manager_only(app, url, body):
    assert login(app, "emma-hughes").post(url, json=body).status_code == 403


def test_settings_page_has_no_edit_for_member(app):
    assert 'data-action="edit"' not in login(app, "emma-hughes").get("/settings").text
    assert 'data-action="edit"' in login(app, "alice-walker").get("/settings").text
