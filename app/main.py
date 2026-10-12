from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings, get_settings
from app.access_control import get_current_user, get_or_create_csrf_token
from app.db import create_database_engine, create_session_factory
from app.integrations.ai_client import create_ai_client
from app.logging_utils import REQUEST_RECEIVED, UNHANDLED_ERROR, log_event, log_exception
from app.models import User
from app.routers import auth, chat, history
from app.templating import TEMPLATES_DIR, templates


def _request_id(request: Request) -> str:
    # 미들웨어가 요청마다 request.state.request_id를 심어둔다. 미들웨어를 타지 않은
    # 경로는 없지만, 혹시 몰라 없을 때는 새로 하나 만들어 대체한다.
    request_id = getattr(request.state, "request_id", None)
    return request_id if isinstance(request_id, str) else uuid.uuid4().hex


def _extract_validation_message(exc: RequestValidationError) -> str:
    # pydantic의 field_validator에서 raise ValueError(message)로 던진 경우,
    # exc.errors()[0]["msg"]에는 "Value error, message" 형태로 접두어가 붙는다.
    # ctx.error에 원래 예외 객체가 그대로 들어있어서, 그걸 str()하면 접두어 없는
    # 원본 메시지를 그대로 쓸 수 있다.
    first_error = exc.errors()[0]
    original_error = first_error.get("ctx", {}).get("error")
    if original_error is not None:
        return str(original_error)
    return first_error.get("msg", "요청 값이 올바르지 않습니다.")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_database_engine(settings.database_url)
    app = FastAPI(title="AI Chatbot", version="0.1.0")
    app.state.settings = settings
    app.state.engine = engine
    app.state.ai_client = create_ai_client(settings)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="session",
        max_age=60 * 60 * 8,
        same_site="lax",
        https_only=settings.is_production,
    )

    # get_db()가 request.app.state.session_factory로 이걸 꺼내 쓴다.
    app.state.session_factory = create_session_factory(engine)
    app.mount("/static", StaticFiles(directory=TEMPLATES_DIR.parent / "static"), name="static")

    # Starlette는 add_middleware를 나중에 호출할수록 더 바깥쪽에 쌓는다. 즉 이
    # 미들웨어는 SessionMiddleware보다 바깥이라 아직 request.session이 채워지기
    # 전에 실행된다 — 그래서 user_id는 여기서 읽지 않고, 이미 로그인 여부를 아는
    # 각 라우터/서비스(chat_service 등)가 필요할 때 직접 남긴다.
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        log_event(
            REQUEST_RECEIVED,
            request_id=request.state.request_id,
            method=request.method,
            path=request.url.path,
        )
        return await call_next(request)

    # 기능별 라우터에 정의한 경로들을 앱에 연결한다.
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.include_router(history.router)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # plan.md가 정한 공통 오류 응답 포맷: {"error": {code, message, request_id}}.
        # FastAPI 기본 핸들러는 {"detail": [...]} 형태라 API 계약과 안 맞아서 덮어쓴다.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": _extract_validation_message(exc),
                    "request_id": _request_id(request),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # 여기까지 오는 건 access_control의 401/403이나 pydantic 검증처럼 "예상된"
        # 오류가 아니라, 미리 분류해두지 못한 버그·장애다. 클라이언트에는 내부
        # 정보를 숨긴 일반 메시지만 주고, 스택 트레이스는 서버 로그에만 남긴다.
        request_id = _request_id(request)
        log_exception(UNHANDLED_ERROR, exc, request_id=request_id, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                    "request_id": request_id,
                }
            },
        )

    @app.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        current_user: User | None = Depends(get_current_user),
    ):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "app_env": settings.app_env,
                "is_authenticated": current_user is not None,
                "csrf_token": (
                    get_or_create_csrf_token(request)
                    if current_user is not None
                    else None
                ),
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
