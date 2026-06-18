"""
MindCradle centralized logging utility.

Usage:
    from app.utils.logger import get_logger

    logger = get_logger(__name__)

    logger.info("User %s logged in", user_id)
    logger.warning("Rate limit hit for user %s", user_id)
    logger.error("Payment processing failed for user %s: %s", user_id, error_code)

Security rules (enforced by convention):
  - NEVER log: passwords, tokens (JWT, FCM, API keys), raw request bodies with PII
  - DO log:    user_id (not email), action names, error codes, timestamps
"""

import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Return a named logger configured for MindCradle production use.

    Args:
        name:  Typically __name__ of the calling module.
        level: Override the log level (defaults to INFO in production).

    Returns:
        A configured Logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers when called multiple times
    if logger.handlers:
        return logger

    effective_level = level if level is not None else logging.INFO
    logger.setLevel(effective_level)

    # Stream handler → stdout (captured by uvicorn / docker / systemd)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(effective_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to the root logger to avoid duplicate output
    logger.propagate = False

    return logger


# ---------------------------------------------------------------------------
# Module-level convenience loggers for cross-cutting concerns
# ---------------------------------------------------------------------------

#: General application events (startup, config, middleware)
app_logger = get_logger("mindcradle.app")

#: Security-relevant events: auth failures, age-gate violations, token issues
security_logger = get_logger("mindcradle.security")

#: User-action audit trail: login, logout, data mutations
audit_logger = get_logger("mindcradle.audit")
