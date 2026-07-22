"""Application-layer operation results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class OperationResult(Generic[T]):
    """Standard application result wrapper."""

    success: bool
    value: T | None = None
    error_code: str | None = None
    message: str | None = None
    correlation_id: str | None = None
    retryable: bool = False

    @staticmethod
    def ok(value: T, *, correlation_id: str | None = None) -> OperationResult[T]:
        """Successful result."""
        return OperationResult(success=True, value=value, correlation_id=correlation_id)

    @staticmethod
    def fail(
        *,
        error_code: str,
        message: str,
        correlation_id: str | None = None,
        retryable: bool = False,
    ) -> OperationResult[T]:
        """Failed result."""
        return OperationResult(
            success=False,
            error_code=error_code,
            message=message,
            correlation_id=correlation_id,
            retryable=retryable,
        )
