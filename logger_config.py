"""
GVP Watch Backend - Logger Configuration
-----------------------------------------
Centralized logging setup using Python's logging module.
All logs are written to both console and a rotating file handler.

Log format includes:
- Timestamp (YYYY-MM-DD HH:MM:SS)
- Log level (INFO, DEBUG, WARNING, ERROR)
- Component/module name
- Ticket ID (if available)
- Message

Example log line:
[2026-04-02 14:30:45] [INFO] [TicketService] [tk-12345] - Ticket created for Northward_Ward
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import json
from config import LOG_FILE, LOG_LEVEL

# Create logs directory
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class ContextualFormatter(logging.Formatter):
    """
    Custom formatter that includes optional ticket context in log messages.
    Allows including ticket_id and other contextual info in thread-local storage.
    """

    def format(self, record):
        # Extract optional ticket_id from record if present
        ticket_id = getattr(record, "ticket_id", None)
        ticket_context = f"[{ticket_id}]" if ticket_id else ""

        # Base format: timestamp, level, logger name, ticket context, message
        base_fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] {ticket_id} - %(message)s"
        formatter = logging.Formatter(
            base_fmt.format(ticket_id=ticket_context),
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return formatter.format(record)


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given module name.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    # Set log level
    logger.setLevel(LOG_LEVEL.upper())

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL.upper())
    console_formatter = ContextualFormatter()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (max 5MB per file, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5
    )
    file_handler.setLevel(LOG_LEVEL.upper())
    file_formatter = ContextualFormatter()
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, ticket_id: str = None):
    """
    Helper function to log a message with optional ticket context.

    Args:
        logger: Logger instance
        level: Log level (INFO, DEBUG, WARNING, ERROR)
        message: Log message
        ticket_id: Optional ticket ID for context
    """
    log_func = getattr(logger, level.lower(), logger.info)

    if ticket_id:
        extra = {"ticket_id": ticket_id}
        log_func(message, extra=extra)
    else:
        log_func(message)


def log_ticket_action(logger: logging.Logger, action: str, ticket_id: str, details: dict = None):
    """
    Log a ticket-related action with structured data.
    This is called for all ticket state changes, reminders, assignments, etc.

    Args:
        logger: Logger instance
        action: Action type (STATUS_CHANGE, REMINDER_SENT, AUTO_RESOLVED, etc.)
        ticket_id: Ticket ID
        details: Dict with additional context (old_status, new_status, officer_phone, etc.)
    """
    if details is None:
        details = {}

    # Build message with all context
    detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
    message = f"[{action}] {detail_str}"

    log_with_context(logger, "INFO", message, ticket_id)


# Initialize root logger at module level
root_logger = get_logger("gvp_watch")

if __name__ == "__main__":
    # Test logging setup
    test_logger = get_logger("test_module")
    test_logger.info("Test log message without context")
    log_with_context(test_logger, "INFO", "Test log message with ticket context", "tk-12345")
    log_ticket_action(test_logger, "STATUS_CHANGE", "tk-12345", {
        "old_status": "INITIATED",
        "new_status": "AWAITING_PHOTO"
    })
