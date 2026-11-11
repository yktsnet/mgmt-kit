"""読み込み口の一覧と SQLite を突き合わせ、更新日時が変わったファイルだけを読み直す。"""

import logging
import sqlite3
from dataclasses import dataclass, field

from .hiring import parse_candidate, store_candidate
from .parse import SheetError
from .review import parse_review, store_review
from .sources import FileRef, Source

logger = logging.getLogger(__name__)

CANDIDATES = "candidates/"
REVIEWS = "reviews/"
KINDS = ("candidate", "review")


@dataclass
class SyncResult:
    read: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


def kind_of(ref: FileRef) -> str | None:
    # reviews/<期>/<名前>
    if ref.path.startswith(REVIEWS) and ref.path.count("/") == 2:
        return "review"
    if ref.path.startswith(CANDIDATES):
        return "candidate"
    return None


def sync(source: Source, db: sqlite3.Connection) -> SyncResult:
    result = SyncResult()
    refs = [r for r in source.list() if kind_of(r)]
    # usage の JSON も files に入るので、シートの種類だけを突き合わせる
    known = {
        row["id"]: row["modified"]
        for row in db.execute(f"SELECT id, modified FROM files WHERE kind IN ({','.join('?' * len(KINDS))})", KINDS)
    }
    seen = {r.id for r in refs}

    with db:
        for file_id in known.keys() - seen:
            db.execute("DELETE FROM files WHERE id = ?", (file_id,))
            result.removed.append(file_id)

        # 同じメールの候補者が2ファイルにあると、新しいほうに上書きされた古いほうは候補者の行を持たない。
        # 新しいほうが消えたときに古いほうを読み直せるよう、行を持たない候補者のファイルも読み直す
        stale = {
            row["id"]
            for row in db.execute(
                "SELECT id FROM files WHERE kind = 'candidate' AND error IS NULL "
                "AND id NOT IN (SELECT file_id FROM candidates)"
            )
        }
        # 同じメールの古いほうは毎回読み直すことになるが、重なりは書き間違いなので数は少ない
        changed = sorted(
            (r for r in refs if known.get(r.id) != r.modified or r.id in stale), key=lambda r: r.modified
        )
        for ref in changed:
            try:
                book = source.read(ref)
                _store(db, ref, kind_of(ref), book)
                result.read.append(ref.path)
            except SheetError as e:
                # 1ファイルの書き間違いで全体を止めない。前に読めた値は消して、誤りを画面に出す
                logger.warning("skip %s: %s", ref.path, e)
                _upsert_file(db, ref, kind_of(ref), str(e))
                _clear(db, ref.id)
                result.errors[ref.path] = str(e)
    return result


def _upsert_file(db: sqlite3.Connection, ref: FileRef, kind: str | None, error: str | None) -> None:
    db.execute(
        "INSERT INTO files (id, path, modified, kind, error, modified_by) VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET path = excluded.path, modified = excluded.modified, "
        "kind = excluded.kind, error = excluded.error, modified_by = excluded.modified_by",
        (ref.id, ref.path, ref.modified, kind, error, ref.modified_by or None),
    )


def _clear(db: sqlite3.Connection, file_id: str) -> None:
    db.execute("DELETE FROM candidates WHERE file_id = ?", (file_id,))
    db.execute("DELETE FROM reviews WHERE file_id = ?", (file_id,))


def _store(db: sqlite3.Connection, ref: FileRef, kind: str | None, book) -> None:
    _upsert_file(db, ref, kind, None)
    _clear(db, ref.id)
    if kind == "candidate":
        store_candidate(db, ref.id, ref.modified, parse_candidate(book))
    elif kind == "review":
        store_review(db, ref.id, parse_review(book))

