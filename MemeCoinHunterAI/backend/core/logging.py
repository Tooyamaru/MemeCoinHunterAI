"""Standard-library logging setup for the application foundation."""

import logging

from backend.core.config import Settings

LOGGER_NAME = "meme_coin_hunter_ai"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"


class RequestIdFilter(logging.Filter):
    """Add the current request ID to every record without requiring callers to pass it."""

    def filter(self, record: logging.LogRecord) -> bool:
        from backend.core.request_id import get_request_id

        record.request_id = get_request_id()
        return True


def get_logger() -> logging.Logger:
    """Return the shared application logger."""

    return logging.getLogger(LOGGER_NAME)


def configure_logging(settings: Settings) -> logging.Logger:
    """Configure one application logger and return it.

    The setup is idempotent so API and future worker entrypoints can safely call
    it independently without producing duplicate log lines.
    """

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"Unsupported LOG_LEVEL: {settings.log_level}")

    logger = get_logger()
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)

    return logger
