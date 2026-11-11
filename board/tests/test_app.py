import os
import re
import shutil
import socket
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app

BOARD = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    monkeypatch.setenv("BOARD_DB", ":memory:")
    c = TestClient(create_app(config.load()))
    c.post("/auth/demo", data={"email": "alice-walker@example.com"})
    c.drive = drive
    return c





def test_settings_shows_definition_assignments_and_requisitions(client):
    html = client.get("/settings").text
    assert "性能・運用・移行の欠落を要件に対して指摘できる。" in html
    assert "Unassigned" in html and "Alice Walker" in html
    assert "リード" in html
    # 読む表示と編集の部品は、区画の Edit で切り替える
    assert 'data-action="edit"' in html and 'class="btn link add edit-only"' in html


def test_version_used_by_reviews_is_locked_until_new_version(client):
    html = client.get("/settings").text
    assert "評価か面接に使われている版" in html
    assert client.post("/api/definition/item", json={"version": 1, "axis": "A", "level": 3, "key": "a", "text": "x"}).status_code == 400
    assert client.post("/api/definition/version").json()["result"] == 2
    r = client.post("/api/definition/item", json={"version": 2, "axis": "A", "level": 3, "key": "a", "text": "v2 で直した細目。"})
    assert r.status_code == 200, r.text
    assert "v2 で直した細目。" in client.get("/settings").text
    assert "v2 で直した細目。" not in client.get("/settings?v=1").text


def test_role_and_reviewer_change(client):
    assert client.post("/api/people", json={"email": "jack-foster@example.com", "role": "manager"}).status_code == 200
    assert client.post("/api/people", json={"email": "jack-foster@example.com", "evaluator": "alice-walker@example.com"}).status_code == 200
    html = client.get("/settings").text
    assert "Manager" in html
    assert client.post("/api/people", json={"email": "jack-foster@example.com", "evaluator": "jack-foster@example.com"}).status_code == 400


# ---- 画面の中身と幅


def test_demo_login_lists_people_with_roles_and_tabs(client):
    client.post("/auth/logout")
    html = client.get("/login").text
    body = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    text = lambda c: " ".join(re.sub(r"<[^>]+>", " ", c).split())  # noqa: E731
    rows = [[text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)] for tr in re.findall(r"<tr>(.*?)</tr>", body, re.S)]
    assert len(rows) == 10
    assert rows[0] == ["🐊 Alice Walker", "Manager", "評価・現在地・採用・設定", "全員（評価を Approve できる）"]
    assert rows[1] == ["🐘 Emma Hughes", "Hiring", "評価・現在地・採用", "🐱 Chloe Evans 🦊 Felix Grant 🦒 Grace Turner"]
    assert rows[2] == ["🐻 Ben Carter", "Member", "現在地", "-"]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """幅を確かめるため、デモを本物のポートで立てる。"""
    uvicorn = pytest.importorskip("uvicorn")
    tmp = tmp_path_factory.mktemp("widths")
    shutil.copytree(BOARD / "samples" / "drive", tmp / "drive")
    env = {"BOARD_XLSX_DIR": str(tmp / "drive"), "BOARD_SYNC_INTERVAL": "0", "BOARD_DB": str(tmp / "board.db")}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        app = create_app(config.load())
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    while not srv.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join()


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # ブラウザを入れていない環境では確かめられない
            pytest.skip(f"chromium is not available: {e}")
        yield b
        b.close()


