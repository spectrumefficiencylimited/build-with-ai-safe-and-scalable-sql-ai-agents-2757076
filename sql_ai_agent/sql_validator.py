"""
SQL Query Validator

This module provides SQL query validation to prevent harmful operations
and enforce safety constraints for SQL AI agents.

It validates queries to:
- Block non-SELECT operations in read-only mode
- Prevent SQL injection via multiple statements
- Enforce result size limits via LIMIT clauses
- Provide clear error messages for violations
"""

from dataclasses import dataclass, field
from typing import Optional
import logging
import sqlglot
from sqlglot import exp

# Create module-level logger
logger = logging.getLogger('sql_ai_agent.validator')


class QueryValidationError(Exception):
    """Raised when a query violates validation rules."""
    pass


@dataclass
class ValidationConfig:
    """Configuration for SQL query validation.

    Attributes:
        read_only: If True, only SELECT queries are allowed
        max_limit: Maximum number of rows that can be returned
        enforce_limit: If True, automatically add/enforce LIMIT clause
        allowed_statements: List of allowed SQL statement types
    """
    read_only: bool = True
    max_limit: int = 10000
    enforce_limit: bool = True
    allowed_statements: list = field(default_factory=lambda: ["Select", "With", "Show", "Describe"])


class SQLValidator:
    """Validates SQL queries against safety rules.

    The validator uses sqlglot to parse and analyze SQL queries without
    executing them, providing a security layer between LLM output and
    database execution.

    Example:
        >>> validator = SQLValidator()
        >>> is_valid, error = validator.validate("SELECT * FROM users")
        >>> if not is_valid:
        ...     raise QueryValidationError(error)

        >>> safe_query = validator.enforce_limit("SELECT * FROM users")
        >>> print(safe_query)
        SELECT * FROM users LIMIT 10000
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """Initialize the SQL validator.

        Args:
            config: Validation configuration. If None, uses default config.
        """
        self.config = config or ValidationConfig()

    def validate(self, query: str) -> tuple[bool, Optional[str]]:
        """Validate SQL query against safety rules.

        Checks for:
        1. Multiple statements (SQL injection protection)
        2. Disallowed statement types (e.g., UPDATE, DELETE in read-only mode)

        Args:
            query: SQL query string to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if query passes validation
            - error_message: Error description if validation fails, None otherwise

        Example:
            >>> validator = SQLValidator()
            >>> is_valid, error = validator.validate("DROP TABLE users")
            >>> print(is_valid, error)
            False, "Operation not allowed: Drop. Only SELECT queries permitted in read-only mode."
        """
        logger.debug(
            "Starting query validation",
            extra={
                'operation_type': 'validation',
                'query_length': len(query) if query else 0,
                'read_only': self.config.read_only
            }
        )

        if not query or not query.strip():
            logger.warning(
                "Empty query rejected",
                extra={'operation_type': 'validation'}
            )
            return False, "Empty query not allowed"

        try:
            # Parse query
            statements = sqlglot.parse(query)

            # Check for multiple statements (SQL injection protection)
            if len(statements) > 1:
                logger.warning(
                    "Multiple statements detected",
                    extra={
                        'operation_type': 'validation',
                        'statement_count': len(statements)
                    }
                )
                return False, "Multiple SQL statements detected. Only single statements allowed."

            # Check for valid statement types
            statement_types = self._get_statement_types(query)

            # In read-only mode, only SELECT is allowed
            if self.config.read_only:
                # Check if all statement types are in allowed list
                allowed_set = set(self.config.allowed_statements)
                if not statement_types.issubset(allowed_set):
                    blocked = statement_types - allowed_set
                    logger.warning(
                        "Disallowed operation in read-only mode",
                        extra={
                            'operation_type': 'validation',
                            'blocked_operations': list(blocked),
                            'query': query[:200]
                        }
                    )
                    return False, (
                        f"Operation not allowed: {', '.join(sorted(blocked))}. "
                        f"Only SELECT queries permitted in read-only mode."
                    )

            logger.debug(
                "Validation passed",
                extra={'operation_type': 'validation'}
            )
            return True, None

        except Exception as e:
            logger.error(
                "Validation error",
                extra={
                    'operation_type': 'validation',
                    'error_type': type(e).__name__,
                    'query': query[:200]
                },
                exc_info=True
            )
            # If parsing fails, be conservative and block the query
            return False, f"Unable to parse query: {str(e)}"

    def enforce_limit(self, query: str) -> str:
        """Add or enforce LIMIT clause on SELECT queries.

        If the query doesn't have a LIMIT, adds one with max_limit.
        If the query has a LIMIT greater than max_limit, reduces it.

        Args:
            query: SQL query string

        Returns:
            Modified query with enforced LIMIT

        Example:
            >>> validator = SQLValidator(ValidationConfig(max_limit=100))
            >>> validator.enforce_limit("SELECT * FROM users")
            'SELECT * FROM users LIMIT 100'

            >>> validator.enforce_limit("SELECT * FROM users LIMIT 10000")
            'SELECT * FROM users LIMIT 100'
        """
        if not self.config.enforce_limit:
            return query

        try:
            # Parse the query
            parsed = sqlglot.parse_one(query)

            # Only enforce LIMIT on SELECT statements
            if not isinstance(parsed, exp.Select):
                return query

            # Check if query already has LIMIT
            limit_expr = parsed.find(exp.Limit)

            if limit_expr:
                # Has LIMIT, check if it's too large
                try:
                    # Get the limit value
                    limit_value = limit_expr.expression
                    if limit_value:
                        current_limit = int(str(limit_value))
                        if current_limit > self.config.max_limit:
                            # Replace with max_limit
                            parsed = parsed.limit(self.config.max_limit)
                except (ValueError, AttributeError):
                    # If we can't parse the limit value, leave it as-is
                    pass
            else:
                # No LIMIT, add one
                parsed = parsed.limit(self.config.max_limit)

            # Return the modified query
            return parsed.sql()

        except Exception as e:
            # If parsing/modification fails, try simple string append
            # This is a fallback for edge cases
            try:
                # Remove trailing semicolon if present
                query_stripped = query.rstrip().rstrip(';')

                # Check if LIMIT already exists (simple string check)
                if 'LIMIT' not in query_stripped.upper():
                    return f"{query_stripped} LIMIT {self.config.max_limit}"

                return query
            except Exception:
                # Last resort: return original query
                return query

    def _get_statement_types(self, query: str) -> set[str]:
        """Extract all statement types from parsed query.

        Args:
            query: SQL query string

        Returns:
            Set of statement type names (e.g., {'Select', 'Insert'})

        Raises:
            QueryValidationError: If query cannot be parsed
        """
        try:
            parsed = sqlglot.parse(query)
            statement_types = set()

            for statement in parsed:
                if statement:
                    # Get the class name (e.g., 'Select', 'Insert', 'Update')
                    statement_types.add(statement.__class__.__name__)

            return statement_types

        except Exception as e:
            raise QueryValidationError(f"Unable to parse query: {str(e)}")

    def get_validation_summary(self) -> dict:
        """Get a summary of current validation settings.

        Returns:
            Dictionary with validation configuration details
        """
        return {
            "read_only": self.config.read_only,
            "max_limit": self.config.max_limit,
            "enforce_limit": self.config.enforce_limit,
            "allowed_statements": self.config.allowed_statements,
        }
