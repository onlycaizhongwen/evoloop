from __future__ import annotations


class InfrastructureError(Exception):
    """Base infrastructure error."""


class AgentCommandError(InfrastructureError):
    """Raised when an external agent command fails."""
