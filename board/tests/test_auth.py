import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import auth, config
from app.main import create_app

BOARD = Path(__file__).resolve().parent.parent
KEY = b"k" * 32


def make(tmp_path, monkeypatch, **env):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_DB", ":memory:")
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return TestClient(create_app(config.load()))


def test_session_round_trip_and_tamper():
    v = auth.issue(KEY, "a@example.com", now=1000)
    assert auth.verify(KEY, v, now=1001) == "a@example.com"
    assert auth.verify(b"x" * 32, v, now=1001) is None
    assert auth.verify(KEY, v[:-2] + "aa", now=1001) is None
    assert auth.verify(KEY, v, now=1000 + auth.SESSION_TTL + 1) is None


def test_pages_require_login(tmp_path, monkeypatch):
    c = make(tmp_path, monkeypatch)
    r = c.get("/settings", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/login"
    assert c.post("/api/definition/version").status_code == 401


def test_demo_login_and_logout(tmp_path, monkeypatch):
    c = make(tmp_path, monkeypatch)
    assert "Alice Walker" in c.get("/login").text
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    html = c.get("/reviews").text
    assert "Sign out" in html and "Manager" in html
    c.post("/auth/logout")
    assert c.get("/reviews", follow_redirects=False).status_code == 307


def test_demo_login_rejects_unknown_person(tmp_path, monkeypatch):
    c = make(tmp_path, monkeypatch)
    assert c.post("/auth/demo", data={"email": "nobody@example.com"}).status_code == 403


def test_demo_entrance_is_closed_outside_demo(tmp_path, monkeypatch):
    c = make(tmp_path, monkeypatch, BOARD_DEMO="0")
    assert c.post("/auth/demo", data={"email": "alice-walker@example.com"}).status_code == 404
    assert "在籍者から1人を選んで" not in c.get("/login").text


@pytest.mark.parametrize(
    "verified,expect",
    [("alice-walker@example.com", 303), (None, 403), ("stranger@example.com", 403)],
)
def test_google_login(tmp_path, monkeypatch, verified, expect):
    c = make(tmp_path, monkeypatch, BOARD_GOOGLE_CLIENT_ID="cid")
    monkeypatch.setattr(auth, "verify_google", lambda credential, client_id, domain: verified)
    r = c.post("/auth/google", data={"credential": "token"}, follow_redirects=False)
    assert r.status_code == expect


def test_verify_google_checks_workspace_domain(monkeypatch):
    from google.oauth2 import id_token

    claims = {"hd": "example.com", "email_verified": True, "email": "A@example.com"}
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *a, **k: claims)
    assert auth.verify_google("t", "cid", "example.com") == "a@example.com"
    # 個人の Google アカウントには hd が無い
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *a, **k: {**claims, "hd": None})
    assert auth.verify_google("t", "cid", "example.com") is None
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *a, **k: {**claims, "email_verified": False})
    assert auth.verify_google("t", "cid", "example.com") is None
