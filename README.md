# PR Review Agent

FastAPI webhook server for a GitHub App that reviews pull requests with an LLM provider and posts the result back as a PR comment.

## What It Does

- Verifies GitHub webhook signatures.
- Handles `pull_request` events for `opened`, `reopened`, `ready_for_review`, and `synchronize`.
- Uses GitHub App installation auth to fetch the PR diff.
- Sends the diff to the configured LLM provider.
- Posts the review as a pull request comment.
- Ships with Docker and Cloud Build config for Cloud Run.

## Local Setup

```bash
cp .env.example .env
uv sync --dev
uv run uvicorn app.main:app --reload --port 8080
```

GitHub should send webhooks to:

```text
https://YOUR_PUBLIC_URL/webhooks/github
```

For local testing, expose port `8080` with a tunnel such as `ngrok` or Cloudflare Tunnel and set the GitHub App webhook URL to the tunnel URL plus `/webhooks/github`.

## GitHub App Settings

Required permissions:

- Pull requests: Read-only
- Contents: Read-only
- Issues: Read and write
- Metadata: Read-only

Subscribe to events:

- Pull request

Use a strong webhook secret and put the same value in `GITHUB_WEBHOOK_SECRET`.

## Environment Variables

| Variable | Description |
| --- | --- |
| `GITHUB_APP_ID` | GitHub App ID. |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret configured in the GitHub App. |
| `GITHUB_PRIVATE_KEY` | GitHub App private key content. Use escaped `\n` locally if needed. |
| `GITHUB_PRIVATE_KEY_PATH` | Alternative to `GITHUB_PRIVATE_KEY`; path to a `.pem` file. |
| `LLM_PROVIDER` | LLM provider name. Defaults to `deepseek`. |
| `LLM_MODEL` | Provider-neutral model override. Defaults to the provider-specific model. |
| `DEEPSEEK_API_KEY` | DeepSeek API key. |
| `DEEPSEEK_BASE_URL` | Defaults to `https://api.deepseek.com`. |
| `DEEPSEEK_MODEL` | DeepSeek-specific default model. Defaults to `deepseek-v4-flash`. |
| `SERVER_PUBLIC_URL` | Optional URL shown in the review footer. |
| `REVIEW_MAX_DIFF_CHARS` | Max diff characters sent to the LLM. |
| `DRY_RUN` | Set `true` to return reviews without posting to GitHub. |

## LLM Providers

Set `LLM_PROVIDER=deepseek` to use the current DeepSeek adapter. The provider layer lives in `app/llm.py`; future providers can implement `LLMProvider` and be returned from `create_llm_provider`. Providers with an OpenAI-compatible `/v1/chat/completions` API can reuse `OpenAICompatibleProvider`.

## Deploy To GCP Cloud Run

Create an Artifact Registry repository once:

```bash
gcloud artifacts repositories create pr-review-agent \
  --repository-format=docker \
  --location=us-central1
```

Create Secret Manager secrets:

```bash
printf 'your-github-app-id' | gcloud secrets create GITHUB_APP_ID --data-file=-
printf 'your-webhook-secret' | gcloud secrets create GITHUB_WEBHOOK_SECRET --data-file=-
gcloud secrets create GITHUB_PRIVATE_KEY --data-file=github-app-private-key.pem
printf 'sk-your-deepseek-key' | gcloud secrets create DEEPSEEK_API_KEY --data-file=-
```

Deploy with Cloud Build:

```bash
gcloud builds submit --config cloudbuild.yaml
```

After deployment, copy the Cloud Run service URL into your GitHub App webhook URL:

```text
https://YOUR_CLOUD_RUN_URL/webhooks/github
```

## Health Check

```bash
curl http://localhost:8080/health
```

Expected response:

```json
{"status":"ok"}
```
