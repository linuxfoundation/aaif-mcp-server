from __future__ import annotations
"""MCP Resource: rules:// — Provisioning rules and tier entitlements.

URI patterns:
  rules://aaif/provisioning     → All provisioning rules
  rules://aaif/tiers            → All tier entitlements
  rules://aaif/working-groups   → All working groups
"""

from ..config import PROVISIONING_RULES, TIER_ENTITLEMENTS, WORKING_GROUPS


async def get_provisioning_rules(foundation_id: str = "aaif") -> dict:
    """Return all provisioning rules for a foundation."""
    config = PROVISIONING_RULES.get(foundation_id)
    if not config:
        return {"error": "NOT_FOUND", "message": f"No rules for '{foundation_id}'"}
    return config.model_dump(mode="json")


async def get_tier_entitlements(foundation_id: str = "aaif") -> dict:
    """Return all tier entitlements for a foundation."""
    tiers = TIER_ENTITLEMENTS.get(foundation_id)
    if not tiers:
        return {"error": "NOT_FOUND", "message": f"No tiers for '{foundation_id}'"}
    return {
        "foundation_id": foundation_id,
        "tiers": {k: v.model_dump(mode="json") for k, v in tiers.items()},
    }


async def get_working_groups(foundation_id: str = "aaif") -> dict:
    """Return all working groups for a foundation."""
    wgs = WORKING_GROUPS.get(foundation_id)
    if not wgs:
        return {"error": "NOT_FOUND", "message": f"No WGs for '{foundation_id}'"}
    return {
        "foundation_id": foundation_id,
        "working_groups": [wg.model_dump(mode="json") for wg in wgs],
    }
