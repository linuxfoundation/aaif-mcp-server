from __future__ import annotations
"""AAIF Member Onboarding MCP Server — main entry point.

Registers all tools, resources, and prompts with the FastMCP framework.
Supports two transports:
  - stdio  (default, for Claude Desktop / Claude Code)
  - streamable-http (for web-based MCP clients)

Usage:
  # Claude Desktop (stdio)
  python -m aaif_mcp_server.server

  # Streamable HTTP
  AAIF_MCP_TRANSPORT=streamable-http python -m aaif_mcp_server.server
"""

import json
import logging
import os

from mcp.server.fastmcp import FastMCP

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=os.environ.get("AAIF_MCP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aaif_mcp_server")


# ── Server Instance ───────────────────────────────────────────────
mcp = FastMCP(
    "AAIF Member Onboarding",
    instructions=(
        "MCP server for the AI & Agentic Infrastructure Foundation (AAIF) "
        "member onboarding workflow. Provides 16 tools across 4 domains: "
        "Tier Validation, Compliance & Sanctions, Mailing List Provisioning, "
        "and Orchestration/Silo Reconciliation."
    ),
)


# ═══════════════════════════════════════════════════════════════════
# TOOLS — 16 tools across 4 domains
# ═══════════════════════════════════════════════════════════════════

# ── Domain 4: Tier Validation (3 tools) ───────────────────────────
from .tools.tier_validation import (
    validate_membership_tier,
    check_tier_entitlements,
    detect_tier_anomalies,
)

