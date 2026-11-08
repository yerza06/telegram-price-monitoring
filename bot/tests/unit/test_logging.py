import json
import logging

import pytest
from rich.logging import RichHandler

from core.logging import configure_logging


@pytest.fixture
def root_logger():
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    # basicConfig(force=True) closes existing handlers; isolate pytest's handlers.
    root.handlers = []
    yield root
    for handler in root.handlers:
        handler.close()
    root.handlers = handlers
    root.setLevel(level)


def test_local_logging(root_logger, capsys):
    configure_logging("local")
    assert isinstance(root_logger.handlers[0], RichHandler)
    logging.getLogger("test").info("Цена %s", 100)
    assert "Цена 100" in capsys.readouterr().out


def test_prod_logging(root_logger, capsys):
    configure_logging("prod")
    logger = logging.getLogger("test")
    logger.info("Цена %s\nобновлена", 100)
    try:
        raise ValueError("ошибка")
    except ValueError:
        logger.exception("Не удалось обновить")

    lines = capsys.readouterr().err.splitlines()
    assert len(lines) == 2
    info, error = map(json.loads, lines)
    assert info["message"] == "Цена 100\nобновлена"
    assert info["level"] == "INFO"
    assert info["logger"] == "test"
    assert info["timestamp"]
    assert error["level"] == "ERROR"
    assert "ValueError: ошибка" in error["exception"]
