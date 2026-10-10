from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.access_control import (
    get_or_create_csrf_token,
    require_header_csrf,
    require_page_user,
    require_user,
)
from app.db import get_db
from app.integrations.ai_client import AIClientProtocol
from app.models import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import (
    ChatPersistenceError,
    ChatService,
    ChatTimeoutError,
    ChatUpstreamError,
)
from app.templating import templates

router = APIRouter(tags=["chat"])


def get_ai_client(request: Request) -> AIClientProtocol:
    return request.app.state.ai_client


def _error_response(
    status_code: int, code: str, message: str, request_id: str
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
    )


@router.get("/chat", response_class=HTMLResponse)
def chat_page(
    request: Request,
    # require_page_user: 로그인 안 돼 있으면 여기서 /auth/login으로 리다이렉트된다.
    _current_user: User = Depends(require_page_user),
):
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            # JS가 fetch("/api/chat")를 보낼 때 X-CSRF-Token 헤더에 그대로 실어 보낼 값.
            # 폼 hidden input과 같은 토큰을 재사용한다 (require_header_csrf가 비교하는 값).
            "csrf_token": get_or_create_csrf_token(request),
        },
    )


@router.post("/api/chat", response_model=ChatResponse)
async def ask_chat(
    # payload: ChatRequest -> FastAPI가 요청 바디(JSON)를 자동으로 파싱하고
    # ChatRequest의 field_validator(trim + 길이 검증)를 통과한 값만 여기 도달한다.
    payload: ChatRequest,
    request: Request,
    # require_user: 미인증이면 401 반환 (require_page_user와 달리 리다이렉트하지 않는다 — JSON API라서).
    current_user: User = Depends(require_user),
    # require_header_csrf: X-CSRF-Token 헤더를 세션의 csrf_token과 대조한다.
    _csrf: None = Depends(require_header_csrf),
    db: Session = Depends(get_db),
    ai_client: AIClientProtocol = Depends(get_ai_client),
):
    request_id = uuid.uuid4().hex

    service = ChatService(
        session=db,
        ai_client=ai_client,
        ai_model=request.app.state.settings.ai_model,
    )
    try:
        result = await service.ask(current_user.id, payload.question)
    except ChatTimeoutError:
        return _error_response(
            504,
            "AI_TIMEOUT",
            "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.",
            request_id,
        )
    except ChatUpstreamError:
        return _error_response(
            502,
            "AI_UPSTREAM_ERROR",
            "AI 서비스에 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            request_id,
        )
    except ChatPersistenceError:
        return _error_response(
            500,
            "DB_WRITE_ERROR",
            "응답을 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            request_id,
        )

    return ChatResponse(
        chat_id=result.chat_id,
        answer=result.answer,
        created_at=result.created_at,
        request_id=request_id,
    )
