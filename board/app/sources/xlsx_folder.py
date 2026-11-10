"""手元のフォルダに置いた .xlsx を読む。デモとテストで Drive の代わりに使う。"""

import datetime as dt
from pathlib import Path

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
