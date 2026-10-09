from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.access_control import (
    get_or_create_csrf_token,
    require_header_csrf,
    require_page_user,
    require_user,
)
from app.models import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.templating import templates

router = APIRouter(tags=["chat"])


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
    # require_user: 미인증이면 401 반환 (require_page_user와 달리 리다이렉트하지 않는다 — JSON API라서).
    # 지금은 "로그인 여부"만 확인하고 유저 정보 자체는 쓰지 않는다 (이슈 #7에서 메시지 저장에 사용 예정).
    _current_user: User = Depends(require_user),
    # require_header_csrf: X-CSRF-Token 헤더를 세션의 csrf_token과 대조한다.
    _csrf: None = Depends(require_header_csrf),
):
    request_id = uuid.uuid4().hex

    # AI 연동 전 임시 응답. 실제 AI 호출·문맥 구성·DB 저장은 이슈 #7에서 구현한다.
    answer = f"(임시 응답) 아직 AI와 연결되지 않았습니다. 받은 질문: {payload.question}"

    return ChatResponse(
        answer=answer,
        created_at=datetime.now(timezone.utc),
        request_id=request_id,
    )
