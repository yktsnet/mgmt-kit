"""シートの読み込み口。Drive の上でも手元のフォルダでも、同じ形で一覧と中身を返す。"""

from dataclasses import dataclass
from typing import Any, Protocol

# シート名 → 行の並び。セルの値は読み込み口ごとの型のまま渡し、解釈は parse に任せる
Book = dict[str, list[list[Any]]]


@dataclass(frozen=True)
class FileRef:
    id: str
    # ルートのフォルダからの相対パス。拡張子は付けない（Drive のスプレッドシートには拡張子が無い）
    path: str
    modified: str


class Source(Protocol):
    def list(self) -> list[FileRef]: ...

    def read(self, ref: FileRef) -> Book: ...

