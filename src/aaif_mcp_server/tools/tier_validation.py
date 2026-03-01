from __future__ import annotations
"""Domain 4: Membership Tier Validation — 3 tools.

Maps to: Deliverable D1 (Agreement & Activation) + D2 (Membership Record)
PRD Requirements: TIER-1 through TIER-5

These tools validate membership tiers against Salesforce, return entitlement
matrices, and detect anomalies where provisioned access doesn't match tier.
"""

from ..connectors.registry import get_sfdc
from ..config import TIER_ENTITLEMENTS, PROVISIONING_RULES, MOCK_LIST_SUBSCRIPTIONS
from ..models import TierAnomaly, TierValidationResult


async def validate_membership_tier(org_id: str, foundation_id: str = "aaif") -> dict:
    """Look up organization's current membership tier from Salesforce and return
    entitlements, contract expiry, and any anomalies.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Tier validation result with entitlements and any detected anomalies.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {
            "error": "ORG_NOT_FOUND",
            "message": f"No organization found with ID '{org_id}' in foundation '{foundation_id}'",
            "org_id": org_id,
        }

    # Get entitlements for this tier
    foundation_tiers = TIER_ENTITLEMENTS.get(foundation_id, {})
    entitlements = foundation_tiers.get(org.tier.value)
    if not entitlements:
        return {
            "error": "TIER_NOT_FOUND",
            "message": f"Tier '{org.tier.value}' not configured for foundation '{foundation_id}'",
            "org_id": org_id,
            "tier": org.tier.value,
        }

    # Check for anomalies
    anomalies = []
    if org.status != "active":
        anomalies.append(f"Organization status is '{org.status}', not 'active'")
    if org.contract_expiry and org.contract_expiry.timestamp() < __import__("time").time():
        anomalies.append(f"Contract expired on {org.contract_expiry.isoformat()}")

    result = TierValidationResult(
        org_id=org.org_id,
        org_name=org.org_name,
        tier=org.tier,
        foundation_id=foundation_id,
        status=org.status,
        contract_expiry=org.contract_expiry,
        entitlements=entitlements,
        anomalies=anomalies,
    )
    return result.model_dump(mode="json")


async def check_tier_entitlements(tier: str, foundation_id: str = "aaif") -> dict:
    """Return the entitlement matrix for a membership tier — what board seats,
    voting rights, WG chair eligibility, and resource access the tier grants.

    Args:
        tier: Membership tier (gold, silver, platinum)
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Complete entitlement matrix for the specified tier.
    """
    # Normalize tier name
    tier_lower = tier.lower().strip()

    # Handle deprecated tier names
    deprecated_map = {"associate": None, "academic": None}
    if tier_lower in deprecated_map:
        return {
            "error": "DEPRECATED_TIER",
            "message": f"The '{tier}' tier is deprecated for AAIF. Current tiers: Platinum, Gold, Silver.",
            "suggestion": "Use 'gold' or 'silver' for standard membership, or 'platinum' for top-tier.",
        }

    foundation_tiers = TIER_ENTITLEMENTS.get(foundation_id, {})
    entitlements = foundation_tiers.get(tier_lower)
    if not entitlements:
        available = list(foundation_tiers.keys())
        return {
            "error": "TIER_NOT_FOUND",
            "message": f"Tier '{tier}' not found for foundation '{foundation_id}'",
            "available_tiers": available,
        }

    return entitlements.model_dump(mode="json")


async def detect_tier_anomalies(foundation_id: str = "aaif") -> dict:
    """Scan all members for mismatches between stated tier and provisioned access.

    For example: a Silver member with Gold-level Slack channels, or a Gold member
    missing their governing-board mailing list subscription.

    Args:
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of anomalies with severity and suggested fixes.
    """
    orgs = await get_sfdc().list_orgs(foundation_id)
    anomalies: list[dict] = []

    rules_config = PROVISIONING_RULES.get(foundation_id)
    if not rules_config:
        return {"error": "NO_RULES", "message": f"No provisioning rules for '{foundation_id}'"}

    for org in orgs:
        if org.status != "active":
            continue

        for contact in org.contacts:
            # Find applicable rules for this tier + role
            expected_lists = set()
            for rule in rules_config.rules:
                if rule.tier == org.tier and rule.role == contact.role:
                    expected_lists.update(rule.resources)

            # Check actual subscriptions (mock data)
            actual_lists = set(MOCK_LIST_SUBSCRIPTIONS.get(contact.email, []))

            missing = expected_lists - actual_lists
            extra = actual_lists - expected_lists

            if missing:
                anomalies.append(TierAnomaly(
                    org_id=org.org_id, org_name=org.org_name, tier=org.tier,
                    anomaly_type="MISSING_ACCESS",
                    description=f"{contact.name} ({contact.role.value}) missing: {', '.join(missing)}",
                    severity="high" if "governing-board" in str(missing) else "medium",
                ).model_dump(mode="json"))

            if extra:
                anomalies.append(TierAnomaly(
                    org_id=org.org_id, org_name=org.org_name, tier=org.tier,
                    anomaly_type="EXCESS_ACCESS",
                    description=f"{contact.name} ({contact.role.value}) has extra: {', '.join(extra)}",
                    severity="medium",
                ).model_dump(mode="json"))

    return {
        "foundation_id": foundation_id,
        "total_members_scanned": len(orgs),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies,
    }
