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
from mcp.server.transport_security import TransportSecuritySettings

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=os.environ.get("AAIF_MCP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("aaif_mcp_server")


# ── Server Instance ───────────────────────────────────────────────
# Disable DNS rebinding protection when running behind a reverse proxy
# (Railway, Cloud Run, etc.) so external host headers are accepted.
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
# TOOLS — 49 tools across 12 domains
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


# ── Domain 5: Contact Role Management (5 tools) ─────────────────
from .tools.contact_roles import (
    list_contacts,
    add_contact,
    update_contact_role,
    remove_contact,
    transfer_voting_rights,
)

@mcp.tool()
async def tool_list_contacts(org_id: str, foundation_id: str = "aaif") -> str:
    """List all contacts for an organization with their roles, emails,
    and downstream system access.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await list_contacts(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_add_contact(
    org_id: str, name: str, email: str, role: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Add a new contact to an organization. Triggers downstream provisioning
    (mailing lists, calendar invites, WG enrollment) based on role.

    IMPORTANT: Defaults to dry_run=True. Confirm with user before executing.

    Args:
        org_id: Salesforce organization ID
        name: Contact full name
        email: Contact email address
        role: Contact role (voting_contact, alternate_contact, technical_contact, billing_contact, marketing_contact, primary_contact)
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await add_contact(org_id, name, email, role, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_update_contact_role(
    org_id: str, contact_id: str, new_role: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Update a contact's role within their organization. Shows downstream
    effects on mailing lists, calendar invites, and WG access.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to update
        new_role: New role to assign
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await update_contact_role(org_id, contact_id, new_role, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_remove_contact(
    org_id: str, contact_id: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Remove a contact from an organization, triggering offboarding actions
    (mailing list removal, calendar cancellation, WG exit).

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to remove
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await remove_contact(org_id, contact_id, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_transfer_voting_rights(
    org_id: str, from_contact_id: str, to_contact_id: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Transfer voting rights from one contact to another within the same org.

    Args:
        org_id: Salesforce organization ID
        from_contact_id: Contact ID giving up voting rights
        to_contact_id: Contact ID receiving voting rights
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await transfer_voting_rights(org_id, from_contact_id, to_contact_id, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 2: Calendar & Meeting Management (3 tools) ───────────
from .tools.calendar import (
    provision_calendar_invites,
    update_meeting_schedule,
    get_upcoming_meetings,
)

@mcp.tool()
async def tool_provision_calendar_invites(
    org_id: str, contact_id: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Send calendar invites for all meetings a contact should attend
    based on their tier and role.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to provision invites for
        dry_run: If True, show what would be sent without sending (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await provision_calendar_invites(org_id, contact_id, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_update_meeting_schedule(
    wg_id: str, new_time: str, new_link: str, foundation_id: str = "aaif"
) -> str:
    """Update a working group's recurring meeting schedule (time and/or link).

    Args:
        wg_id: Working group identifier
        new_time: New meeting time (e.g., 'Wednesdays 10:00 AM PT')
        new_link: New meeting link (e.g., Zoom URL)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await update_meeting_schedule(wg_id, new_time, new_link, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_upcoming_meetings(
    contact_id: str, foundation_id: str = "aaif"
) -> str:
    """Get upcoming meetings for a contact based on their calendar invites.

    Args:
        contact_id: Contact ID to look up meetings for
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_upcoming_meetings(contact_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 6: Working Group Enrollment (5 tools) ────────────────
from .tools.wg_enrollment import (
    enroll_in_working_group,
    leave_working_group,
    list_available_working_groups,
    get_wg_members,
    check_wg_eligibility,
)

@mcp.tool()
async def tool_enroll_in_working_group(
    contact_id: str, wg_id: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Enroll a contact in a working group across all systems
    (Groups.io, Discord, GitHub, Calendar).

    Args:
        contact_id: Contact ID to enroll
        wg_id: Working group identifier
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await enroll_in_working_group(contact_id, wg_id, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_leave_working_group(
    contact_id: str, wg_id: str,
    dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Remove a contact from a working group across all systems.

    Args:
        contact_id: Contact ID to remove
        wg_id: Working group identifier
        dry_run: If True, show what would change without making changes (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await leave_working_group(contact_id, wg_id, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_list_available_working_groups(
    contact_id: str, foundation_id: str = "aaif"
) -> str:
    """List all working groups with the contact's current enrollment status
    and eligibility.

    Args:
        contact_id: Contact ID to check enrollment for
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await list_available_working_groups(contact_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_wg_members(wg_id: str, foundation_id: str = "aaif") -> str:
    """Get the full member roster for a working group, including roles
    and organization affiliations.

    Args:
        wg_id: Working group identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_wg_members(wg_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_check_wg_eligibility(
    contact_id: str, wg_id: str, foundation_id: str = "aaif"
) -> str:
    """Check if a contact is eligible to join a working group based on
    their org's tier, role, and current enrollment.

    Args:
        contact_id: Contact ID to check
        wg_id: Working group identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await check_wg_eligibility(contact_id, wg_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 10: Onboarding Call Scheduling (3 tools) ─────────────
from .tools.call_scheduling import (
    schedule_onboarding_call,
    reschedule_onboarding_call,
    get_onboarding_call_status,
)

@mcp.tool()
async def tool_schedule_onboarding_call(
    org_id: str, contact_ids_str: str,
    lf_staff_ids_str: str = "", foundation_id: str = "aaif"
) -> str:
    """Schedule an onboarding call with member contacts and LF staff.
    Finds available time slots and creates calendar invites.

    Args:
        org_id: Salesforce organization ID
        contact_ids_str: Comma-separated contact IDs to include
        lf_staff_ids_str: Comma-separated LF staff IDs (optional, defaults to assigned staff)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await schedule_onboarding_call(org_id, contact_ids_str, lf_staff_ids_str, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_reschedule_onboarding_call(
    meeting_id: str, new_time: str, foundation_id: str = "aaif"
) -> str:
    """Reschedule an existing onboarding call to a new time.

    Args:
        meeting_id: Calendar meeting ID to reschedule
        new_time: New meeting time (ISO 8601 format)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await reschedule_onboarding_call(meeting_id, new_time, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_onboarding_call_status(
    org_id: str, foundation_id: str = "aaif"
) -> str:
    """Get the status of an organization's onboarding call — scheduled,
    completed, pending, or not yet scheduled.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_onboarding_call_status(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 7: Election & Voting Operations (5 tools) ────────────
from .tools.elections import (
    create_election,
    validate_candidate_eligibility,
    check_voter_eligibility,
    get_election_status,
    diagnose_ballot_access,
)

@mcp.tool()
async def tool_create_election(
    wg_id: str, position: str, nomination_end: str,
    voting_start: str, voting_end: str, foundation_id: str = "aaif"
) -> str:
    """Create a new election for a working group position in LFX Platform.

    Args:
        wg_id: Working group identifier
        position: Position title (e.g., 'WG Chair', 'TSC Representative')
        nomination_end: Nomination deadline (ISO 8601 date)
        voting_start: Voting start date (ISO 8601 date)
        voting_end: Voting end date (ISO 8601 date)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await create_election(wg_id, position, nomination_end, voting_start, voting_end, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_validate_candidate_eligibility(
    contact_id: str, election_id: str, foundation_id: str = "aaif"
) -> str:
    """Check if a contact is eligible to be a candidate in an election.
    Verifies LFID, org membership, tier requirements, and WG participation.

    Args:
        contact_id: Contact ID to validate
        election_id: Election identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await validate_candidate_eligibility(contact_id, election_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_check_voter_eligibility(
    contact_id: str, election_id: str, foundation_id: str = "aaif"
) -> str:
    """Check if a contact is eligible to vote in an election.
    Verifies LFID, org membership, and voting-contact role.

    Args:
        contact_id: Contact ID to check
        election_id: Election identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await check_voter_eligibility(contact_id, election_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_election_status(
    election_id: str, foundation_id: str = "aaif"
) -> str:
    """Retrieve election status, timeline, candidates, and vote counts.

    Args:
        election_id: Election identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_election_status(election_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_diagnose_ballot_access(
    contact_id: str, election_id: str, foundation_id: str = "aaif"
) -> str:
    """Diagnostic tool: check all prerequisites for ballot access and
    identify any blockers preventing a contact from voting.

    Args:
        contact_id: Contact ID to diagnose
        election_id: Election identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await diagnose_ballot_access(contact_id, election_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 8: Press Release Drafting (3 tools) ──────────────────
from .tools.press_release import (
    draft_press_release,
    get_press_release_status,
    list_press_release_templates,
)

@mcp.tool()
async def tool_draft_press_release(
    org_id: str, template_id: str = "new-member-announcement",
    foundation_id: str = "aaif"
) -> str:
    """Generate a press release draft from a template, auto-filling
    organization details and membership information.

    Args:
        org_id: Salesforce organization ID
        template_id: Template to use (default: new-member-announcement)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await draft_press_release(org_id, template_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_press_release_status(
    pr_id: str, foundation_id: str = "aaif"
) -> str:
    """Retrieve press release approval workflow status — draft, review,
    approved, or published.

    Args:
        pr_id: Press release identifier
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_press_release_status(pr_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_list_press_release_templates(
    foundation_id: str = "aaif"
) -> str:
    """List all available press release templates with descriptions
    and required fields.

    Args:
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await list_press_release_templates(foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 9: Logo & Brand Validation (3 tools) ─────────────────
from .tools.logo_brand import (
    validate_logo,
    get_brand_guidelines,
    request_logo_upload,
)

@mcp.tool()
async def tool_validate_logo(
    file_url: str, foundation_id: str = "aaif"
) -> str:
    """Validate a logo file against foundation brand guidelines.
    Checks format, dimensions, color space, and file size.

    Args:
        file_url: URL or path to the logo file to validate
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await validate_logo(file_url, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_brand_guidelines(
    foundation_id: str = "aaif"
) -> str:
    """Retrieve brand guidelines and logo requirements for the foundation.

    Args:
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_brand_guidelines(foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_request_logo_upload(
    org_id: str, foundation_id: str = "aaif"
) -> str:
    """Generate a secure, temporary upload URL for an organization
    to submit their logo.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await request_logo_upload(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Domain 11: Renewal & Engagement Intelligence (5 tools) ──────
from .tools.renewal_intelligence import (
    get_renewal_status,
    get_engagement_score,
    predict_churn_risk,
    get_renewal_dashboard,
    trigger_renewal_outreach,
)

@mcp.tool()
async def tool_get_renewal_status(
    org_id: str, foundation_id: str = "aaif"
) -> str:
    """Get contract renewal status — timeline, stage, and recommended actions.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_renewal_status(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_engagement_score(
    org_id: str, foundation_id: str = "aaif"
) -> str:
    """Calculate engagement score (0-100) for a member organization
    based on meeting attendance, WG participation, and GitHub activity.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_engagement_score(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_predict_churn_risk(
    org_id: str, foundation_id: str = "aaif"
) -> str:
    """Predict churn risk (0-100) based on engagement score, renewal
    timeline, and historical patterns.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await predict_churn_risk(org_id, foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_get_renewal_dashboard(
    foundation_id: str = "aaif"
) -> str:
    """Foundation-wide renewal and engagement dashboard — renewal pipeline,
    engagement distribution, churn risk summary, and action items.

    Args:
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await get_renewal_dashboard(foundation_id)
    return json.dumps(result, indent=2, default=str)


@mcp.tool()
async def tool_trigger_renewal_outreach(
    org_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> str:
    """Generate renewal outreach plan with email template, talking points,
    and engagement recommendations.

    IMPORTANT: Defaults to dry_run=True. Confirm with user before executing.

    Args:
        org_id: Salesforce organization ID
        dry_run: If True, show plan without executing (default: True)
        foundation_id: Foundation identifier (default: aaif)
    """
    result = await trigger_renewal_outreach(org_id, dry_run, foundation_id)
    return json.dumps(result, indent=2, default=str)


# ── Health Check ──────────────────────────────────────────────────

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
    logger.info("Registered 48 tools, 7 resources, 3 prompts")

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
