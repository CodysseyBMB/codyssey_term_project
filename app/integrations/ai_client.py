from __future__ import annotations

from typing import Protocol

import httpx

from app.config import Settings

# Anthropic API 버전. 게이트웨이가 요구하는 값이라 모델/엔드포인트와 무관하게 고정한다.
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 1024


class AIClientError(Exception):
    """AI 호출이 실패했을 때의 공통 베이스 예외."""


class AITimeoutError(AIClientError):
    """지정한 시간 안에 AI 응답이 오지 않았을 때 발생한다."""


class AIConnectionError(AIClientError):
    """AI 공급자와 네트워크 연결을 맺거나 유지하지 못했을 때 발생한다."""


class AIProviderError(AIClientError):
    """AI 공급자(게이트웨이)가 오류 상태 코드를 반환했을 때 발생한다."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"AI provider error {status_code}: {message}")
        self.status_code = status_code


class AIClientProtocol(Protocol):
    # Protocol: "이 모양의 generate 메서드를 가진 객체라면 전부 AIClient로 취급한다"는
    # 구조적 타이핑(structural typing)이다. 아래 AnthropicGatewayClient와 FakeAIClient가
    # 서로 다른 클래스이면서도 이 모양만 맞추면 호출하는 쪽 코드를 바꾸지 않고 교체할 수 있다.
    async def generate(self, messages: list[dict[str, str]]) -> str: ...


class AnthropicGatewayClient:
    """Codyssey 'Neito' 게이트웨이의 Anthropic 네이티브 엔드포인트(/v1/messages)를 호출한다."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._timeout_seconds = timeout_seconds
        # transport는 테스트에서 실제 네트워크 없이 가짜 응답을 주입하기 위한 용도.
        # 운영에서는 None으로 두면 httpx가 기본(실제) 전송 방식을 사용한다.
        self._transport = transport

    def __repr__(self) -> str:
        # api_key를 절대 노출하지 않는다 (로그에 이 객체가 찍혀도 키가 새면 안 된다).
        return f"AnthropicGatewayClient(model={self._model!r}, base_url={self._base_url!r})"

    async def generate(self, messages: list[dict[str, str]]) -> str:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    f"{self._base_url}/v1/messages",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": ANTHROPIC_VERSION,
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "max_tokens": DEFAULT_MAX_TOKENS,
                        "messages": messages,
                    },
                )
        except httpx.TimeoutException as exc:
            raise AITimeoutError(
                f"AI request timed out after {self._timeout_seconds}s"
            ) from exc
        except httpx.RequestError as exc:
            raise AIConnectionError("AI provider connection failed") from exc

        if response.status_code >= 400:
            raise AIProviderError(response.status_code, response.text)

        try:
            answer = response.json()["content"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(
                response.status_code, "invalid response payload"
            ) from exc
        if not isinstance(answer, str) or not answer:
            raise AIProviderError(response.status_code, "empty response content")
        return answer


class FakeAIClient:
    """테스트·개발용 가짜 클라이언트. 실제 네트워크를 전혀 쓰지 않는다."""

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


def create_ai_client(settings: Settings) -> AIClientProtocol:
    """설정값만으로 실제 클라이언트를 만든다. 테스트에서는 FakeAIClient를 직접 써서 교체한다."""
    return AnthropicGatewayClient(
        api_key=settings.ai_api_key,
        base_url=settings.ai_base_url,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )
