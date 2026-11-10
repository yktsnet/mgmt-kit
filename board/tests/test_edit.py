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
    c.get("/settings")
    return c


def rows(path: Path, sheet: str) -> list[list]:
    return [list(r) for r in load_workbook(path)[sheet].iter_rows(values_only=True)]


def test_edit_item_writes_back_to_sheet(client):
    r = client.post("/api/definition/item", json={"version": 1, "axis": "A", "level": 3, "key": "a", "text": "直した判定文。", "evidence": "設計資料"})
    assert r.status_code == 200, r.text
    sheet = rows(client.drive / "settings" / "definition.xlsx", "v1")
    assert ["A", "L3", "a", "直した判定文。", "設計資料"] in sheet
    assert "直した判定文。" in client.get("/settings").text


def test_add_item_takes_next_key_and_delete_removes_it(client):
    client.post("/api/definition/item", json={"version": 1, "axis": "A", "level": 3, "text": "足した細目。"})
    sheet = rows(client.drive / "settings" / "definition.xlsx", "v1")
    added = [r for r in sheet if r[:2] == ["A", "L3"] and r[3] == "足した細目。"]
    assert added and added[0][2] == "c"
    client.post("/api/definition/item/delete", json={"version": 1, "axis": "A", "level": 3, "key": "c"})
    assert not any(r[3] == "足した細目。" for r in rows(client.drive / "settings" / "definition.xlsx", "v1"))


def test_deleting_the_last_item_of_a_cell_is_refused(client):
    r = client.post("/api/definition/item/delete", json={"version": 1, "axis": "C", "level": 2, "key": "a"})
    assert r.status_code == 400
    assert "C-L2" in r.json()["error"]


def test_new_version_copies_latest(client):
    r = client.post("/api/definition/version")
    assert r.json()["result"] == 2
    wb = load_workbook(client.drive / "settings" / "definition.xlsx")
    assert wb.sheetnames[-2:] == ["v1", "v2"] or {"v1", "v2"} <= set(wb.sheetnames)
    assert "v2" in client.get("/settings").text


def test_change_evaluator(client):
    r = client.post("/api/people/evaluator", json={"email": "jack-foster@example.com", "evaluator": "alice-walker@example.com"})
    assert r.status_code == 200, r.text
    sheet = rows(client.drive / "settings" / "people.xlsx", "在籍者")
    assert ["jack-foster@example.com", "Jack Foster", "alice-walker@example.com"] in sheet


def test_self_evaluator_is_refused(client):
    r = client.post("/api/people/evaluator", json={"email": "jack-foster@example.com", "evaluator": "jack-foster@example.com"})
    assert r.status_code == 400


def test_set_requisition(client):
    r = client.post("/api/requisitions", json={"name": "開発", "count": 3, "target": {"A": 3, "B": 4, "C": None, "D": 3, "E": None}})
    assert r.status_code == 200, r.text
    sheet = rows(client.drive / "settings" / "requisitions.xlsx", "求める人材")
    assert ["開発", 3, "L3", 3, 4, None, 3, None] in sheet


def test_out_of_range_target_is_refused(client):
    r = client.post("/api/requisitions", json={"name": "開発", "count": 1, "target": {"A": 9}})
    assert r.status_code == 400


def test_sheet_changed_elsewhere_is_a_conflict(client):
    path = client.drive / "settings" / "people.xlsx"
    t = time.time() + 30
    os.utime(path, (t, t))
    r = client.post("/api/people/evaluator", json={"email": "jack-foster@example.com", "evaluator": ""})
    assert r.status_code == 409
