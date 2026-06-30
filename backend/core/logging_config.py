"""Structured logging setup (structlog). Dev → console, prod → JSON."""
import logging

import structlog

from backend.config import ENVIRONMENT, LOG_LEVEL


def configure_logging() -> None:
    """Configure stdlib + structlog. Idempotent."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    )
    renderer = (
        structlog.processors.JSONRenderer()
        if ENVIRONMENT == "production"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
