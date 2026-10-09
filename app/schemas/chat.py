from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator

# plan.md 입력 검증 기본값: 앞뒤 공백 제거 후 빈 질문 거부, 길이 1~2,000자.
MIN_QUESTION_LENGTH = 1
MAX_QUESTION_LENGTH = 2000


class ChatRequest(BaseModel):
    """POST /api/chat 요청 본문. FastAPI가 JSON을 이 모델로 자동 파싱·검증한다."""

    question: str

    @field_validator("question")
    @classmethod
    def _trim_and_check_length(cls, value: str) -> str:
        # field_validator가 return한 값이 그대로 question 필드에 저장된다.
        # 즉 라우터 쪽 코드는 이미 trim된 값만 보게 된다.
        trimmed = value.strip()
        if not (MIN_QUESTION_LENGTH <= len(trimmed) <= MAX_QUESTION_LENGTH):
            # 여기서 던진 ValueError는 pydantic이 잡아서
            # FastAPI의 RequestValidationError로 바꿔준다.
            # 실제 요청자에게 보여줄 메시지는 app/main.py의
            # validation_error_handler가 공통 포맷으로 다시 만든다.
            raise ValueError(
                f"질문은 공백을 제외하고 {MIN_QUESTION_LENGTH}~{MAX_QUESTION_LENGTH}자 사이여야 합니다."
            )
        return trimmed


class ChatResponse(BaseModel):
    """POST /api/chat 성공 응답 본문."""

    chat_id: int
    answer: str
    created_at: datetime
    request_id: str
