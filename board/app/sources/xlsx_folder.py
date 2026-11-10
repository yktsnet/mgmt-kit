"""手元のフォルダに置いた .xlsx を読む。デモとテストで Drive の代わりに使う。"""

import datetime as dt
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from . import Book, FileRef


class XlsxFolderSource:
    def __init__(self, root: Path) -> None:
        self.root = root

    def list(self) -> list[FileRef]:
        refs = []
        for p in sorted(self.root.rglob("*.xlsx")):
            # Excel が保存中に作るロックファイル
            if p.name.startswith("~$"):
                continue
            rel = p.relative_to(self.root).with_suffix("").as_posix()
            modified = dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).isoformat()
            refs.append(FileRef(id=str(p), path=rel, modified=modified))
        return refs

    def read(self, ref: FileRef) -> Book:
        wb = load_workbook(ref.id, read_only=True, data_only=True)
        try:
            return {ws.title: [list(row) for row in ws.iter_rows(values_only=True)] for ws in wb.worksheets}
        finally:
            wb.close()

    def write(self, ref: FileRef, sheet: str, rows: list[list[Any]]) -> None:
        wb = load_workbook(ref.id)
        ws = wb[sheet] if sheet in wb.sheetnames else wb.create_sheet(sheet)
        # 入力規則と列の幅は残し、値だけを入れ替える
        if ws.max_row:
            ws.delete_rows(1, ws.max_row)
        for row in rows:
            ws.append(row)
        wb.save(ref.id)
