from abc import ABC, abstractmethod

import httpx

from app.config import Settings


class PullRequestReviewRequest:
    def __init__(self, repo_full_name: str, pull_number: int, title: str, diff: str):
        self.repo_full_name = repo_full_name
        self.pull_number = pull_number
        self.title = title
        self.diff = diff


class LLMProvider(ABC):
    @abstractmethod
    async def review_pull_request(self, request: PullRequestReviewRequest) -> str:
        """Return a Markdown review for a pull request diff."""


SYSTEM_PROMPT = """You are a senior engineer reviewing a GitHub pull request.
Focus on concrete correctness, security, reliability, data-loss, performance, and maintainability issues.
Do not invent findings. If the diff is clean, say so briefly.
Return Markdown with:
- A short overall summary
- Findings ordered by severity
- Test gaps or follow-up suggestions
When possible, mention file paths and relevant changed code context from the diff."""


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, settings: Settings, api_key: str, base_url: str, model: str):
        self.settings = settings
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def review_pull_request(self, request: PullRequestReviewRequest) -> str:
        truncated = request.diff[: self.settings.review_max_diff_chars]
        suffix = ""
        if len(request.diff) > len(truncated):
            suffix = (
                "\n\n[Diff truncated because it exceeded REVIEW_MAX_DIFF_CHARS. "
                "Call out that the review may be incomplete.]"
            )

        user_prompt = f"""Review this pull request.

Repository: {request.repo_full_name}
Pull request: #{request.pull_number}
Title: {request.title}

Diff:
```diff
{truncated}
```{suffix}
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()


def create_llm_provider(settings: Settings) -> LLMProvider:
    provider = settings.llm_provider.lower()

    if provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required when LLM_PROVIDER=deepseek")
        return OpenAICompatibleProvider(
            settings=settings,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.llm_model or settings.deepseek_model,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
