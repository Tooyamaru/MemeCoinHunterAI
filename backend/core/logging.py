"""Standard-library logging setup for the application foundation."""

import logging

from backend.core.config import Settings

LOGGER_NAME = "meme_coin_hunter_ai"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure one application logger and return it.

    The setup is idempotent so API and future worker entrypoints can safely call
    it independently without producing duplicate log lines.
    """

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported LOG_LEVEL: {settings.log_level}")

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)

    return logger
