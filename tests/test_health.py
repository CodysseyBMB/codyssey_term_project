from __future__ import annotations

from fastapi.testclient import TestClient

def test_index_renders_skeleton_page(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "AI Chatbot 프로젝트" in response.text


def test_health_does_not_depend_on_database(client: TestClient) -> None:
    client.app.state.engine.dispose()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
