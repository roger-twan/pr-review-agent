import logging
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.github import GitHubClient
from app.llm import PullRequestReviewRequest, create_llm_provider
from app.security import verify_github_signature

logger = logging.getLogger(__name__)

app = FastAPI(title="PR Review Agent", version="0.1.0")

REVIEWABLE_ACTIONS = {"opened", "reopened", "ready_for_review", "synchronize"}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    body = await request.body()
    if not verify_github_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub signature")

    payload = await request.json()
    if x_github_event != "pull_request":
        return {"ok": True, "ignored": f"event {x_github_event}"}

    action = payload.get("action")
    pull_request = payload.get("pull_request") or {}
    if action not in REVIEWABLE_ACTIONS or pull_request.get("draft"):
        return {"ok": True, "ignored": f"action {action}"}

    installation_id = (payload.get("installation") or {}).get("id")
    repository = payload.get("repository") or {}
    owner = (repository.get("owner") or {}).get("login")
    repo = repository.get("name")
    repo_full_name = repository.get("full_name") or f"{owner}/{repo}"
    pull_number = pull_request.get("number")
    title = pull_request.get("title") or ""

    if not all([installation_id, owner, repo, pull_number]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incomplete pull_request payload")

    background_tasks.add_task(
        process_pull_request_review,
        settings,
        int(installation_id),
        owner,
        repo,
        repo_full_name,
        int(pull_number),
        title,
        action,
    )
    return {"ok": True, "queued": True}


async def process_pull_request_review(
    settings: Settings,
    installation_id: int,
    owner: str,
    repo: str,
    repo_full_name: str,
    pull_number: int,
    title: str,
    action: str,
) -> None:
    github = GitHubClient(settings)

    logger.info("Reviewing %s#%s for action=%s", repo_full_name, pull_number, action)
    try:
        reviewer = create_llm_provider(settings)
        diff = await github.pull_request_diff(installation_id, owner, repo, pull_number)
        review = await reviewer.review_pull_request(
            PullRequestReviewRequest(
                repo_full_name=repo_full_name,
                pull_number=pull_number,
                title=title,
                diff=diff,
            )
        )
        comment_body = format_review_comment(review, settings)

        if settings.dry_run:
            logger.info("DRY_RUN enabled; not posting comment to GitHub. Review:\n%s", comment_body)
            return

        comment = await github.post_issue_comment(installation_id, owner, repo, pull_number, comment_body)
        logger.info("Posted review comment: %s", comment.get("html_url"))
    except Exception:
        logger.exception("Failed to review %s#%s", repo_full_name, pull_number)


def format_review_comment(review: str, settings: Settings) -> str:
    footer = f"\n\n---\nReviewed by {settings.llm_provider} via GitHub App."
    if settings.server_public_url:
        footer += f"\nServer: {settings.server_public_url}"
    return f"## Automated PR Review\n\n{review}{footer}"
