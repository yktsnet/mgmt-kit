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
    ladder_dir: Path
    personas: Path
    usage_dir: Path
    email_domain: str
    db_path: str
    # この秒数より前に読んでいれば、画面を開いたときに読み直す
    sync_interval: float


def load() -> Config:
    source = os.environ.get("BOARD_SOURCE", "xlsx")
    if source not in ("xlsx", "drive"):
        raise SystemExit(f"BOARD_SOURCE must be xlsx or drive, got {source!r}")
    return Config(
        source=source,
        xlsx_dir=_path("BOARD_XLSX_DIR", BOARD / "samples" / "drive"),
        drive_folder_id=os.environ.get("BOARD_DRIVE_FOLDER_ID", ""),
        service_account_key=os.environ.get("BOARD_SERVICE_ACCOUNT_KEY", ""),
        ladder_dir=_path("BOARD_LADDER_DIR", BOARD / "samples" / "ladder"),
        personas=_path("BOARD_PERSONAS", REPO / "ladder" / "docs" / "personas.md"),
        usage_dir=_path("BOARD_USAGE_DIR", REPO / "usage" / "tools" / "usage" / "claude-code"),
        email_domain=os.environ.get("BOARD_EMAIL_DOMAIN", "example.com"),
        db_path=os.environ.get("BOARD_DB", ":memory:"),
        sync_interval=float(os.environ.get("BOARD_SYNC_INTERVAL", "3" if source == "xlsx" else "60")),
    )
