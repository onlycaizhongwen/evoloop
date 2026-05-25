from __future__ import annotations


class DomainError(Exception):
    """Base domain error."""


class SafetyViolation(DomainError):
    """Raised when a task violates safety policy."""


class MalformedReview(DomainError):
    """Raised when review output cannot be trusted."""

    def __init__(self, reason: str, expected: str | None = None, actual: str | None = None):
        self.reason = reason
        self.expected = expected
        self.actual = actual
        message = reason
        if expected is not None or actual is not None:
            message = f"{reason}: expected={expected!r}, actual={actual!r}"
        super().__init__(message)
