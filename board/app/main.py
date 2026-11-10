"""board のウェブアプリ。画面を開いたときに、前に読んでから sync_interval 秒たっていれば読み直す。"""

import datetime as dt
import logging
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, views
from .ladder import sync_ladder
from .parse import AXES
from .sources.xlsx_folder import XlsxFolderSource
from .store import connect
from .sync import sync
from .usage import sync_usage

logger = logging.getLogger(__name__)
HERE = Path(__file__).resolve().parent
AXIS_NAMES = {"A": "上流・提案と関係者調整", "B": "標準化されたワークフローの運用", "C": "ドメイン理解", "D": "検証・品質保証", "E": "インフラ・基盤"}


def make_source(cfg: config.Config):
    if cfg.source == "drive":
        from .sources.drive import DriveSource, service_account_session

        return DriveSource(cfg.drive_folder_id, service_account_session(cfg.service_account_key))
    return XlsxFolderSource(cfg.xlsx_dir)


class Board:
    def __init__(self, cfg: config.Config) -> None:
        self.cfg = cfg
        self.db = connect(cfg.db_path)
        self.source = make_source(cfg)
        self.lock = threading.Lock()
        self.synced_at = 0.0
        self.synced_label = ""

    def refresh(self, force: bool = False) -> None:
        with self.lock:
            if not force and time.monotonic() - self.synced_at < self.cfg.sync_interval:
                return
            try:
                sync(self.source, self.db)
                sync_ladder(self.cfg.ladder_dir, self.cfg.personas, self.cfg.email_domain, self.db)
                sync_usage(self.cfg.usage_dir, self.db)
            except Exception:
                # 読み込み口が一時的に落ちても、前に読めた値で画面を出す
                logger.exception("sync failed")
            self.synced_at = time.monotonic()
            self.synced_label = dt.datetime.now().strftime("%H:%M:%S")


def create_app(cfg: config.Config | None = None) -> FastAPI:
    board = Board(cfg or config.load())
    app = FastAPI(title="board", docs_url=None, redoc_url=None)
    app.state.board = board
    app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
    templates = Jinja2Templates(directory=HERE / "templates")
    templates.env.globals.update(AXES=AXES, AXIS_NAMES=AXIS_NAMES)

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        ctx.update(
            errors=views.errors(board.db),
            synced=board.synced_label,
            source="Drive" if board.cfg.source == "drive" else "手元のフォルダ",
            page=name,
        )
        return templates.TemplateResponse(request, f"{name}.html", ctx)

    @app.get("/")
    def home():
        # 評価のタブができるまでは設定を入口にする
        return RedirectResponse("/settings")

    @app.get("/settings", response_class=HTMLResponse)
    def settings(request: Request, v: int | None = None):
        board.refresh()
        return render(
            request,
            "settings",
            definition=views.definition(board.db, v),
            assignments=views.assignments(board.db),
            requisitions=views.requisitions(board.db),
        )

    return app