WIDTHS = {1440: 900, 2560: 1440, 390: 844}
# (ログインする人, 画面)。None はログインしない
SCREENS = [
    (None, "/login"),
    ("alice-walker", "/reviews"),
    ("alice-walker", "/reviews/2026-H2/emma-hughes@example.com"),
    ("alice-walker", "/now"),
    ("alice-walker", "/now/emma-hughes@example.com"),
    ("henry-ward", "/now"),
    ("alice-walker", "/hiring"),
    ("alice-walker", "/hiring/liam-price@example.com"),
]


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("who,path", SCREENS)
def test_no_horizontal_scroll(server, browser, who, path, width):
    ctx = browser.new_context(viewport={"width": width, "height": WIDTHS[width]})
    if who:
        ctx.request.post(server + "/auth/demo", form={"email": f"{who}@example.com"}, max_redirects=0)
    page = ctx.new_page()
    page.goto(server + path)
    sw, iw = page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
    ctx.close()
    assert sw <= iw


@pytest.mark.parametrize("path", ["/reviews", "/now"])
def test_wide_screen_stops_at_max_width_with_even_margins(server, browser, path):
    ctx = browser.new_context(viewport={"width": 2560, "height": 1440})
    ctx.request.post(server + "/auth/demo", form={"email": "alice-walker@example.com"}, max_redirects=0)
    page = ctx.new_page()
    page.goto(server + path)
    left, right, width = page.evaluate("(() => { const r = document.querySelector('.wrap').getBoundingClientRect(); return [r.left, innerWidth - r.right, r.width]; })()")
    ctx.close()
    assert width == 1920 and left == right == 320


def test_narrow_now_stacks_charts_with_readable_text(server, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.request.post(server + "/auth/demo", form={"email": "alice-walker@example.com"}, max_redirects=0)
    page = ctx.new_page()
    page.goto(server + "/now")
    tops, smallest = page.evaluate("""(() => {
      const charts = [...document.querySelectorAll('.pair > .frame')].map(f => f.getBoundingClientRect());
      const sizes = [...document.querySelectorAll('.chart svg text')].map(t => parseFloat(getComputedStyle(t).fontSize) * t.getScreenCTM().a);
      return [charts.map(r => [r.top, r.bottom, r.left]), Math.min(...sizes)];
    })()""")
    ctx.close()
    (t1, b1, l1), (t2, _, l2) = tops
    assert t2 >= b1 and l1 == l2
    assert smallest >= 12


def test_narrow_hiring_keeps_name_stage_and_axes_visible(server, browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.request.post(server + "/auth/demo", form={"email": "alice-walker@example.com"}, max_redirects=0)
    page = ctx.new_page()
    page.goto(server + "/hiring")
    clipped = page.evaluate("""(() => [...document.querySelectorAll('table.roster.hiring tbody tr:not(.target)')].flatMap(tr =>
      [...tr.querySelectorAll('td')].filter(td => getComputedStyle(td).display !== 'none').map(td => {
        const r = td.getBoundingClientRect(), box = td.closest('.scroll').getBoundingClientRect();
        return (r.right > box.right + 0.5 || td.scrollWidth > td.clientWidth) ? tr.querySelector('td').innerText + ':' + td.innerText : null;
      }).filter(Boolean)))()""")
    shown = page.evaluate("[...document.querySelector('table.roster.hiring thead tr').children].filter(th => getComputedStyle(th).display !== 'none').map(th => th.innerText)")
    ctx.close()
    assert shown == ["Candidate", "Stage", "A", "B", "C", "D", "E"]
    assert clipped == []


@pytest.mark.parametrize("path", ["/reviews/2026-H2/emma-hughes@example.com", "/hiring/liam-price@example.com"])
def test_narrow_items_wrap_within_screen(server, browser, path):
    ctx = browser.new_context(viewport={"width": 390, "height": 844})
    ctx.request.post(server + "/auth/demo", form={"email": "alice-walker@example.com"}, max_redirects=0)
    page = ctx.new_page()
    page.goto(server + path)
    count, outside = page.evaluate("""(() => {
      const items = [...document.querySelectorAll('table.grid .item')];
      return [items.length, items.filter(i => { const r = i.getBoundingClientRect(); return r.left < 0 || r.right > innerWidth; }).length];
    })()""")
    ctx.close()
    assert count > 0 and outside == 0
