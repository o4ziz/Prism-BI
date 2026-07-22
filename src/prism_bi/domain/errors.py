"""Typed domain errors."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain failures."""

    def __init__(self, message: str, *, code: str = "domain_error") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(DomainError):
    """Invalid domain input or invariant violation."""

    def __init__(self, message: str, *, code: str = "validation_error") -> None:
        super().__init__(message, code=code)
