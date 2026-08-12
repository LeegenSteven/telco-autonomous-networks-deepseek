import os

from google.adk.models.lite_llm import LiteLlm

from telco_local.settings import settings


def build_model(role: str) -> LiteLlm:
    """Build an ADK model backed by DeepSeek's OpenAI-compatible API."""

    model_name = settings.model_for(role)
    # ADK's LiteLlm wrapper only exposes the model field. LiteLLM reads provider
    # credentials and the endpoint from these standard DeepSeek variables.
    os.environ["DEEPSEEK_API_KEY"] = (
        settings.deepseek_api_key or "missing-deepseek-api-key"
    )
    os.environ["DEEPSEEK_API_BASE"] = settings.deepseek_base_url
    return LiteLlm(model=f"deepseek/{model_name}")


def assert_deepseek_configured() -> None:
    if not settings.deepseek_api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is missing. Copy agents/.env.example to "
            "agents/.env and add your key."
        )
