import pytest

from app.config import Settings
from app.llm import OpenAICompatibleProvider, create_llm_provider


def test_create_llm_provider_uses_deepseek_by_default() -> None:
    settings = Settings(
        GITHUB_APP_ID="1",
        GITHUB_WEBHOOK_SECRET="secret",
        GITHUB_PRIVATE_KEY="unused",
        DEEPSEEK_API_KEY="deepseek-key",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://api.deepseek.com"
    assert provider.model == "deepseek-v4-flash"


def test_create_llm_provider_uses_neutral_model_override() -> None:
    settings = Settings(
        GITHUB_APP_ID="1",
        GITHUB_WEBHOOK_SECRET="secret",
        GITHUB_PRIVATE_KEY="unused",
        DEEPSEEK_API_KEY="deepseek-key",
        LLM_MODEL="deepseek-chat",
    )

    provider = create_llm_provider(settings)

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.model == "deepseek-chat"


def test_create_llm_provider_rejects_unknown_provider() -> None:
    settings = Settings(
        GITHUB_APP_ID="1",
        GITHUB_WEBHOOK_SECRET="secret",
        GITHUB_PRIVATE_KEY="unused",
        DEEPSEEK_API_KEY="deepseek-key",
        LLM_PROVIDER="unknown",
    )

    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        create_llm_provider(settings)
