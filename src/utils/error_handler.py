import asyncio
import random
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
import aiohttp

class ErrorType(Enum):
    """Classification of different error types"""
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_CLIENT_ERROR = "http_client_error"  # 4xx
    HTTP_SERVER_ERROR = "http_server_error"  # 5xx
    RATE_LIMITED = "rate_limited"  # 429
    PARSING_ERROR = "parsing_error"
    SCREENSHOT_ERROR = "screenshot_error"
    STORAGE_ERROR = "storage_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: List[ErrorType] = None

    def __post_init__(self):
        if self.retryable_errors is None:
            self.retryable_errors = [
                ErrorType.NETWORK_TIMEOUT,
                ErrorType.CONNECTION_ERROR,
                ErrorType.HTTP_SERVER_ERROR,
                ErrorType.RATE_LIMITED
            ]

@dataclass
class ErrorInfo:
    """Information about an error occurrence"""
    url: str
    error_type: ErrorType
    status_code: Optional[int]
    message: str
    timestamp: float
    attempt: int
    response_time: Optional[float] = None

class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.reset()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    def record_failure(self):
        """Record a failure and update circuit breaker state"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logging.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def reset(self):
        """Reset circuit breaker to closed state"""
        self.failure_count = 0
        self.state = "closed"
        logging.info("Circuit breaker reset to closed state")

class ErrorHandler:
    """Comprehensive error handling and retry system"""

    def __init__(self, retry_config: RetryConfig = None):
        self.retry_config = retry_config or RetryConfig()
        self.error_history: List[ErrorInfo] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)
        self.failed_urls: Dict[str, List[ErrorInfo]] = defaultdict(list)

    def classify_error(self, error: Exception, status_code: Optional[int] = None) -> ErrorType:
        """Classify an error into appropriate error type"""
        if isinstance(error, asyncio.TimeoutError):
            return ErrorType.NETWORK_TIMEOUT
        elif isinstance(error, aiohttp.ClientConnectorError):
            return ErrorType.CONNECTION_ERROR
        elif status_code:
            if status_code == 429:
                return ErrorType.RATE_LIMITED
            elif 400 <= status_code < 500:
                return ErrorType.HTTP_CLIENT_ERROR
            elif 500 <= status_code < 600:
                return ErrorType.HTTP_SERVER_ERROR
        elif "parsing" in str(error).lower():
            return ErrorType.PARSING_ERROR
        elif "screenshot" in str(error).lower():
            return ErrorType.SCREENSHOT_ERROR
        elif "storage" in str(error).lower():
            return ErrorType.STORAGE_ERROR

        return ErrorType.UNKNOWN_ERROR

    def is_retryable(self, error_type: ErrorType, attempt: int) -> bool:
        """Determine if an error should be retried"""
        if attempt >= self.retry_config.max_attempts:
            return False

        return error_type in self.retry_config.retryable_errors

    def calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """Calculate delay before retry using exponential backoff with jitter"""
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base ** (attempt - 1)
        )

        # Special handling for rate limiting
        if error_type == ErrorType.RATE_LIMITED:
            delay *= 2  # Extra delay for rate limiting

        # Apply maximum delay limit
        delay = min(delay, self.retry_config.max_delay)

        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            jitter = delay * 0.1 * random.random()
            delay += jitter

        return delay

    async def execute_with_retry(
        self,
        func: Callable,
        url: str,
        *args,
        domain: str = None,
        **kwargs
    ) -> Any:
        """Execute a function with retry logic and circuit breaker protection"""
        domain = domain or url.split("//")[1].split("/")[0] if "//" in url else "unknown"
        circuit_breaker = self.circuit_breakers[domain]

        for attempt in range(1, self.retry_config.max_attempts + 1):
            start_time = time.time()
            error_info = None

            try:
                # Use circuit breaker for the function call
                result = await circuit_breaker.call(func, *args, **kwargs)

                # Success - reset any previous failures for this URL
                if url in self.failed_urls:
                    del self.failed_urls[url]

                return result

            except Exception as error:
                response_time = time.time() - start_time
                status_code = getattr(error, 'status', None)
                error_type = self.classify_error(error, status_code)

                error_info = ErrorInfo(
                    url=url,
                    error_type=error_type,
                    status_code=status_code,
                    message=str(error),
                    timestamp=time.time(),
                    attempt=attempt,
                    response_time=response_time
                )

                self.error_history.append(error_info)
                self.failed_urls[url].append(error_info)

                # Log the error
                log_level = logging.WARNING if attempt < self.retry_config.max_attempts else logging.ERROR
                logging.log(
                    log_level,
                    f"Attempt {attempt}/{self.retry_config.max_attempts} failed for {url}: "
                    f"{error_type.value} - {error}"
                )

                # Check if we should retry
                if not self.is_retryable(error_type, attempt):
                    logging.error(f"Non-retryable error or max attempts reached for {url}")
                    raise error

                # Calculate and apply delay before retry
                if attempt < self.retry_config.max_attempts:
                    delay = self.calculate_delay(attempt, error_type)
                    logging.info(f"Retrying {url} in {delay:.1f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    raise error

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered"""
        if not self.error_history:
            return {"total_errors": 0}

        error_counts = defaultdict(int)
        domain_errors = defaultdict(int)

        for error in self.error_history:
            error_counts[error.error_type.value] += 1
            domain = error.url.split("//")[1].split("/")[0] if "//" in error.url else "unknown"
            domain_errors[domain] += 1

        failed_urls_count = len(self.failed_urls)
        total_errors = len(self.error_history)

        # Calculate success rate
        recent_errors = [e for e in self.error_history if time.time() - e.timestamp < 300]  # Last 5 minutes

        return {
            "total_errors": total_errors,
            "failed_urls": failed_urls_count,
            "error_types": dict(error_counts),
            "domain_errors": dict(domain_errors),
            "recent_errors": len(recent_errors),
            "circuit_breaker_states": {
                domain: cb.state for domain, cb in self.circuit_breakers.items()
            }
        }

    def get_failed_urls(self) -> List[str]:
        """Get list of URLs that ultimately failed after all retries"""
        return list(self.failed_urls.keys())

    def reset_domain_failures(self, domain: str):
        """Reset circuit breaker and error history for a domain"""
        if domain in self.circuit_breakers:
            self.circuit_breakers[domain].reset()

        # Remove errors for this domain from history
        self.error_history = [
            e for e in self.error_history
            if domain not in e.url
        ]