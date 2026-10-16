from __future__ import annotations

import asyncio
import json
import logging

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.asgi_logging import ASGILoggingMiddleware
from app.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_tables():
    """이 모듈은 DB를 사용하지 않는다. 상위의 DB 초기화 fixture를 대체한다."""
    yield


@pytest.mark.parametrize("environment", ["development", "production", "test", "product"])
def test_environment_and_shared_request_id(environment, caplog):
    settings = Settings(
        _env_file=None, app_env=environment, database_url="sqlite://",
        session_secret="x" * 32, ai_api_key="unused-test-key",
    )
    app = create_app(settings)

    @app.post("/__echo")
    async def echo(request: Request):
        return {"request_id": request.state.request_id, "body": (await request.body()).decode()}

    @app.get("/__boom")
    def boom():
        raise RuntimeError("test failure")

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            with caplog.at_level(logging.INFO, logger="app.events"):
                response = client.post(
                    "/__echo", content="private-body",
                    headers={"Authorization": "private-token", "Cookie": "secret=private-cookie"},
                )
            assert response.status_code == 200
            assert response.json()["body"] == "private-body"
            records = [r.getMessage() for r in caplog.records if r.name == "app.events"]
            asgi_records = [r for r in records if r.startswith("asgi_")]
            assert bool(asgi_records) == (environment == "development")
            assert any(r.startswith("request_received") for r in records)
            for record in records:
                assert f"request_id={response.json()['request_id']}" in record
            assert all(secret not in caplog.text for secret in (
                "private-body", "private-token", "private-cookie",
            ))
            if environment == "development":
                assert "type=http.request" in caplog.text
                assert "type=http.response.start status=200" in caplog.text
                assert "response_complete=True" in caplog.text
                caplog.clear()
                failure = client.get("/__boom")
                assert failure.status_code == 500
                assert "asgi_request_error" in caplog.text
                assert "response_complete=False" in caplog.text
                # 최외곽 ServerErrorMiddleware의 500 응답은 이 미들웨어를 지나지 않는다.
                assert "asgi_send" not in caplog.text
                assert "unhandled_error" in caplog.text
    finally:
        app.state.engine.dispose()


def test_chunked_messages_are_forwarded_unchanged(caplog):
    incoming = [
        {"type": "http.request", "body": b"private-", "more_body": True},
        {"type": "http.request", "body": b"body", "more_body": False},
        {"type": "http.disconnect"},
    ]
    outgoing = [
        {"type": "http.response.start", "status": 200, "headers": []},
        {"type": "http.response.body", "body": b"first", "more_body": True},
        {"type": "http.response.body", "body": b"last", "more_body": False},
    ]
    received, sent = [], []

    async def receive():
        return incoming[len(received)]

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        for _ in incoming:
            received.append(await receive())
        for message in outgoing:
            await send(message)

    with caplog.at_level(logging.INFO, logger="app.events"):
        asyncio.run(ASGILoggingMiddleware(app)(
            {"type": "http", "method": "POST", "path": "/chunks"}, receive, send,
        ))
    assert all(actual is original for actual, original in zip(received, incoming, strict=True))
    assert all(actual is original for actual, original in zip(sent, outgoing, strict=True))
    assert "more_body=True" in caplog.text
    assert "type=http.disconnect" in caplog.text
    assert "private-" not in caplog.text
    assert "response_complete=True" in caplog.text


def test_scope_metadata_and_header_allowlist(caplog):
    scope = {
        "type": "http", "method": "POST", "path": "/scope",
        "http_version": "1.1", "scheme": "http",
        "client": ("127.0.0.1", 52312), "server": ("127.0.0.1", 8000),
        "query_string": b"token=private-query",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", b"32"),
            (b"accept", b"application/json"),
            (b"accept", b"text/plain\r\nforged-line"),
            (b"authorization", b"private-token"),
            (b"cookie", b"private-cookie"),
            (b"x-api-key", b"private-key"),
        ],
    }

    async def receive():
        raise AssertionError("scope logging must not read the body")

    async def send(message):
        pass

    async def app(actual_scope, receive, send):
        assert actual_scope is scope
        assert len(actual_scope["headers"]) == 7

    with caplog.at_level(logging.INFO, logger="app.events"):
        asyncio.run(ASGILoggingMiddleware(app)(scope, receive, send))
    record = next(r.getMessage() for r in caplog.records if r.getMessage().startswith("asgi_scope "))
    assert "type=http http_version=1.1 scheme=http" in record
    assert 'client=["127.0.0.1", 52312]' in record
    assert 'server=["127.0.0.1", 8000]' in record
    headers = json.loads(record.split(" headers=", 1)[1])
    assert headers == [[name.decode(), value.decode()] for name, value in scope["headers"][:4]]
    assert "\n" not in record
    assert all(secret not in caplog.text for secret in (
        "private-query", "private-token", "private-cookie", "private-key",
    ))


@pytest.mark.parametrize("scope_type", ["lifespan", "websocket"])
def test_non_http_is_passed_through(scope_type, caplog):
    scope = {"type": scope_type}

    async def receive():
        raise AssertionError("must not read events")

    async def send(message):
        raise AssertionError("must not send events")

    async def app(actual_scope, actual_receive, actual_send):
        assert actual_scope is scope
        assert actual_receive is receive
        assert actual_send is send

    with caplog.at_level(logging.INFO, logger="app.events"):
        asyncio.run(ASGILoggingMiddleware(app)(scope, receive, send))
    assert not caplog.records


def test_send_failure_is_propagated_without_marking_complete(caplog):
    failure = RuntimeError("private-error-detail")

    async def receive():
        raise AssertionError("must not read ahead")

    async def send(message):
        raise failure

    async def app(scope, receive, send):
        await send({"type": "http.response.body", "body": b"private-body"})

    with caplog.at_level(logging.INFO, logger="app.events"), pytest.raises(RuntimeError) as caught:
        asyncio.run(ASGILoggingMiddleware(app)(
            {"type": "http", "method": "GET", "path": "/"}, receive, send,
        ))
    assert caught.value is failure
    assert "exception_type=RuntimeError" in caplog.text
    assert "response_complete=False" in caplog.text
    assert "private-error-detail" not in caplog.text
    assert "asgi_send" not in caplog.text
