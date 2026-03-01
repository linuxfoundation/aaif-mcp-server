from __future__ import annotations
"""Authentication & authorization layer.

Wraps the LFX auth system:
- Service-to-service: API key + SFDC org context
- User-delegated: OAuth 2.0 via LFX SSO
- Tool-level ACL: role-based access control per tool

For Phase 1, this provides the scaffold. Production implementation
will integrate with LFX SSO and the PCC permission model.
"""

import functools
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ── Auth Configuration ─────────────────────────────────────────────

class AuthConfig:
    """Server-level auth configuration loaded from environment."""

    def __init__(self):
        self.api_key = os.environ.get("AAIF_MCP_API_KEY", "dev-key-not-for-production")
        self.lf_sso_client_id = os.environ.get("LF_SSO_CLIENT_ID", "")
        self.lf_sso_client_secret = os.environ.get("LF_SSO_CLIENT_SECRET", "")
        self.enforce_auth = os.environ.get("AAIF_MCP_ENFORCE_AUTH", "false").lower() == "true"

    @property
    def is_dev_mode(self) -> bool:
        return not self.enforce_auth


# Global auth config (initialized on server start)
auth_config = AuthConfig()


# ── Role Definitions ───────────────────────────────────────────────

ROLES = {
    "pmo_admin": "PMO administrator — full access to all tools",
    "foundation_ed": "Foundation Executive Director — full access",
    "membership_manager": "Membership team — intake, tier validation, compliance",
    "operations_manager": "Operations — provisioning, WG management, elections",
    "member_self_service": "Member — limited to own org's data via Org Dashboard",
    "readonly": "Read-only access to resources",
}


# ── Current User Context ──────────────────────────────────────────

class UserContext:
    """Represents the authenticated user for the current request."""

    def __init__(
        self,
        user_id: str = "dev-user",
        email: str = "dev@linuxfoundation.org",
        roles: Optional[list[str]] = None,
        org_id: Optional[str] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.roles = roles or ["pmo_admin"]  # Dev mode: full access
        self.org_id = org_id

    def has_role(self, role: str) -> bool:
        return role in self.roles or "pmo_admin" in self.roles

    def can_access_org(self, org_id: str) -> bool:
        """Check if user can access data for this org."""
        if self.has_role("pmo_admin") or self.has_role("foundation_ed"):
            return True
        return self.org_id == org_id


# Default dev context
_current_user = UserContext()


def get_current_user() -> UserContext:
    """Return the current authenticated user context."""
    return _current_user


def set_current_user(user: UserContext) -> None:
    """Set the current user context (called during auth middleware)."""
    global _current_user
    _current_user = user


# ── Tool-Level ACL ─────────────────────────────────────────────────

def requires_role(*roles: str):
    """Decorator to enforce role-based access on tool functions.

    Usage:
        @requires_role("pmo_admin", "membership_manager")
        async def validate_membership_tier(org_id: str) -> dict:
            ...

    In dev mode (AAIF_MCP_ENFORCE_AUTH=false), all access is allowed.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not auth_config.is_dev_mode:
                user = get_current_user()
                if not any(user.has_role(r) for r in roles):
                    return {
                        "error": "ACCESS_DENIED",
                        "message": f"This tool requires one of: {', '.join(roles)}",
                        "user_roles": user.roles,
                    }
            return await func(*args, **kwargs)
        # Preserve original function metadata for MCP tool registration
        wrapper.__tool_roles__ = roles
        return wrapper
    return decorator
