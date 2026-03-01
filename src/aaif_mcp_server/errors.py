"""Structured error handling for AAIF MCP Server.

Defines a hierarchy of domain-specific exceptions that can be caught,
logged, and converted to standardized error responses.
"""

from __future__ import annotations


class AAIFError(Exception):
    """Base exception class for all AAIF MCP Server errors.

    Attributes:
        error_code: Machine-readable error identifier (e.g., "ORG_NOT_FOUND")
        message: Human-readable error description
    """

    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert error to dictionary for JSON responses."""
        return {"error": self.error_code, "message": self.message}


class OrgNotFoundError(AAIFError):
    """Raised when a requested organization is not found in Salesforce or mock data."""

    def __init__(self, org_id: str):
        super().__init__(
            "ORG_NOT_FOUND",
            f"Organization with ID '{org_id}' not found"
        )


class ContactNotFoundError(AAIFError):
    """Raised when a requested contact is not found for an organization."""

    def __init__(self, contact_id: str, org_id: str | None = None):
        if org_id:
            msg = f"Contact '{contact_id}' not found in organization '{org_id}'"
        else:
            msg = f"Contact with ID '{contact_id}' not found"
        super().__init__("CONTACT_NOT_FOUND", msg)


class TierNotFoundError(AAIFError):
    """Raised when a requested membership tier is not defined."""

    def __init__(self, tier: str, foundation_id: str = "aaif"):
        super().__init__(
            "TIER_NOT_FOUND",
            f"Tier '{tier}' not found for foundation '{foundation_id}'"
        )


class ConnectorError(AAIFError):
    """Raised when a connector (Salesforce, Groups.io, etc.) operation fails."""

    def __init__(self, connector_name: str, operation: str, details: str = ""):
        message = f"{connector_name} connector failed during {operation}"
        if details:
            message += f": {details}"
        super().__init__("CONNECTOR_ERROR", message)


class ValidationError(AAIFError):
    """Raised when input data fails validation."""

    def __init__(self, field: str, reason: str):
        super().__init__(
            "VALIDATION_ERROR",
            f"Validation failed for field '{field}': {reason}"
        )
