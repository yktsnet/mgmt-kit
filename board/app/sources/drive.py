"""Drive のフォルダにあるスプレッドシートを、Drive API と Sheets API で読む。

認証はサービスアカウントで行い、読むフォルダをそのアカウントに共有しておく。
ログインした人の権限では読まない。
"""

from typing import Any

from . import Book, FileRef

DRIVE = "https://www.googleapis.com/drive/v3/files"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
FOLDER = "application/vnd.google-apps.folder"
SPREADSHEET = "application/vnd.google-apps.spreadsheet"
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def service_account_session(key_file: str) -> Any:
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
    return AuthorizedSession(creds)


class DriveSource:
    def __init__(self, folder_id: str, session: Any) -> None:
        self.folder_id = folder_id
        self.session = session

    def _children(self, folder_id: str) -> list[dict]:
        files, token = [], None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, lastModifyingUser(displayName))",
                "pageSize": 1000,
                # 共有ドライブに置いたフォルダも読む
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if token:
                params["pageToken"] = token
            res = self.session.get(DRIVE, params=params)
            res.raise_for_status()
            body = res.json()
            files += body.get("files", [])
            token = body.get("nextPageToken")
            if not token:
                return files

    def list(self) -> list[FileRef]:
        refs, stack = [], [(self.folder_id, "")]
        while stack:
            folder, prefix = stack.pop()
            for f in self._children(folder):
                path = f"{prefix}{f['name']}"
                if f["mimeType"] == FOLDER:
                    stack.append((f["id"], f"{path}/"))
                elif f["mimeType"] == SPREADSHEET:
                    refs.append(FileRef(id=f["id"], path=path, modified=f["modifiedTime"], modified_by=f.get("lastModifyingUser", {}).get("displayName", "")))
        return sorted(refs, key=lambda r: r.path)

    def read(self, ref: FileRef) -> Book:
        res = self.session.get(
            f"{SHEETS}/{ref.id}",
            params={
                "includeGridData": "true",
                "fields": "sheets(properties(title),data(rowData(values(effectiveValue,effectiveFormat(numberFormat(type))))))",
            },
        )
        res.raise_for_status()
        return {s["properties"]["title"]: _rows(s) for s in res.json().get("sheets", [])}


def _rows(sheet: dict) -> list[list[Any]]:
    rows = []
    for data in sheet.get("data", []):
        for row in data.get("rowData", []):
            rows.append([_cell(c) for c in row.get("values", [])])
    return rows


def _cell(cell: dict) -> Any:
    value = cell.get("effectiveValue")
    if not value:
        return None
    if "numberValue" in value:
        n = value["numberValue"]
        # 日付は数値（1899-12-30 からの日数）で返るので、書式の型で見分けて parse に渡す
        if cell.get("effectiveFormat", {}).get("numberFormat", {}).get("type") in ("DATE", "DATE_TIME"):
            return {"serial_date": n}
        return int(n) if float(n).is_integer() else n
    for key in ("stringValue", "boolValue"):
        if key in value:
            return value[key]
    return None
