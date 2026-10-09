from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.ai_client import AIClientError, AIClientProtocol, AITimeoutError
from app.repositories.chat_repository import (
    add_message,
    create_conversation,
    list_recent_messages,
)


DEFAULT_CONTEXT_CONVERSATIONS = 5


class ChatServiceError(Exception):
    """채팅 처리 실패를 라우터에 전달하는 서비스 계층 예외."""


class ChatTimeoutError(ChatServiceError):
    """AI 응답이 제한 시간 안에 오지 않은 경우."""


class ChatUpstreamError(ChatServiceError):
    """AI 공급자가 요청 처리에 실패한 경우."""


class ChatPersistenceError(ChatServiceError):
    """문맥 조회 또는 새 대화 저장에 실패한 경우."""


@dataclass(frozen=True)
class ChatResult:
    chat_id: int
    answer: str
    created_at: datetime


class ChatService:
    def __init__(
        self,
        session: Session,
        ai_client: AIClientProtocol,
        ai_model: str,
        context_conversations: int = DEFAULT_CONTEXT_CONVERSATIONS,
    ) -> None:
        self._session = session
        self._ai_client = ai_client
        self._ai_model = ai_model
        self._context_conversations = context_conversations

    async def ask(self, user_id: int, question: str) -> ChatResult:
        try:
            history = list_recent_messages(
                self._session,
                user_id,
                conversation_limit=self._context_conversations,
            )
            messages = [
                {"role": message.role, "content": message.content}
                for message in history
            ]
            # 읽기 쿼리가 연 트랜잭션과 DB 연결을 긴 AI 호출 동안 유지하지 않는다.
            self._session.rollback()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise ChatPersistenceError("대화 문맥을 조회하지 못했습니다.") from exc

        messages.append({"role": "user", "content": question})
        started_at = perf_counter()
        try:
            answer = await self._ai_client.generate(messages)
        except AITimeoutError as exc:
            raise ChatTimeoutError("AI 응답 시간이 초과되었습니다.") from exc
        except AIClientError as exc:
            raise ChatUpstreamError("AI 공급자 요청에 실패했습니다.") from exc
        latency_ms = max(0, round((perf_counter() - started_at) * 1000))

        try:
            conversation = create_conversation(self._session, user_id)
            add_message(
                self._session,
                user_id,
                conversation.id,
                "user",
                question,
            )
            assistant_message = add_message(
                self._session,
                user_id,
                conversation.id,
                "assistant",
                answer,
                ai_model=self._ai_model,
                latency_ms=latency_ms,
            )
            self._session.commit()
        except SQLAlchemyError as exc:
            self._session.rollback()
            raise ChatPersistenceError("대화를 저장하지 못했습니다.") from exc

        return ChatResult(
            chat_id=conversation.id,
            answer=assistant_message.content,
            created_at=assistant_message.created_at,
        )
