import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryExhaustedError(RuntimeError):
    pass


def retry_call(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay_seconds: float = 0.25,
    backoff_multiplier: float = 2.0,
    retryable_exceptions: tuple[
        type[Exception],
        ...,
    ] = (
        OSError,
        TimeoutError,
        ConnectionError,
    ),
) -> tuple[T, int]:
    if attempts <= 0:
        raise ValueError("attempts must be greater than zero")

    delay = initial_delay_seconds

    failures = 0

    for attempt in range(
        1,
        attempts + 1,
    ):
        try:
            return (
                operation(),
                failures,
            )

        except retryable_exceptions as exc:
            failures += 1

            if attempt >= attempts:
                raise RetryExhaustedError(f"Operation failed after {attempts} attempts") from exc

            if delay > 0:
                time.sleep(delay)

            delay *= backoff_multiplier

    raise RuntimeError("Unreachable retry state")
