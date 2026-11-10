"""DriveSource を、Drive API と Sheets API の応答の形を真似た偽のセッションで確かめる。"""

from app.parse import parse_candidate
from app.sources.drive import FOLDER, SPREADSHEET, DriveSource
from app.store import connect
from app.sync import sync


class Response:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self.body


def cell(v=None, date=False):
    if v is None:
        return {}
    c = {"effectiveValue": {"numberValue": v} if isinstance(v, (int, float)) else {"stringValue": v}}
    if date:
        c["effectiveFormat"] = {"numberFormat": {"type": "DATE"}}
    return c


def grid(title, rows):
    return {"properties": {"title": title}, "data": [{"rowData": [{"values": r} for r in rows]}]}


CANDIDATE = {
    "sheets": [
        grid("候補者", [
            [cell("氏名"), cell("Ada")],
            [cell("メール"), cell("ada@example.com")],
            [cell("段階"), cell("一次面接")],
            [cell("応募日"), cell(46083, date=True)],
        ]),
        grid("面接", [
            [cell("日付"), cell("A"), cell("B")],
            [cell(46090, date=True), cell(3), {}],
        ]),
    ]
}


class FakeSession:
    def __init__(self, modified="2026-04-01T00:00:00Z"):
        self.modified = modified
        self.calls = []

    def get(self, url, params: dict | None = None):
        params = params or {}
        self.calls.append((url, params))
        if "drive/v3" in url:
            q = params["q"]
            if "'root'" in q:
                # 1ページ目と2ページ目に分けて、ページ送りを通す
                if "pageToken" not in params:
                    return Response({"files": [{"id": "f1", "name": "candidates", "mimeType": FOLDER, "modifiedTime": "x"}], "nextPageToken": "p2"})
                return Response({"files": [{"id": "doc", "name": "memo", "mimeType": "application/vnd.google-apps.document", "modifiedTime": "x"}]})
            if "'f1'" in q:
                return Response({"files": [{"id": "s1", "name": "ada", "mimeType": SPREADSHEET, "modifiedTime": self.modified}]})
        if "sheets.googleapis.com" in url:
            return Response(CANDIDATE)
        raise AssertionError(url)


def test_lists_spreadsheets_in_subfolders_across_pages():
    refs = DriveSource("root", FakeSession()).list()
    assert [(r.id, r.path) for r in refs] == [("s1", "candidates/ada")]


def test_reads_grid_into_candidate():
    src = DriveSource("root", FakeSession())
    c = parse_candidate(src.read(src.list()[0]))
    assert (c.email, c.stage, c.applied.isoformat()) == ("ada@example.com", "一次面接", "2026-03-02")
    assert c.scores() == {"A": 3}


def test_sync_rereads_only_when_modified_time_changes():
    session = FakeSession()
    db = connect(":memory:")
    src = DriveSource("root", session)
    assert sync(src, db).read == ["candidates/ada"]
    assert sync(src, db).read == []
    session.modified = "2026-04-02T00:00:00Z"
    assert sync(src, db).read == ["candidates/ada"]
