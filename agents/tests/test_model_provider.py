import os

from telco_local.model_provider import build_model
from telco_local.settings import settings


def test_deepseek_model_provider_configures_litellm(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    monkeypatch.setattr(settings, "deepseek_base_url", "https://api.deepseek.com")
    model = build_model("incident_detector")

    assert model.model.startswith("deepseek/")
    assert os.environ["DEEPSEEK_API_KEY"] == "test-key"
    assert os.environ["DEEPSEEK_API_BASE"] == "https://api.deepseek.com"
