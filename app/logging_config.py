"""Allowlisted technical events. Exception messages/tracebacks are never logged.

Exception strings can include SQL values, file paths and personal data. Record
only the exception class and fixed event names, even at debug level.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.paths import managed_path

EVENTS = frozenset({
    "database_migration_started", "database_migration_completed",
    "database_migration_failed", "backup_created", "backup_failed",
    "restore_started", "restore_completed", "restore_failed",
    "certificate_copy_failed", "unexpected_exception", "payment_reminder",
})
logger = logging.getLogger("onca.technical")
logger.addHandler(logging.NullHandler())
logger.propagate = False


def configure_logging(data_root: Path) -> None:
    """Rotate technical logs outside source; replace earlier handlers safely."""
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    directory = managed_path(data_root, "logs")
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(managed_path(data_root, "logs/technical.log"), maxBytes=512_000,
                                  backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def log_event(event: str, error: BaseException | None = None) -> None:
    """Log a fixed event and, optionally, an exception type, never its value."""
    if event not in EVENTS:
        raise ValueError("Unknown technical event")
    if error is None:
        logger.info(event)
    else:
        logger.error("%s error_type=%s", event, type(error).__name__)
