from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.access_control import require_page_user, require_user
from app.db import get_db
from app.models import User
from app.repositories.chat_repository import list_chat_history
from app.schemas.history import ChatHistoryItem, ChatHistoryResponse
from app.templating import templates


DEFAULT_HISTORY_LIMIT = 20
MAX_HISTORY_LIMIT = 100
HistoryLimit = Annotated[int, Query(ge=1, le=MAX_HISTORY_LIMIT)]
HistoryOffset = Annotated[int, Query(ge=0)]

router = APIRouter(tags=["history"])


def _get_history(
    db: Session,
    user_id: int,
    limit: int,
    offset: int,
) -> ChatHistoryResponse:
    page = list_chat_history(db, user_id, limit=limit, offset=offset)
    return ChatHistoryResponse(
        items=[ChatHistoryItem.model_validate(item, from_attributes=True) for item in page.items],
        limit=limit,
        offset=offset,
        has_more=page.has_more,
    )


@router.get("/api/me/chats", response_model=ChatHistoryResponse)
def get_my_chats(
    limit: HistoryLimit = DEFAULT_HISTORY_LIMIT,
    offset: HistoryOffset = 0,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> ChatHistoryResponse:
    return _get_history(db, current_user.id, limit, offset)


@router.get("/history", response_class=HTMLResponse)
def history_page(
    request: Request,
    limit: HistoryLimit = DEFAULT_HISTORY_LIMIT,
    offset: HistoryOffset = 0,
    current_user: User = Depends(require_page_user),
    db: Session = Depends(get_db),
):
    history = _get_history(db, current_user.id, limit, offset)
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "history": history,
            "previous_offset": max(0, offset - limit),
            "next_offset": offset + limit,
        },
    )
