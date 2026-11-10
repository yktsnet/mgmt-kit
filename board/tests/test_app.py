import os
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import config
from app.main import create_app

BOARD = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    drive = tmp_path / "drive"
    shutil.copytree(BOARD / "samples" / "drive", drive)
    monkeypatch.setenv("BOARD_XLSX_DIR", str(drive))
    monkeypatch.setenv("BOARD_SYNC_INTERVAL", "0")
    c = TestClient(create_app(config.load()))
    c.drive = drive
    return c


def save_later(wb, path):
    wb.save(path)
    t = time.time() + 10
    os.utime(path, (t, t))




def test_settings_shows_definition_assignments_and_requisitions(client):
    html = client.get("/settings").text
    assert "性能・運用・移行の欠落を要件に対して指摘できる。" in html
    assert "Unassigned" in html and "Alice Walker" in html
    assert "リード" in html
    # 読む表示と編集の部品は、区画の Edit で切り替える
    assert 'data-action="edit"' in html and 'class="btn link add edit-only"' in html


def test_new_version_is_shown_and_old_one_is_reachable(client):
    path = client.drive / "settings" / "definition.xlsx"
    wb = load_workbook(path)
    v2 = wb.copy_worksheet(wb["v1"])
    v2.title = "v2"
    v2.append(["A", "L3", "c", "v2 で足した細目。", ""])
    save_later(wb, path)
    assert "v2 で足した細目。" in client.get("/settings").text
    assert "v2 で足した細目。" not in client.get("/settings?v=1").text


def test_bad_assignment_is_shown_as_error(client):
    path = client.drive / "settings" / "people.xlsx"
    wb = load_workbook(path)
    wb["在籍者"]["C3"] = "nobody@example.com"
    save_later(wb, path)
    html = client.get("/settings").text
    assert "読めなかったファイル" in html and "settings/people" in html
