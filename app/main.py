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
from app.models import User
from app.routers import auth, chat
from app.templating import TEMPLATES_DIR, templates


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

    # routers/auth.py, routers/chat.py에 정의한 경로들을 앱에 연결한다.
    app.include_router(auth.router)
    app.include_router(chat.router)

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
                    "request_id": uuid.uuid4().hex,
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
