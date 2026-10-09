from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.integrations.ai_client import (
    AIConnectionError,
    AIProviderError,
    AITimeoutError,
    AnthropicGatewayClient,
    FakeAIClient,
)


def run(coro):
    # pytest-asyncio 같은 플러그인을 추가하지 않고, 동기 테스트 안에서
    # 비동기 함수(coroutine)를 그냥 실행만 시키기 위한 작은 헬퍼.
    return asyncio.run(coro)


def make_real_client(handler, timeout_seconds: float = 5) -> AnthropicGatewayClient:
    # transport에 가짜 handler를 주입하면 실제 네트워크를 전혀 안 타고,
    # handler가 돌려주는 응답을 httpx가 "진짜 서버 응답인 것처럼" 처리해준다.
    return AnthropicGatewayClient(
        api_key="test-key",
        base_url="https://fake.test",
        model="claude-haiku-4",
        timeout_seconds=timeout_seconds,
        transport=httpx.MockTransport(handler),
    )


def test_generate_returns_text_on_success() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "안녕하세요!"}]},
        )

    client = make_real_client(handler)

    result = run(client.generate([{"role": "user", "content": "안녕"}]))

    assert result == "안녕하세요!"
    assert captured["headers"]["x-api-key"] == "test-key"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert captured["body"] == {
        "model": "claude-haiku-4",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "안녕"}],
    }


def test_generate_raises_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("simulated timeout")

    client = make_real_client(handler)

    with pytest.raises(AITimeoutError):
        run(client.generate([{"role": "user", "content": "안녕"}]))


def test_generate_raises_provider_error_on_failure_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "overloaded"}})

    client = make_real_client(handler)

    with pytest.raises(AIProviderError) as exc_info:
        run(client.generate([{"role": "user", "content": "안녕"}]))

    assert exc_info.value.status_code == 500


def test_generate_raises_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated connection failure", request=request)

    client = make_real_client(handler)

    with pytest.raises(AIConnectionError):
        run(client.generate([{"role": "user", "content": "안녕"}]))


def test_generate_rejects_invalid_success_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": []})

    client = make_real_client(handler)

    with pytest.raises(AIProviderError):
        run(client.generate([{"role": "user", "content": "안녕"}]))


def test_repr_does_not_leak_api_key() -> None:
    client = AnthropicGatewayClient(
        api_key="super-secret-key",
        base_url="https://fake.test",
        model="claude-haiku-4",
        timeout_seconds=5,
    )

    assert "super-secret-key" not in repr(client)


def test_fake_client_returns_configured_response_and_records_messages() -> None:
    client = FakeAIClient(response="테스트 응답")

    result = run(client.generate([{"role": "user", "content": "질문"}]))

    assert result == "테스트 응답"
    assert client.received_messages == [{"role": "user", "content": "질문"}]


def test_fake_client_raises_configured_error() -> None:
    client = FakeAIClient(error=AITimeoutError("boom"))

    with pytest.raises(AITimeoutError):
        run(client.generate([{"role": "user", "content": "질문"}]))


async def _ask(client, question: str) -> str:
    # AIClientProtocol 모양만 맞으면 어떤 클라이언트든 이 함수 하나로 다룰 수 있다 —
    # 완료 조건 "실제 클라이언트와 가짜 클라이언트를 설정으로 교체할 수 있다"를 보여준다.
    return await client.generate([{"role": "user", "content": question}])


def test_real_and_fake_clients_are_interchangeable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": [{"type": "text", "text": "실제 응답"}]})

    real = make_real_client(handler)
    fake = FakeAIClient(response="가짜 응답")

    assert run(_ask(real, "안녕")) == "실제 응답"
    assert run(_ask(fake, "안녕")) == "가짜 응답"
