"""board のウェブアプリ。画面を開いたときに、前に読んでから sync_interval 秒たっていれば読み直す。"""

import datetime as dt
import logging
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, settings as cfg_settings, views
from .ladder import sync_ladder
from .parse import AXES, SheetError
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
        if cfg.db_path != ":memory:":
            Path(cfg.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = connect(cfg.db_path)
        cfg_settings.seed(self.db, cfg.ladder_md, cfg.demo)
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


class ItemKey(BaseModel):
    version: int
    axis: str
    level: int
    key: str


class ItemBody(BaseModel):
    version: int
    axis: str
    level: int
    key: str | None = None
    text: str
    evidence: str = ""


class PersonBody(BaseModel):
    email: str
    evaluator: str | None = None
    role: str | None = None


class RequisitionBody(BaseModel):
    name: str
    count: int
    target: dict[str, int | None]


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
        return RedirectResponse("/reviews")

    @app.get("/reviews", response_class=HTMLResponse)
    def reviews(request: Request, period: str | None = None):
        board.refresh()
        ps = views.periods(board.db)
        if period not in ps:
            period = ps[-1] if ps else None
        return render(request, "reviews", periods=ps, period=period, groups=views.reviews(board.db, period))

    @app.get("/reviews/{period}/{email}", response_class=HTMLResponse)
    def review(request: Request, period: str, email: str):
        board.refresh()
        d = views.review_detail(board.db, period, email)
        if not d:
            raise HTTPException(404)
        return render(request, "review", period=period, **d)

    @app.get("/settings", response_class=HTMLResponse)
    def settings(request: Request, v: int | None = None):
        board.refresh()
        return render(
            request,
            "settings",
            definition=views.definition(board.db, v),
            assignments=views.assignments(board.db),
            people=views.people(board.db),
            requisitions=views.requisitions(board.db),
        )

    def apply(fn, *args):
        """設定を直す。決まりに合わなければ 400 を返す。"""
        try:
            with board.lock:
                result = fn(board.db, *args)
        except SheetError as e:
            return JSONResponse({"error": str(e)}, 400)
        return {"ok": True, "result": result}

    @app.post("/api/definition/item")
    def save_item(body: ItemBody):
        return apply(cfg_settings.save_item, body.version, body.axis, body.level, body.key, body.text, body.evidence)

    @app.post("/api/definition/item/delete")
    def delete_item(body: ItemKey):
        return apply(cfg_settings.delete_item, body.version, body.axis, body.level, body.key)

    @app.post("/api/definition/version")
    def new_version():
        return apply(cfg_settings.new_version)

    @app.post("/api/people")
    def set_person(body: PersonBody):
        return apply(cfg_settings.set_person, body.email, body.evaluator, body.role)

    @app.post("/api/requisitions")
    def set_requisition(body: RequisitionBody):
        return apply(cfg_settings.set_requisition, body.name, body.count, body.target)

    return app
