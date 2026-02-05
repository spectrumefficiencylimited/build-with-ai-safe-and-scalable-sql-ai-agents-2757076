"""
Token Counting Utilities for SQL AI Agent

Provides functions to estimate token counts for prompts sent to LLMs.
Uses tiktoken for accurate token counting matching OpenAI's tokenization.
"""

from typing import List, Dict, Any, Optional


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Estimate the number of tokens in a text string.

    Uses tiktoken library for accurate token counting that matches
    OpenAI's tokenization. Falls back to rough estimation if tiktoken
    is not available.

    Args:
        text: Text to count tokens for
        model: Model name to use for tokenization (default: "gpt-4o")

    Returns:
        Estimated token count

    Example:
        >>> estimate_tokens("How many rows are in the table?", "gpt-4o")
        8
    """
    try:
        import tiktoken

        # Get the encoding for the model
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            # This is used by gpt-4, gpt-3.5-turbo, and newer models
            encoding = tiktoken.get_encoding("cl100k_base")

        # Count tokens
        tokens = encoding.encode(text)
        return len(tokens)

    except ImportError:
        # Fallback: Rough estimation if tiktoken is not available
        # Average: 1 token ≈ 4 characters or 0.75 words
        return _estimate_tokens_fallback(text)


def _estimate_tokens_fallback(text: str) -> int:
    """
    Fallback token estimation when tiktoken is not available.

    Uses rough heuristic: 1 token ≈ 4 characters.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count (rough approximation)
    """
    return len(text) // 4


def estimate_messages_tokens(messages: List[Dict[str, Any]], model: str = "gpt-4o") -> int:
    """
    Estimate tokens for a list of chat messages.

    Accounts for message formatting overhead used by chat models.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model name for tokenization

    Returns:
        Estimated total token count including formatting overhead

    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are a helpful assistant"},
        ...     {"role": "user", "content": "Hello!"}
        ... ]
        >>> estimate_messages_tokens(messages, "gpt-4o")
        20
    """
    try:
        import tiktoken

        # Get encoding
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        # Base tokens for message formatting
        # Every message has some overhead for formatting
        tokens_per_message = 3  # <|start|>role/name\n{content}<|end|>\n
        tokens_per_name = 1

        num_tokens = 0

        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(str(value)))
                if key == "name":
                    num_tokens += tokens_per_name

        # Add 3 tokens for reply priming
        num_tokens += 3

        return num_tokens

    except ImportError:
        # Fallback: Sum all message content
        total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
        return total_chars // 4 + len(messages) * 3  # Add overhead per message


def format_token_count(token_count: int) -> str:
    """
    Format token count for display with context.

    Args:
        token_count: Number of tokens

    Returns:
        Formatted string with token count and approximate character/word count

    Example:
        >>> format_token_count(1000)
        '1,000 tokens (~4,000 chars, ~750 words)'
    """
    chars = token_count * 4
    words = int(token_count * 0.75)

    return f"{token_count:,} tokens (~{chars:,} chars, ~{words:,} words)"


def check_token_limit(token_count: int, model: str, buffer: int = 500) -> Dict[str, Any]:
    """
    Check if token count is within model's context window.

    Args:
        token_count: Number of tokens to check
        model: Model name
        buffer: Safety buffer to leave for response (default: 500)

    Returns:
        Dictionary with:
        - within_limit: Boolean indicating if within limits
        - model_limit: Maximum context window for model
        - buffer: Safety buffer used
        - remaining: Tokens remaining for response
        - percentage_used: Percentage of context window used

    Example:
        >>> check_token_limit(8000, "gpt-4o")
        {
            'within_limit': True,
            'model_limit': 128000,
            'buffer': 500,
            'remaining': 119500,
            'percentage_used': 6.25
        }
    """
    # Model context windows (approximate)
    model_limits = {
        # OpenAI models
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16385,
        "gpt-3.5-turbo-16k": 16385,
        # Anthropic models
        "claude-3-5-sonnet": 200000,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
        # Google models
        "gemini-1.5-pro": 2000000,
        "gemini-1.5-flash": 1000000,
        # Default fallback
        "default": 8192
    }

    # Find matching model limit
    limit = model_limits.get(model)
    if limit is None:
        # Try to find partial match
        for model_name, model_limit in model_limits.items():
            if model_name in model.lower():
                limit = model_limit
                break
        else:
            limit = model_limits["default"]

    # Calculate metrics
    usable_limit = limit - buffer
    within_limit = token_count <= usable_limit
    remaining = usable_limit - token_count
    percentage_used = (token_count / limit) * 100

    return {
        "within_limit": within_limit,
        "model_limit": limit,
        "buffer": buffer,
        "remaining": max(0, remaining),
        "percentage_used": round(percentage_used, 2),
        "tokens_over": max(0, token_count - usable_limit)
    }


def get_token_stats(text: str, model: str = "gpt-4o") -> Dict[str, Any]:
    """
    Get comprehensive token statistics for a text.

    Args:
        text: Text to analyze
        model: Model name for tokenization

    Returns:
        Dictionary with token statistics:
        - token_count: Number of tokens
        - char_count: Number of characters
        - word_count: Approximate word count
        - model: Model used for tokenization
        - formatted: Formatted display string
        - limit_check: Token limit check results

    Example:
        >>> stats = get_token_stats("How many rows?", "gpt-4o")
        >>> print(stats['token_count'])
        4
    """
    token_count = estimate_tokens(text, model)
    char_count = len(text)
    word_count = len(text.split())

    return {
        "token_count": token_count,
        "char_count": char_count,
        "word_count": word_count,
        "model": model,
        "formatted": format_token_count(token_count),
        "limit_check": check_token_limit(token_count, model)
    }


# Example usage
if __name__ == "__main__":
    """
    Examples of token counting utilities.
    """
    print("=" * 80)
    print("Token Counting Utilities - Examples")
    print("=" * 80)

    # Example 1: Simple token counting
    print("\n📌 Example 1: Count tokens in a simple prompt")
    prompt = "SELECT * FROM employees WHERE department = 'Engineering'"
    tokens = estimate_tokens(prompt, "gpt-4o")
    print(f"Prompt: {prompt}")
    print(f"Token count: {tokens}")

    # Example 2: Token statistics
    print("\n📌 Example 2: Get comprehensive token statistics")
    long_prompt = """
    You are a SQL expert. Given the following table schema:

    employees (id INT, name VARCHAR, age INT, department VARCHAR)

    Write a SQL query to find the average age of employees in each department.
    """
    stats = get_token_stats(long_prompt, "gpt-4o")
    print(f"Token count: {stats['token_count']}")
    print(f"Character count: {stats['char_count']}")
    print(f"Word count: {stats['word_count']}")
    print(f"Formatted: {stats['formatted']}")
    print(f"Within limit: {stats['limit_check']['within_limit']}")

    # Example 3: Chat messages
    print("\n📌 Example 3: Count tokens in chat messages")
    messages = [
        {"role": "system", "content": "You are a SQL expert assistant."},
        {"role": "user", "content": "How do I join two tables?"},
        {"role": "assistant", "content": "You can use JOIN clause with ON condition."},
        {"role": "user", "content": "Show me an example."}
    ]
    message_tokens = estimate_messages_tokens(messages, "gpt-4o")
    print(f"Messages: {len(messages)}")
    print(f"Total tokens: {message_tokens}")

    # Example 4: Check token limits
    print("\n📌 Example 4: Check token limits")
    large_prompt = "SELECT * FROM table " * 1000
    large_tokens = estimate_tokens(large_prompt, "gpt-4o")
    limit_check = check_token_limit(large_tokens, "gpt-4o")
    print(f"Token count: {large_tokens:,}")
    print(f"Model limit: {limit_check['model_limit']:,}")
    print(f"Within limit: {limit_check['within_limit']}")
    print(f"Percentage used: {limit_check['percentage_used']}%")
    print(f"Remaining tokens: {limit_check['remaining']:,}")

    print("\n" + "=" * 80)
    print("✅ Examples complete!")
    print("=" * 80)
