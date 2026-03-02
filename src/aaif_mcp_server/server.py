from __future__ import annotations
"""AAIF PMO Agent — MCP Server entry point.

Registers all tools, resources, and prompts with the FastMCP framework.
Supports two transports:
  - stdio  (default, for Cowork plugin, Goose, local dev)
  - streamable-http (for LFX PCC, Intercom Fin, Agno agents)

Usage:
  # Local / Cowork (stdio)
  python -m aaif_mcp_server.server

  # Streamable HTTP (PCC, Intercom)
  AAIF_MCP_TRANSPORT=streamable-http python -m aaif_mcp_server.server
"""

import json
import logging
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=os.environ.get("AAIF_MCP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aaif_mcp_server")


# ── Server Instance ───────────────────────────────────────────────
# Disable DNS rebinding protection when running behind a reverse proxy
# (Cloud Run, etc.) so external host headers are accepted.
_transport = os.environ.get("AAIF_MCP_TRANSPORT", "stdio")
_security = None
if _transport == "streamable-http":
    _security = TransportSecuritySettings(enable_dns_rebinding_protection=False)

mcp = FastMCP(
    "AAIF Member Onboarding",
    instructions=(
        "MCP server for the AI & Agentic Infrastructure Foundation (AAIF) "
        "member onboarding workflow. Provides 49 tools across 12 domains: "
        "Tier Validation, Compliance & Sanctions, Mailing List Provisioning, "
        "Orchestration/Silo Reconciliation, Contact Role Management, "
        "Calendar & Meeting Management, Working Group Enrollment, "
        "Onboarding Call Scheduling, Election & Voting Operations, "
        "Press Release Drafting, Logo & Brand Validation, "
        "Renewal & Engagement Intelligence, and Health Check."
    ),
    transport_security=_security,
)


# ═══════════════════════════════════════════════════════════════════
# DYNAMIC TOOL REGISTRATION — 48 tools auto-registered from domains
# ═══════════════════════════════════════════════════════════════════

from .tools._registry import register_all_tools

# Register all tools at import time
_registered_tool_count = register_all_tools(mcp)


# ── Health Check ──────────────────────────────────────────────────
# This tool remains special and stays in server.py

@mcp.tool()
async def tool_health_check() -> str:
    """Run a health check across all connectors and return system status.

    Returns connectivity status for each connector (Salesforce, Groups.io,
    Calendar, Discord, GitHub, LFX Platform, HubSpot) plus overall health.
    """
    from .connectors.registry import (
        get_sfdc, get_groupsio, get_calendar,
        get_discord, get_github, get_lfx, get_hubspot,
    )

    checks = {}
    connectors = {
        "salesforce": get_sfdc,
        "groupsio": get_groupsio,
        "calendar": get_calendar,
        "discord": get_discord,
        "github": get_github,
        "lfx_platform": get_lfx,
        "hubspot": get_hubspot,
    }

    all_healthy = True
    for name, getter in connectors.items():
        try:
            connector = getter()
            result = await connector.health_check()
            checks[name] = result
            if result.get("status") != "healthy":
                all_healthy = False
        except Exception as e:
            checks[name] = {"status": "error", "error": str(e)}
            all_healthy = False

    return json.dumps({
        "overall_status": "healthy" if all_healthy else "degraded",
        "connectors": checks,
        "tool_count": 49,
        "domain_count": 12,
    }, indent=2, default=str)


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

async def _initialize():
    """Initialize all connectors at server startup."""
    from .connectors.registry import initialize_connectors
    await initialize_connectors()


def main():
    """Run the MCP server."""
    import asyncio
    transport = os.environ.get("AAIF_MCP_TRANSPORT", "stdio")
    logger.info(f"Starting AAIF MCP Server v0.1.0 (transport={transport})")
    logger.info(f"Registered {_registered_tool_count + 1} tools, 7 resources, 3 prompts")

    # Initialize all 7 connectors before starting the server
    asyncio.run(_initialize())
    logger.info("Connector registry initialized")

    if transport == "streamable-http":
        import uvicorn
        host = os.environ.get("FASTMCP_HOST", "0.0.0.0")
        port = int(os.environ.get("FASTMCP_PORT", os.environ.get("PORT", "8080")))
        logger.info(f"Binding to {host}:{port}")
        app = mcp.streamable_http_app()
        uvicorn.run(
            app, host=host, port=port,
            proxy_headers=True, forwarded_allow_ips="*",
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
