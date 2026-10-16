from __future__ import annotations

import json
from time import perf_counter
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_utils import log_event


# 필요한 헤더만 허용한다. 중복 헤더를 보존하고 개행은 JSON으로 이스케이프한다.
SCOPE_LOG_HEADERS = {b"content-type", b"content-length", b"accept"}


class ASGILoggingMiddleware:
    """HTTP 이벤트의 메타데이터만 관찰하며 원래 메시지를 그대로 전달한다."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        response_complete = False
        log_event(
            "asgi_request_start", request_id=request_id,
            method=scope["method"], path=scope["path"],
        )
        headers = [
            (name.decode("latin-1"), value.decode("latin-1"))
            for name, value in scope.get("headers", [])
            if name.lower() in SCOPE_LOG_HEADERS
        ]
        log_event(
            "asgi_scope", request_id=request_id,
            type=scope["type"], http_version=scope.get("http_version"),
            scheme=scope.get("scheme"),
            client=json.dumps(scope.get("client"), ensure_ascii=True),
            server=json.dumps(scope.get("server"), ensure_ascii=True),
            headers=json.dumps(headers, ensure_ascii=True),
        )

        async def logged_receive() -> Message:
            message = await receive()
            fields: dict[str, object] = {"type": message["type"]}
            if message["type"] == "http.request":
                fields.update(
                    body_bytes=len(message.get("body", b"")),
                    more_body=message.get("more_body", False),
                )
            log_event("asgi_receive", request_id=request_id, **fields)
            return message

        async def logged_send(message: Message) -> None:
            nonlocal response_complete
            # 다음 계층에 전달한 후 기록한다. 브라우저의 수신 완료를 뜻하지 않는다.
            await send(message)
            fields: dict[str, object] = {"type": message["type"]}
            if message["type"] == "http.response.start":
                fields["status"] = message["status"]
            elif message["type"] == "http.response.body":
                more_body = message.get("more_body", False)
                fields.update(body_bytes=len(message.get("body", b"")), more_body=more_body)
                response_complete = not more_body
            log_event("asgi_send", request_id=request_id, **fields)

        try:
            await self.app(scope, logged_receive, logged_send)
        except BaseException as exc:
            # 취소도 기록 후 그대로 전파한다. 예외 메시지에는 민감 정보가 있을 수 있다.
            log_event("asgi_request_error", request_id=request_id, exception_type=type(exc).__name__)
            raise
        finally:
            log_event(
                "asgi_request_end", request_id=request_id,
                duration_ms=round((perf_counter() - started) * 1000, 3),
                response_complete=response_complete,
            )
