from __future__ import annotations

import re

from fastapi.testclient import TestClient


CSRF_INPUT_PATTERN = re.compile(
    r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']'
)


def get_csrf_token(client: TestClient, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    match = CSRF_INPUT_PATTERN.search(response.text)
    assert match is not None
    return match.group(1)