@mcp.tool()
async def tool_validate_membership_tier(org_id: str, foundation_id: str = "aaif") -> str:
    """Look up an organization's membership tier from Salesforce and return
    entitlements, contract expiry, and any anomalies.

    Args:
        org_id: Salesforce organization ID (e.g., '0017V00001HITACHI')
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await validate_membership_tier(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_check_tier_entitlements(tier: str, foundation_id: str = "aaif") -> str:
    """Return the entitlement matrix for a membership tier — board seats,
    voting rights, WG chair eligibility, mailing lists, and pricing.

    Args:
        tier: Membership tier name (platinum, gold, silver)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await check_tier_entitlements(tier, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_detect_tier_anomalies(foundation_id: str = "aaif") -> str:
    """Scan all members for mismatches between stated tier and provisioned access.
    Detects cases like Silver members with Gold-level access or Gold members
    missing their governing-board list subscription.

    Args:
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await detect_tier_anomalies(foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 3: Compliance & Sanctions (4 tools) ───────────────────
from .tools.compliance import (
    check_sanctions,
    check_tax_exempt_status,
    get_compliance_report,
    flag_compliance_issue,
)

@mcp.tool()
async def tool_check_sanctions(org_name: str, country: str, org_id: str = "") -> str:
    """Look up sanctions screening status from Salesforce/Descartes.

    OFAC screening is handled natively in SFDC via the Descartes integration
    at membership intake. This tool retrieves the result from SFDC.

    Args:
        org_name: Organization legal name to screen
        country: Country code (ISO 3166-1 alpha-2, e.g., 'US', 'JP', 'GB')
        org_id: Optional Salesforce org ID for enhanced lookup
    """
    result = await check_sanctions(org_name, country, org_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_check_tax_exempt_status(org_id: str) -> str:
    """Verify 501(c)(6) tax-exempt compliance for a member organization.
    The Linux Foundation operates as a 501(c)(6) trade association.

    Args:
        org_id: Salesforce organization ID
    """
    result = await check_tax_exempt_status(org_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_compliance_report(org_id: str) -> str:
    """Full compliance summary — sanctions screening, tax-exempt status,
    and any open compliance issues for a member organization.

    Args:
        org_id: Salesforce organization ID
    """
    result = await get_compliance_report(org_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_flag_compliance_issue(org_id: str, issue_type: str, details: str) -> str:
    """Raise a compliance issue for human review. Creates a ticket in the
    compliance tracking system.

    Args:
        org_id: Salesforce organization ID
        issue_type: Type of issue (sanctions_match, tax_exempt_concern, legal_question, other)
        details: Detailed description of the compliance concern
    """
    result = await flag_compliance_issue(org_id, issue_type, details)
    return json.dumps(result, indent=2, default=str)


# ── Domain 1: Mailing List Provisioning (4 tools) ────────────────
from .tools.mailing_list import (
    provision_mailing_lists,
    remove_from_mailing_lists,
    check_mailing_list_membership,
    remediate_mailing_lists,
)

@mcp.tool()
async def tool_provision_mailing_lists(
    org_id: str, contact_email: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Provision a contact onto the correct mailing lists based on their org's
    tier and role. Uses rule-based provisioning engine.

    IMPORTANT: Defaults to dry_run=True. Confirm with user before setting
    dry_run=False to actually make changes.

    Args:
        org_id: Salesforce organization ID
        contact_email: Email address of the contact to provision
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await provision_mailing_lists(org_id, contact_email, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_remove_from_mailing_lists(
    org_id: str, contact_email: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Remove a contact from all mailing lists. Used during offboarding,
    contact changes, or tier downgrades.

    Args:
        org_id: Salesforce organization ID
        contact_email: Email address to remove
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await remove_from_mailing_lists(org_id, contact_email, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_check_mailing_list_membership(
    contact_email: str, foundation_id: str = "aaif"
) -> str:
    """Check which mailing lists a contact is subscribed to across the foundation.

    Args:
        contact_email: Email address to check
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await check_mailing_list_membership(contact_email, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_remediate_mailing_lists(
    foundation_id: str = "aaif", dry_run: bool = True
) -> str:
    """Scan all members and fix mailing list gaps — add missing subscriptions
    and flag excess subscriptions based on provisioning rules.

    This is the drift-remediation tool for mailing lists.

    Args:
        foundation_id: Foundation identifier (default: aaif)
        dry_run: If True, report gaps without making changes (default: True)
    """
    result = await remediate_mailing_lists(foundation_id, dry_run)
    return json.dumps(result, indent=2, default=str)


# ── Domain 12: Orchestrator (5 tools) ────────────────────────────
from .tools.orchestrator import (
    run_onboarding_checklist,
    get_onboarding_status,
    reconcile_silos,
    run_offboarding_checklist,
    get_silo_health,
)

@mcp.tool()
async def tool_run_onboarding_checklist(
    org_id: str, contact_id: str, foundation_id: str = "aaif", dry_run: bool = True
) -> str:
    """Execute the full D1-D5 onboarding checklist for a new member contact.
    Runs each step, calling mapped tools (if automated) and tracking results.

    IMPORTANT: Defaults to dry_run=True. Set dry_run=False to actually execute
    the checklist steps.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID being onboarded
        foundation_id: Foundation identifier (default: aaif)
        dry_run: If True, simulate without executing (default: True)
    """
    result = await run_onboarding_checklist(org_id, contact_id, foundation_id, dry_run)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_onboarding_status(org_id: str, contact_id: str) -> str:
    """Get the current onboarding status for a member contact — which
    deliverables are complete, in progress, or pending.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to check
    """
    result = await get_onboarding_status(org_id, contact_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_reconcile_silos(org_id: str, foundation_id: str = "aaif") -> str:
    """Compare data across Salesforce, Groups.io, and other systems to detect
    discrepancies for a specific organization. Checks contacts, list access,
    and tier entitlements.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await reconcile_silos(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_run_offboarding_checklist(
    org_id: str, contact_email: str, reason: str = "membership_cancelled",
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Execute offboarding for a member contact — remove from mailing lists,
    revoke access, and flag manual follow-up steps.

    Args:
        org_id: Salesforce organization ID
        contact_email: Email of the contact being offboarded
        reason: Reason (membership_cancelled, tier_downgrade, contact_inactive)
        dry_run: If True, show what would change without executing (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await run_offboarding_checklist(org_id, contact_email, reason, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_silo_health(foundation_id: str = "aaif") -> str:
    """Foundation-wide silo health report — how well-synced are all systems?
    Returns an aggregate health score, member sync status, and top issues.

    Args:
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_silo_health(foundation_id)
    return json.dumps(result, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════
# RESOURCES — 3 resource groups
# ═══════════════════════════════════════════════════════════════════

from .resources.member import get_member_profile, list_members
from .resources.checklist import get_checklist_template, get_deliverable_template
from .resources.rules import get_provisioning_rules, get_tier_entitlements, get_working_groups


@mcp.resource("member://aaif/{org_id}")
async def resource_member_profile(org_id: str) -> str:
    """Member organization profile — org details, contacts, and entitlements."""
    result = await get_member_profile(org_id)
    return json.dumps(result, indent=2, default=str)


@mcp.resource("member://aaif/list")
async def resource_member_list() -> str:
    """All AAIF members — summary list with tier, status, and contact count."""
    result = await list_members("aaif")
    return json.dumps(result, indent=2, default=str)


@mcp.resource("checklist://aaif")
async def resource_checklist() -> str:
    """Full D1-D5 onboarding checklist template for AAIF."""
    result = await get_checklist_template("aaif")
    return json.dumps(result, indent=2, default=str)


@mcp.resource("checklist://aaif/{deliverable_id}")
async def resource_deliverable(deliverable_id: str) -> str:
    """Single deliverable checklist (e.g., D1, D3, D5)."""
    result = await get_deliverable_template(deliverable_id, "aaif")
    return json.dumps(result, indent=2, default=str)


@mcp.resource("rules://aaif/provisioning")
async def resource_provisioning_rules() -> str:
    """All provisioning rules — maps tier + role to mailing lists and resources."""
    result = await get_provisioning_rules("aaif")
    return json.dumps(result, indent=2, default=str)


@mcp.resource("rules://aaif/tiers")
async def resource_tier_entitlements() -> str:
    """All tier entitlements — Platinum, Gold, Silver matrices."""
    result = await get_tier_entitlements("aaif")
    return json.dumps(result, indent=2, default=str)


@mcp.resource("rules://aaif/working-groups")
async def resource_working_groups() -> str:
    """All AAIF working groups — names, schedules, mailing lists, Discord channels."""
    result = await get_working_groups("aaif")
    return json.dumps(result, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════
# PROMPTS — 3 starter prompts for common workflows
# ═══════════════════════════════════════════════════════════════════

@mcp.prompt()
def onboard_new_member(org_name: str) -> str:
    """Step-by-step onboarding prompt for a new AAIF member organization."""
    return f"""You are onboarding a new AAIF member: {org_name}.

Follow these steps in order:

1. **Validate Membership**: Use tool_validate_membership_tier to confirm the org's tier and entitlements.
2. **Compliance Screening**: Use tool_check_sanctions to verify the org's sanctions status (handled by Descartes in SFDC at intake). If flagged, STOP and route to compliance team.
3. **Check Tax-Exempt Status**: Use tool_check_tax_exempt_status if applicable.
4. **Provision Mailing Lists**: For each contact, use tool_provision_mailing_lists with dry_run=True first. Show the user the plan, then run with dry_run=False after confirmation.
5. **Run Full Checklist**: Use tool_run_onboarding_checklist with dry_run=True to see the full D1-D5 status.
6. **Reconcile Silos**: Use tool_reconcile_silos to verify everything is in sync.

IMPORTANT: Always show dry_run results first. Never auto-execute without human confirmation.
"""


@mcp.prompt()
def check_deliverable_status(org_id: str, deliverable: str = "all") -> str:
    """Check onboarding status for a specific deliverable or all deliverables."""
    return f"""Check the onboarding status for org '{org_id}'.

{'Check all deliverables (D1-D5).' if deliverable == 'all' else f'Focus on deliverable {deliverable}.'}

Steps:
1. Use tool_get_onboarding_status to see current progress.
2. If not started, use tool_run_onboarding_checklist with dry_run=True to generate the checklist.
3. For any incomplete items, explain what's needed and which tools to use.
4. Use tool_reconcile_silos to check for data consistency issues.
"""


@mcp.prompt()
def diagnose_access(contact_email: str) -> str:
    """Diagnose and fix access issues for a member contact."""
    return f"""A member contact ({contact_email}) may have access issues.

Diagnostic steps:
1. Use tool_check_mailing_list_membership to see current subscriptions.
2. Look up their org to find their tier and role.
3. Compare actual vs expected access using provisioning rules (read rules://aaif/provisioning).
4. If gaps exist, use tool_provision_mailing_lists with dry_run=True to show the fix.
5. Use tool_detect_tier_anomalies to check for broader issues.
6. Summarize findings and recommended actions.
"""


# ═══════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════

def main():
    """Run the MCP server."""
    transport = os.environ.get("AAIF_MCP_TRANSPORT", "stdio")
    logger.info(f"Starting AAIF MCP Server v0.1.0 (transport={transport})")
    logger.info("Registered 16 tools, 7 resources, 3 prompts")

    if transport == "streamable-http":
        import uvicorn
        host = os.environ.get("FASTMCP_HOST", "0.0.0.0")
        port = int(os.environ.get("FASTMCP_PORT", os.environ.get("PORT", "8080")))
        logger.info(f"Binding to {host}:{port}")
        app = mcp.streamable_http_app()
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
