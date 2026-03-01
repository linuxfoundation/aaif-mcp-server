from __future__ import annotations
"""MCP Resource: member:// — Member organization profiles.

URI patterns:
  member://aaif/{org_id}        → Full member profile (org + contacts + entitlements)
  member://aaif/list             → All AAIF members (summary)
"""

from ..connectors.salesforce import SalesforceConnector
from ..config import TIER_ENTITLEMENTS

sfdc: SalesforceConnector = SalesforceConnector()


async def get_member_profile(org_id: str, foundation_id: str = "aaif") -> dict:
    """Return full member profile for an org."""
    org = await sfdc.get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    entitlements = TIER_ENTITLEMENTS.get(foundation_id, {}).get(org.tier.value)

    return {
        "org": org.model_dump(mode="json"),
        "entitlements": entitlements.model_dump(mode="json") if entitlements else None,
        "contact_count": len(org.contacts),
    }


async def list_members(foundation_id: str = "aaif") -> dict:
    """Return summary list of all members."""
    orgs = await sfdc.list_orgs(foundation_id)
    return {
        "foundation_id": foundation_id,
        "total": len(orgs),
        "members": [
            {
                "org_id": o.org_id,
                "org_name": o.org_name,
                "tier": o.tier.value,
                "status": o.status,
                "country": o.country,
                "contact_count": len(o.contacts),
            }
            for o in orgs
        ],
    }
