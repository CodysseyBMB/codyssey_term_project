from __future__ import annotations

from app.integrations.ai_client import AIClientError


class FakeAIClient:
    """테스트용 가짜 클라이언트. 실제 네트워크를 전혀 쓰지 않는다."""

    def __init__(
        self, response: str = "fake response", error: AIClientError | None = None
    ) -> None:
        self._response = response
        self._error = error
        # 테스트에서 "호출한 쪽이 어떤 messages를 넘겼는지" 확인할 수 있게 저장해둔다.
        self.received_messages: list[dict[str, str]] | None = None

    async def generate(self, messages: list[dict[str, str]]) -> str:
        self.received_messages = messages
        if self._error is not None:
            raise self._error
        return self._response
