from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import Settings, get_settings
from app.access_control import get_current_user, get_or_create_csrf_token
from app.db import create_database_engine, create_session_factory
from app.models import User
from app.routers import auth
from app.templating import TEMPLATES_DIR, templates


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

    # routers/auth.py에 정의한 /auth/signup 등을 앱에 연결한다.
    app.include_router(auth.router)

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
