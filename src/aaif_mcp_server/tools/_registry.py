"""Dynamic tool registration registry for AAIF MCP Server.

This module provides auto-registration of all 48 tools (organized by domain)
without the need for manual @mcp.tool() wrappers in server.py.

The register_all_tools(mcp_instance) function:
1. Imports tool functions from each domain module
2. Creates wrapped versions that json.dumps the result
3. Registers them with the MCP instance
4. Returns the count of registered tools

TOOL_CATALOG is organized by domain (12 domains, 48 tools total).
The health_check tool remains special and stays in server.py.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# TOOL CATALOG — 48 tools organized by domain
# ─────────────────────────────────────────────────────────────────────────

def _build_catalog() -> dict[str, list[Callable]]:
    """Build the tool catalog by importing from all domain modules.

    Returns a dict mapping domain name to list of tool functions.
    """
    from .tier_validation import (
        validate_membership_tier,
        check_tier_entitlements,
        detect_tier_anomalies,
    )
    from .compliance import (
        check_sanctions,
        check_tax_exempt_status,
        get_compliance_report,
        flag_compliance_issue,
    )
    from .mailing_list import (
        provision_mailing_lists,
        remove_from_mailing_lists,
        check_mailing_list_membership,
        remediate_mailing_lists,
    )
    from .orchestrator import (
        run_onboarding_checklist,
        get_onboarding_status,
        reconcile_silos,
        run_offboarding_checklist,
        get_silo_health,
    )
    from .contact_roles import (
        list_contacts,
        add_contact,
        update_contact_role,
        remove_contact,
        transfer_voting_rights,
    )
    from .calendar import (
        provision_calendar_invites,
        update_meeting_schedule,
        get_upcoming_meetings,
    )
    from .wg_enrollment import (
        enroll_in_working_group,
        leave_working_group,
        list_available_working_groups,
        get_wg_members,
        check_wg_eligibility,
    )
    from .call_scheduling import (
        schedule_onboarding_call,
        reschedule_onboarding_call,
        get_onboarding_call_status,
    )
    from .elections import (
        create_election,
        validate_candidate_eligibility,
        check_voter_eligibility,
        get_election_status,
        diagnose_ballot_access,
    )
    from .press_release import (
        draft_press_release,
        get_press_release_status,
        list_press_release_templates,
    )
    from .logo_brand import (
        validate_logo,
        get_brand_guidelines,
        request_logo_upload,
    )
    from .renewal_intelligence import (
        get_renewal_status,
        get_engagement_score,
        predict_churn_risk,
        get_renewal_dashboard,
        trigger_renewal_outreach,
    )

    return {
        "Domain 1: Tier Validation": [
            validate_membership_tier,
            check_tier_entitlements,
            detect_tier_anomalies,
        ],
        "Domain 2: Compliance & Sanctions": [
            check_sanctions,
            check_tax_exempt_status,
            get_compliance_report,
            flag_compliance_issue,
        ],
        "Domain 3: Mailing List Provisioning": [
            provision_mailing_lists,
            remove_from_mailing_lists,
            check_mailing_list_membership,
            remediate_mailing_lists,
        ],
        "Domain 4: Orchestrator / Data Silo Bridge": [
            run_onboarding_checklist,
            get_onboarding_status,
            reconcile_silos,
            run_offboarding_checklist,
            get_silo_health,
        ],
        "Domain 5: Contact Role Management": [
            list_contacts,
            add_contact,
            update_contact_role,
            remove_contact,
            transfer_voting_rights,
        ],
        "Domain 6: Meetings & Scheduling": [
            provision_calendar_invites,
            update_meeting_schedule,
            get_upcoming_meetings,
        ],
        "Domain 7: Working Group Enrollment": [
            enroll_in_working_group,
            leave_working_group,
            list_available_working_groups,
            get_wg_members,
            check_wg_eligibility,
        ],
        "Domain 8: Onboarding Call Scheduling": [
            schedule_onboarding_call,
            reschedule_onboarding_call,
            get_onboarding_call_status,
        ],
        "Domain 9: Election & Voting Operations": [
            create_election,
            validate_candidate_eligibility,
            check_voter_eligibility,
            get_election_status,
            diagnose_ballot_access,
        ],
        "Domain 10: Press Release Drafting": [
            draft_press_release,
            get_press_release_status,
            list_press_release_templates,
        ],
        "Domain 11: Logo & Brand Validation": [
            validate_logo,
            get_brand_guidelines,
            request_logo_upload,
        ],
        "Domain 12: Renewal & Engagement Intelligence": [
            get_renewal_status,
            get_engagement_score,
            predict_churn_risk,
            get_renewal_dashboard,
            trigger_renewal_outreach,
        ],
    }


def _make_tool_wrapper(fn: Callable) -> Callable:
    """Create an MCP tool wrapper that calls fn and json.dumps the result.

    This wrapper:
    1. Preserves function metadata using functools.wraps
    2. Overrides __name__ with tool_ prefix
    3. Ensures return annotation is str for MCP schema
    4. Works correctly with FastMCP's inspect.signature() introspection

    Args:
        fn: The original async tool function to wrap

    Returns:
        A wrapped async function suitable for mcp.tool() registration
    """
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        """Wrapper that calls the tool function and returns JSON string."""
        result = await fn(*args, **kwargs)
        return json.dumps(result, indent=2, default=str)

    # Override the function name with tool_ prefix
    wrapper.__name__ = f"tool_{fn.__name__}"
    wrapper.__qualname__ = f"tool_{fn.__name__}"

    # Ensure return type annotation is str for MCP schema generation
    sig = inspect.signature(fn)
    wrapper.__signature__ = sig.replace(return_annotation=str)
    wrapper.__annotations__ = {**fn.__annotations__, 'return': str}

    return wrapper


def register_all_tools(mcp_instance: Any) -> int:
    """Register all 48 tool functions with the MCP instance.

    Dynamically builds wrappers for each tool in TOOL_CATALOG and registers
    them using the mcp_instance.tool() decorator.

    Args:
        mcp_instance: FastMCP instance to register tools with

    Returns:
        The total count of registered tools
    """
    catalog = _build_catalog()

    tool_count = 0
    for domain_name, functions in catalog.items():
        logger.debug(f"Registering {len(functions)} tools in {domain_name}")

        for fn in functions:
            # Create the wrapper
            wrapped = _make_tool_wrapper(fn)

            # Register with MCP
            mcp_instance.tool()(wrapped)

            tool_count += 1
            logger.debug(f"  Registered tool_{fn.__name__}")

    logger.info(f"Successfully registered {tool_count} tools")
    return tool_count
