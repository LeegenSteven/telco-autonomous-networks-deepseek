import json
import logging
from datetime import UTC, datetime

from telco_local.settings import settings


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_local_logging() -> None:
    root = logging.getLogger()
    marker = "telco_local_json_file"
    if any(getattr(handler, "name", "") == marker for handler in root.handlers):
        return

    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(settings.log_path, encoding="utf-8")
    handler.name = marker
    handler.setFormatter(JsonLineFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
