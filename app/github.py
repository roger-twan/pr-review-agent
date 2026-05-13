from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

from app.config import Settings


class GitHubClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _app_jwt(self) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "iat": int((now - timedelta(seconds=60)).timestamp()),
            "exp": int((now + timedelta(minutes=9)).timestamp()),
            "iss": self.settings.github_app_id,
        }
        return jwt.encode(payload, self.settings.private_key, algorithm="RS256")

    async def installation_token(self, installation_id: int) -> str:
        url = f"{self.settings.github_api_url}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._app_jwt()}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()["token"]

    async def pull_request_diff(self, installation_id: int, owner: str, repo: str, pull_number: int) -> str:
        token = await self.installation_token(installation_id)
        url = f"{self.settings.github_api_url}/repos/{owner}/{repo}/pulls/{pull_number}"
        headers = {
            "Accept": "application/vnd.github.v3.diff",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    async def post_issue_comment(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> dict[str, Any]:
        token = await self.installation_token(installation_id)
        url = f"{self.settings.github_api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json={"body": body})
            response.raise_for_status()
            return response.json()

