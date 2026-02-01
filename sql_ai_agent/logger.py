"""
SQL AI Agent Logging Module

Provides structured logging capabilities with JSON formatting, performance timing,
and context-aware logging for the SQL AI Agent.

Features:
- Structured JSON logging for easy parsing and analysis
- Human-readable console output for development
- Performance timing decorators
- Session and request tracking
- Minimal performance overhead
"""

import logging
import time
import uuid
import json
from typing import Any, Dict, Optional
from functools import wraps
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """
    Formats log records as JSON with structured fields.

    Creates JSON log entries with consistent structure including timestamp,
    level, logger name, message, and any extra fields provided.
    """

    def format(self, record):
        """Format a log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class SQLAgentLogger(logging.LoggerAdapter):
    """
    Custom logger adapter that adds context fields to all log records.

    Automatically includes:
    - session_id: Unique identifier for agent instance
    - request_id: Unique identifier for each operation
    - operation_type: Category of operation being logged

    Usage:
        logger = SQLAgentLogger(base_logger, extra={'session_id': 'abc123'})
        logger.info("Query executed", extra={'duration_ms': 45.2})
    """

    def __init__(self, logger, extra=None):
        """
        Initialize logger adapter with context fields.

        Args:
            logger: Base Python logger instance
            extra: Dictionary of context fields to add to all log records
        """
        extra = extra or {}
        extra.setdefault('session_id', str(uuid.uuid4()))
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        """
        Process log record to merge extra fields from adapter and call-time.

        Args:
            msg: Log message
            kwargs: Keyword arguments including optional 'extra' dict

        Returns:
            Tuple of (message, kwargs) with merged extra fields
        """
        # Merge extra fields from both adapter and call-time
        extra_fields = dict(self.extra)
        if 'extra' in kwargs:
            extra_fields.update(kwargs['extra'])
            kwargs.pop('extra')

        # Store in record for formatter
        kwargs['extra'] = {'extra_fields': extra_fields}
        return msg, kwargs


def timed_operation(operation_type: str):
    """
    Decorator to automatically log operation duration and success/failure.

    Logs start time at DEBUG level, end time and duration at INFO level.
    Automatically captures exceptions and logs them at ERROR level.

    Args:
        operation_type: Category name for the operation (e.g., "query_execution")

    Usage:
        @timed_operation("query_execution")
        def execute_query(self, query):
            return query_execute(self.con, query)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from self if it's a method
            logger = getattr(args[0], 'logger', None) if args else None

            start_time = time.perf_counter()
            request_id = str(uuid.uuid4())

            if logger:
                logger.debug(
                    f"Starting {operation_type}",
                    extra={
                        'operation_type': operation_type,
                        'request_id': request_id,
                        'function': func.__name__
                    }
                )

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if logger:
                    logger.info(
                        f"Completed {operation_type}",
                        extra={
                            'operation_type': operation_type,
                            'request_id': request_id,
                            'duration_ms': round(duration_ms, 2),
                            'success': True
                        }
                    )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000

                if logger:
                    logger.error(
                        f"Failed {operation_type}: {str(e)}",
                        extra={
                            'operation_type': operation_type,
                            'request_id': request_id,
                            'duration_ms': round(duration_ms, 2),
                            'success': False,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        },
                        exc_info=True
                    )

                raise

        return wrapper
    return decorator


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console_format: str = "human",
    file_format: str = "json",
    log_to_console: bool = True,
) -> SQLAgentLogger:
    """
    Configure logging for SQL AI Agent.

    Creates a logger with configurable console and file handlers.
    Supports both human-readable and JSON formats for different environments.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (None for console only)
        console_format: Format for console output ("human" or "json")
        file_format: Format for file output ("human" or "json")
        log_to_console: Whether to output logs to console (default: True)

    Returns:
        Configured SQLAgentLogger instance

    Example:
        logger = setup_logging(
            log_level="INFO",
            log_file="logs/agent.log",
            console_format="human",
            file_format="json",
            log_to_console=False
        )
        logger.info("Agent initialized")
    """
    logger = logging.getLogger('sql_ai_agent')
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()  # Remove existing handlers

    # Console handler (optional)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))

        if console_format == "json":
            console_handler.setFormatter(StructuredFormatter())
        else:
            # Human-readable format
            console_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        # Create logs directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))

        if file_format == "json":
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            )
        logger.addHandler(file_handler)

    return SQLAgentLogger(logger)
