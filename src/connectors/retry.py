"""
Retry logic with exponential backoff for ERP API calls.

Handles transient failures, rate limiting, and circuit breaker patterns.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Set, Type
import logging

import httpx


logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True  # Add randomness to prevent thundering herd

    # Which HTTP status codes should trigger retry
    retryable_status_codes: Set[int] = None

    # Which exceptions should trigger retry
    retryable_exceptions: Set[Type[Exception]] = None

    def __post_init__(self):
        if self.retryable_status_codes is None:
            # Default: retry on server errors and rate limiting
            self.retryable_status_codes = {429, 500, 502, 503, 504}

        if self.retryable_exceptions is None:
            # Default: retry on timeout and connection errors
            self.retryable_exceptions = {
                httpx.TimeoutException,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
            }


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing) -> CLOSED
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "CLOSED"
        self.logger = logging.getLogger(f"{__name__}.CircuitBreaker")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self._state == "OPEN":
            if time.time() - self._last_failure_time < self.recovery_timeout:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Retry after {self.recovery_timeout}s"
                )
            else:
                self._state = "HALF_OPEN"
                self.logger.info("Circuit breaker entering HALF_OPEN state")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        if self._state == "HALF_OPEN":
            self.logger.info("Circuit breaker recovered, entering CLOSED state")
            self._state = "CLOSED"
        self._failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "OPEN"
            self.logger.warning(
                f"Circuit breaker OPEN after {self._failure_count} failures"
            )


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """
    Calculate delay before next retry attempt.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    if config.strategy == RetryStrategy.FIXED:
        delay = config.initial_delay
    elif config.strategy == RetryStrategy.LINEAR:
        delay = config.initial_delay * (attempt + 1)
    else:  # EXPONENTIAL
        delay = config.initial_delay * (config.exponential_base ** attempt)

    # Cap at max_delay
    delay = min(delay, config.max_delay)

    # Add jitter to prevent thundering herd
    if config.jitter:
        import random
        delay = delay * (0.5 + random.random())

    return delay


def should_retry(
    exception: Optional[Exception],
    response: Optional[httpx.Response],
    config: RetryConfig
) -> bool:
    """
    Determine if request should be retried.

    Args:
        exception: Exception that occurred (if any)
        response: HTTP response (if any)
        config: Retry configuration

    Returns:
        True if should retry
    """
    # Check exception type
    if exception:
        return any(
            isinstance(exception, exc_type)
            for exc_type in config.retryable_exceptions
        )

    # Check response status code
    if response:
        return response.status_code in config.retryable_status_codes

    return False


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute async function with retry logic.

    Args:
        func: Async function to execute
        args: Positional arguments
        config: Retry configuration
        kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        RetryExhaustedError: If all retry attempts fail
    """
    config = config or RetryConfig()
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
            return result

        except Exception as e:
            last_exception = e

            # Check if we should retry this error
            response = getattr(e, "response", None)
            if not should_retry(e, response, config):
                logger.warning(f"Non-retryable error: {e}")
                raise

            # Don't retry if this was the last attempt
            if attempt >= config.max_attempts - 1:
                break

            # Calculate delay and wait
            delay = calculate_delay(attempt, config)
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

    # All retries exhausted
    raise RetryExhaustedError(
        f"Failed after {config.max_attempts} attempts. Last error: {last_exception}"
    ) from last_exception


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to async functions.

    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Prevents exceeding API rate limits.
    """

    def __init__(
        self,
        rate: int,
        per: float = 1.0,
        burst: Optional[int] = None
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum number of requests
            per: Time period in seconds
            burst: Maximum burst size (defaults to rate)
        """
        self.rate = rate
        self.per = per
        self.burst = burst or rate

        self._tokens = float(self.burst)
        self._last_update = time.time()
        self._lock = asyncio.Lock()

        self.logger = logging.getLogger(f"{__name__}.RateLimiter")

    async def acquire(self, tokens: int = 1):
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            while True:
                now = time.time()
                elapsed = now - self._last_update

                # Add tokens based on elapsed time
                self._tokens = min(
                    self.burst,
                    self._tokens + (elapsed * self.rate / self.per)
                )
                self._last_update = now

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                # Not enough tokens, calculate wait time
                needed = tokens - self._tokens
                wait_time = (needed * self.per) / self.rate

                self.logger.debug(f"Rate limit hit, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
