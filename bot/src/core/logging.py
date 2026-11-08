import json
import logging
from datetime import UTC, datetime
from typing import Literal

from rich.logging import RichHandler


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            data["stack"] = self.formatStack(record.stack_info)
        return json.dumps(data, ensure_ascii=False)


def configure_logging(environment: Literal["local", "prod"]) -> None:
    if environment == "local":
        handler = RichHandler(rich_tracebacks=True, tracebacks_show_locals=False)
        handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
