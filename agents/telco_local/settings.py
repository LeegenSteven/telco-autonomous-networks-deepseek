from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


AGENTS_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = AGENTS_DIR.parent


class LocalSettings(BaseSettings):
    """Configuration shared by both local agents."""

    model_config = SettingsConfigDict(
        env_file=AGENTS_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_default_model: str = "deepseek-v4-flash"

    incident_detector_model: Optional[str] = None
    root_agent_model: Optional[str] = None
    incident_retriever_model: Optional[str] = None
    analyzer_model: Optional[str] = None
    instruction_generator_model: Optional[str] = None
    severity_classifier_model: Optional[str] = None
    external_doc_retriever_model: Optional[str] = None
    internal_doc_retriever_model: Optional[str] = None
    prior_incidents_searcher_model: Optional[str] = None
    report_generator_model: Optional[str] = None
    agent_executor_model: Optional[str] = None

    root_agent_name: str = "root_cause_analyst"
    confirm_each_step: bool = False
    local_db_path: str = "../.local/telco_demo.duckdb"
    local_log_path: str = "../.local/logs/agent_events.jsonl"
    external_docs_enabled: bool = False
    similarity_search_min_score: float = 0.10
    similarity_search_max_number_of_incidents: int = 5

    def model_for(self, role: str) -> str:
        override = getattr(self, f"{role}_model", None)
        return override or self.deepseek_default_model

    @property
    def database_path(self) -> Path:
        path = Path(self.local_db_path)
        return path if path.is_absolute() else (AGENTS_DIR / path).resolve()

    @property
    def log_path(self) -> Path:
        path = Path(self.local_log_path)
        return path if path.is_absolute() else (AGENTS_DIR / path).resolve()


settings = LocalSettings()
