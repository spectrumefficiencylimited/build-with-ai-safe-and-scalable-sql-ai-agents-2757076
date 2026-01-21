"""
LangChain Callbacks for SQL AI Agent

Provides custom callback handlers for tracking LLM metrics including:
- Token usage and cost estimation
- LLM invocation timing
- Error tracking
- Session-level aggregation

These callbacks automatically log all LLM interactions when attached to
LangChain chains or LLMs.
"""

from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List, Optional
import time


class LLMMetricsCallback(BaseCallbackHandler):
    """
    LangChain callback handler for tracking LLM metrics.

    Automatically logs LLM invocations, token usage, timing, and errors.
    Integrates with the SQL AI Agent logging system for structured output.

    Attributes:
        logger: SQLAgentLogger instance for logging
        session_id: Unique session identifier
        invocation_count: Total number of LLM calls in this session
        total_tokens: Cumulative token count
        total_cost: Estimated total cost (if pricing configured)

    Usage:
        callback = LLMMetricsCallback(logger, session_id="abc123")
        llm = ChatOpenAI(
            model="gpt-4o",
            callbacks=[callback]
        )
    """

    def __init__(self, logger, session_id: str):
        """
        Initialize the metrics callback.

        Args:
            logger: SQLAgentLogger instance for logging
            session_id: Unique session identifier
        """
        self.logger = logger
        self.session_id = session_id
        self.invocation_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self._current_run_start = None

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """
        Called when LLM starts running.

        Logs the start of an LLM invocation with model details.

        Args:
            serialized: Serialized LLM configuration
            prompts: List of prompt strings
            **kwargs: Additional keyword arguments
        """
        self._current_run_start = time.perf_counter()
        self.invocation_count += 1

        model_name = serialized.get('name', 'unknown')

        self.logger.debug(
            f"LLM invocation started: {model_name}",
            extra={
                'operation_type': 'llm_invocation',
                'model_name': model_name,
                'prompt_count': len(prompts),
                'invocation_number': self.invocation_count
            }
        )

    def on_llm_end(self, response, **kwargs: Any) -> None:
        """
        Called when LLM finishes running successfully.

        Logs completion with token usage, timing, and cumulative metrics.

        Args:
            response: LLM response object with token usage info
            **kwargs: Additional keyword arguments
        """
        duration_ms = (time.perf_counter() - self._current_run_start) * 1000

        # Extract token usage from response
        llm_output = response.llm_output or {}
        token_usage = llm_output.get('token_usage', {})
        prompt_tokens = token_usage.get('prompt_tokens', 0)
        completion_tokens = token_usage.get('completion_tokens', 0)
        total_tokens = token_usage.get('total_tokens', 0)

        self.total_tokens += total_tokens

        self.logger.info(
            f"LLM invocation completed",
            extra={
                'operation_type': 'llm_invocation',
                'duration_ms': round(duration_ms, 2),
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'cumulative_tokens': self.total_tokens,
                'invocation_number': self.invocation_count
            }
        )

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Called when LLM encounters an error.

        Logs error details with timing and error type information.

        Args:
            error: Exception that occurred
            **kwargs: Additional keyword arguments
        """
        duration_ms = (time.perf_counter() - self._current_run_start) * 1000

        self.logger.error(
            f"LLM invocation failed: {str(error)}",
            extra={
                'operation_type': 'llm_invocation',
                'duration_ms': round(duration_ms, 2),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'invocation_number': self.invocation_count
            },
            exc_info=True
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for this session.

        Returns:
            Dictionary with session metrics including:
            - session_id: Session identifier
            - total_invocations: Number of LLM calls
            - total_tokens: Total tokens used
            - total_cost: Estimated total cost
        """
        return {
            'session_id': self.session_id,
            'total_invocations': self.invocation_count,
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost
        }
