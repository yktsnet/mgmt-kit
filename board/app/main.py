"""board のウェブアプリ。画面を開いたときに、前に読んでから sync_interval 秒たっていれば読み直す。"""

import datetime as dt
import logging
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import access, auth, config, hiring, settings as cfg_settings, usage_report, views, workflow
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


def _when(iso: str | None) -> str:
    """UTC の ISO 形式を、手元の時刻の「11/10 23:20」にする。"""
    if not iso:
        return ""
    try:
        return dt.datetime.fromisoformat(iso).astimezone().strftime("%m/%d %H:%M")
    except ValueError:
        return iso


class ActionBody(BaseModel):
    action: str


class AxisBody(BaseModel):
    axis: str


class MemoBody(BaseModel):
    body: str


class PersonBody(BaseModel):
    email: str
    evaluator: str | None = None
    role: str | None = None
    hiring: bool | None = None


class StageBody(BaseModel):
    stage: str


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
    templates.env.filters["when"] = _when

    def current_user(request: Request):
        email = auth.verify(board.cfg.session_key, request.cookies.get(auth.COOKIE))
        if not email:
            return None
        return board.db.execute("SELECT * FROM people WHERE email = ?", (email,)).fetchone()

    @app.middleware("http")
    async def require_login(request: Request, call_next):
        path = request.url.path
        if path.startswith(("/static/", "/login", "/auth/")) or current_user(request):
            return await call_next(request)
        if path.startswith("/api/"):
            return JSONResponse({"error": "ログインしてください"}, 401)
        return RedirectResponse("/login")

    def login_page(request: Request, error: str = ""):
        people = []
        if board.cfg.demo:
            # デモでは、入る前に誰が何を見られるかが分かるようにする
            for p in board.db.execute("SELECT * FROM people ORDER BY rowid").fetchall():
                reviewees = [r[0] for r in board.db.execute("SELECT name FROM people WHERE evaluator = ? ORDER BY rowid", (p["email"],))]
                tabs = ["評価" if access.has_reviews(board.db, p) else None, "現在地", "採用" if access.can_hire(p) else None,
                        "設定" if access.is_manager(p) else None]
                people.append({"email": p["email"], "name": p["name"], "role": p["role"], "hiring": access.can_hire(p),
                               "reviewees": reviewees, "tabs": [t for t in tabs if t]})
        return templates.TemplateResponse(
            request, "login.html",
            {"demo": board.cfg.demo, "people": people, "client_id": board.cfg.google_client_id, "domain": board.cfg.allowed_domain, "error": error},
            status_code=403 if error else 200,
        )

    def signed_in(email: str):
        res = RedirectResponse("/", status_code=303)
        # デモは http で開くので Secure を付けない
        res.set_cookie(auth.COOKIE, auth.issue(board.cfg.session_key, email), max_age=auth.SESSION_TTL, httponly=True, samesite="lax", secure=not board.cfg.demo)
        return res

    def known(email: str) -> bool:
        return board.db.execute("SELECT 1 FROM people WHERE email = ?", (email,)).fetchone() is not None

    @app.get("/login", response_class=HTMLResponse)
    def login(request: Request):
        return login_page(request)

    @app.post("/auth/google")
    def auth_google(request: Request, credential: str = Form(...)):
        if not board.cfg.google_client_id:
            raise HTTPException(404)
        email = auth.verify_google(credential, board.cfg.google_client_id, board.cfg.allowed_domain)
        if not email:
            return login_page(request, f"@{board.cfg.allowed_domain} の Google Workspace のアカウントでログインしてください")
        if not known(email):
            return login_page(request, f"{email} は在籍者にいません。設定の在籍者に足してもらってください")
        return signed_in(email)

    @app.post("/auth/demo")
    def auth_demo(request: Request, email: str = Form(...)):
        # デモのときだけ開く入口。Google を通らない
        if not board.cfg.demo:
            raise HTTPException(404)
        if not known(email):
            return login_page(request, "在籍者にいない人は選べません")
        return signed_in(email)

    @app.post("/auth/logout")
    def logout():
        res = RedirectResponse("/login", status_code=303)
        res.delete_cookie(auth.COOKIE)
        return res

    def render(request: Request, name: str, **ctx) -> HTMLResponse:
        me = current_user(request)
        ctx.update(
            me=me,
            can_hire=access.can_hire(me),
            has_reviews=access.has_reviews(board.db, me),
            errors=views.errors(board.db),
            synced=board.synced_label,
            source="Drive" if board.cfg.source == "drive" else "手元のフォルダ",
            page=name,
        )
        return templates.TemplateResponse(request, f"{name}.html", ctx)

    @app.get("/")
    def home(request: Request):
        return RedirectResponse("/reviews" if access.has_reviews(board.db, current_user(request)) else "/now")

    @app.get("/reviews", response_class=HTMLResponse)
    def reviews(request: Request, period: str | None = None):
        board.refresh()
        if not access.has_reviews(board.db, current_user(request)):
            raise HTTPException(403)
        ps = views.periods(board.db)
        if period not in ps:
            period = ps[-1] if ps else None
        return render(request, "reviews", periods=ps, period=period, groups=views.reviews(board.db, period, current_user(request)))

    @app.get("/now", response_class=HTMLResponse)
    def now_page(request: Request):
        board.refresh()
        me = current_user(request)
        rows, together = views.now(board.db, me)
        only = None if access.is_manager(me) else {r.email for r in rows}
        return render(request, "now", rows=rows, together=together, report=usage_report.team(board.cfg.usage_dir, only),
                      can_edit={r.email for r in rows if r.period and (access.is_manager(me) or access.reviews_of(board.db, me, r.email))})

    @app.get("/now/{email}", response_class=HTMLResponse)
    def now_member(request: Request, email: str):
        board.refresh()
        me = current_user(request)
        person = board.db.execute("SELECT * FROM people WHERE email = ?", (email,)).fetchone()
        if not person:
            raise HTTPException(404)
        if not access.can_see_person(board.db, me, email):
            raise HTTPException(403)
        rows, _ = views.now(board.db, me)
        row = next((r for r in rows if r.email == email), None)
        return render(request, "now_member", person=person, row=row, usage=usage_report.member(board.cfg.usage_dir, email))

    @app.post("/api/growth/{period}/{email}")
    def set_growth(request: Request, period: str, email: str, body: AxisBody):
        return apply(lambda db: workflow.set_next_axis(db, current_user(request), email, period, body.axis))

    @app.get("/reviews/{period}/{email}", response_class=HTMLResponse)
    def review(request: Request, period: str, email: str):
        board.refresh()
        me = current_user(request)
        d = views.review_detail(board.db, period, email)
        if not d:
            raise HTTPException(404)
        if not access.can_see_review(board.db, me, email, period):
            raise HTTPException(403)
        show_records = access.can_see_records(board.db, me, email)
        if not show_records:
            d["records"] = []
        acts = workflow.allowed(board.db, me, email, period, d["row"].status == "ready") if d["review"] else []
        return render(request, "review", period=period, actions=acts, show_records=show_records,
                      skill_usage=usage_report.skills(board.cfg.usage_dir, email), counts_skills=views.counts_skills, **d)

    def forbidden():
        return JSONResponse({"error": "この操作をする権限が無い"}, 403)

    @app.post("/api/reviews/{period}/{email}/action")
    def review_action(request: Request, period: str, email: str, body: ActionBody):
        me = current_user(request)
        d = views.review_detail(board.db, period, email)
        if not d or not d["review"]:
            raise HTTPException(404)
        if not access.can_see_review(board.db, me, email, period):
            return forbidden()
        return apply(lambda db: workflow.act(db, me, email, period, body.action, d["row"].status == "ready"))

    @app.post("/api/reviews/{period}/{email}/memo")
    def review_memo(request: Request, period: str, email: str, body: MemoBody):
        me = current_user(request)
        if not views.review_detail(board.db, period, email):
            raise HTTPException(404)
        if not access.can_see_records(board.db, me, email):
            return forbidden()
        return apply(lambda db: workflow.add_memo(db, me, email, period, body.body))

    # ---- 採用

    @app.get("/hiring", response_class=HTMLResponse)
    def hiring_page(request: Request):
        board.refresh()
        if not access.can_hire(current_user(request)):
            raise HTTPException(403)
        return render(request, "hiring", openings=views.openings(board.db), stages=hiring.STAGES)

    @app.get("/hiring/{email}", response_class=HTMLResponse)
    def candidate_page(request: Request, email: str):
        board.refresh()
        if not access.can_hire(current_user(request)):
            raise HTTPException(403)
        d = views.candidate_detail(board.db, email)
        if not d:
            raise HTTPException(404)
        return render(request, "candidate", **d)

    def hiring_api(request: Request, email: str, fn):
        me = current_user(request)
        if not access.can_hire(me):
            return forbidden()
        if not board.db.execute("SELECT 1 FROM candidates WHERE email = ?", (email,)).fetchone():
            raise HTTPException(404)
        return apply(lambda db: fn(db, me))

    @app.post("/api/hiring/{email}/stage")
    def candidate_stage(request: Request, email: str, body: StageBody):
        return hiring_api(request, email, lambda db, me: hiring.set_stage(db, me, email, body.stage))

    @app.post("/api/hiring/{email}/memo")
    def candidate_memo(request: Request, email: str, body: MemoBody):
        return hiring_api(request, email, lambda db, me: hiring.add_memo(db, me, email, body.body))

    @app.get("/settings", response_class=HTMLResponse)
    def settings(request: Request, v: int | None = None):
        board.refresh()
        if not access.is_manager(current_user(request)):
            raise HTTPException(403)
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

    def manager_only(request: Request, fn, *args):
        if not access.is_manager(current_user(request)):
            return forbidden()
        return apply(fn, *args)

    @app.post("/api/definition/item")
    def save_item(request: Request, body: ItemBody):
        return manager_only(request, cfg_settings.save_item, body.version, body.axis, body.level, body.key, body.text, body.evidence)

    @app.post("/api/definition/item/delete")
    def delete_item(request: Request, body: ItemKey):
        return manager_only(request, cfg_settings.delete_item, body.version, body.axis, body.level, body.key)

    @app.post("/api/definition/version")
    def new_version(request: Request):
        return manager_only(request, cfg_settings.new_version)

    @app.post("/api/people")
    def set_person(request: Request, body: PersonBody):
        return manager_only(request, cfg_settings.set_person, body.email, body.evaluator, body.role, body.hiring)

    @app.post("/api/requisitions")
    def set_requisition(request: Request, body: RequisitionBody):
        return manager_only(request, cfg_settings.set_requisition, body.name, body.count, body.target)

    return app
