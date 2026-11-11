"""環境変数から設定を読む。何も設定しなければ、リポに同梱したダミーで動く。"""

import os
from dataclasses import dataclass
from pathlib import Path

BOARD = Path(__file__).resolve().parent.parent
REPO = BOARD.parent


def _path(name: str, default: Path) -> Path:
    v = os.environ.get(name)
    return Path(v) if v else default


@dataclass(frozen=True)
class Config:
    source: str
    xlsx_dir: Path
    drive_folder_id: str
    service_account_key: str
    usage_dir: Path
    db_path: str
    # 設定が空のときに、デモの在籍者と採用枠を入れる
    demo: bool
    ladder_md: Path
    google_client_id: str
    allowed_domain: str
    session_key: bytes
    # この秒数より前に読んでいれば、画面を開いたときに読み直す
    sync_interval: float


def _session_key() -> bytes:
    key = os.environ.get("BOARD_SESSION_KEY", "")
    if key:
        return key.encode()
    # 鍵を設定しないと、起動のたびにログインの状態が切れる。デモではそれで困らない
    return os.urandom(32)


def load() -> Config:
    source = os.environ.get("BOARD_SOURCE", "xlsx")
    if source not in ("xlsx", "drive"):
        raise SystemExit(f"BOARD_SOURCE must be xlsx or drive, got {source!r}")
    return Config(
        source=source,
        xlsx_dir=_path("BOARD_XLSX_DIR", BOARD / "samples" / "drive"),
        drive_folder_id=os.environ.get("BOARD_DRIVE_FOLDER_ID", ""),
        service_account_key=os.environ.get("BOARD_SERVICE_ACCOUNT_KEY", ""),
        usage_dir=_path("BOARD_USAGE_DIR", REPO / "usage" / "tools" / "usage" / "claude-code"),
        # 設定はアプリが持つので、DB はファイルに置いて残す
        db_path=os.environ.get("BOARD_DB", str(BOARD / "data" / "board.db")),
        demo=os.environ.get("BOARD_DEMO", "1" if source == "xlsx" else "0") == "1",
        ladder_md=_path("BOARD_LADDER_MD", REPO / "ladder" / "docs" / "ladder.md"),
        google_client_id=os.environ.get("BOARD_GOOGLE_CLIENT_ID", ""),
        allowed_domain=os.environ.get("BOARD_ALLOWED_DOMAIN", "example.com").lower(),
        session_key=_session_key(),
        sync_interval=float(os.environ.get("BOARD_SYNC_INTERVAL", "3" if source == "xlsx" else "60")),
    )
