import hashlib
import hmac

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def _signature(secret: str, payload: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pull_request_webhook_queues_review(monkeypatch) -> None:
    secret = "webhook-secret"
    settings = Settings(
        GITHUB_APP_ID="1",
        GITHUB_WEBHOOK_SECRET=secret,
        GITHUB_PRIVATE_KEY="unused",
        DEEPSEEK_API_KEY="unused",
    )
    calls = []

    async def fake_review(*args, **kwargs) -> None:
        calls.append((args, kwargs))

    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("app.main.process_pull_request_review", fake_review)

    payload = b"""{
      "action": "opened",
      "installation": {"id": 99},
      "repository": {"name": "repo", "full_name": "octo/repo", "owner": {"login": "octo"}},
      "pull_request": {"number": 7, "title": "Improve code", "draft": false}
    }"""

    try:
        response = TestClient(app).post(
            "/webhooks/github",
            content=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": _signature(secret, payload),
                "Content-Type": "application/json",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True, "queued": True}
    assert len(calls) == 1
    assert calls[0][0][3:7] == ("repo", "octo/repo", 7, "Improve code")


def test_webhook_rejects_invalid_signature() -> None:
    settings = Settings(
        GITHUB_APP_ID="1",
        GITHUB_WEBHOOK_SECRET="webhook-secret",
        GITHUB_PRIVATE_KEY="unused",
        DEEPSEEK_API_KEY="unused",
    )
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = TestClient(app).post(
            "/webhooks/github",
            content=b"{}",
            headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=bad"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
