from __future__ import annotations

import re

from fastapi.testclient import TestClient


CSRF_INPUT_PATTERN = re.compile(
    r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']'
)
# chat.html처럼 폼이 아니라 JS fetch()로 CSRF 토큰을 보내는 화면은
# <body data-csrf-token="..."> 속성에 토큰을 심어둔다.
CSRF_DATA_ATTR_PATTERN = re.compile(r'data-csrf-token=["\']([^"\']+)["\']')


def get_csrf_token(client: TestClient, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_INPUT_PATTERN.search(response.text)
    assert match is not None
    return match.group(1)


def get_header_csrf_token(client: TestClient, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_DATA_ATTR_PATTERN.search(response.text)
    assert match is not None
    return match.group(1)
