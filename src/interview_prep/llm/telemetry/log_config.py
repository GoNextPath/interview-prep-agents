"""CLI application logging configuration, independent of provider SDK logging."""

import logging
import sys

from interview_prep.llm.contracts import ConfigurationError


def configure_logging(level: str) -> None:
    """CLI logging for our namespace only; DEBUG never enables SDK request-body logging."""
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigurationError("INTERVIEW_PREP_LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
    application_logger = logging.getLogger("interview_prep")
    application_logger.setLevel(level)
    application_logger.propagate = False
    # The CLI owns its application handlers. Repeated setup should not duplicate output.
    for handler in application_logger.handlers[:]:
        application_logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    application_logger.addHandler(handler)
