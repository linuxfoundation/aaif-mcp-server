"""Pytest configuration and shared fixtures for AAIF MCP Server tests.

Provides:
- Async test support via pytest-asyncio
- Connector registry initialization (auto-used)
- Tool function imports and exposure
- Mock org_id and contact fixtures
- Foundation ID defaults
"""

from __future__ import annotations

import pytest
import pytest_asyncio

# Import all tool functions for use in tests
from aaif_mcp_server.tools.tier_validation import (
    validate_membership_tier,
    check_tier_entitlements,
    detect_tier_anomalies,
)
from aaif_mcp_server.tools.compliance import (
    check_sanctions,
    check_tax_exempt_status,
    get_compliance_report,
    flag_compliance_issue,
)
from aaif_mcp_server.tools.mailing_list import (
    provision_mailing_lists,
    remove_from_mailing_lists,
    check_mailing_list_membership,
    remediate_mailing_lists,
)
from aaif_mcp_server.tools.orchestrator import (
    run_onboarding_checklist,
    get_onboarding_status,
    reconcile_silos,
    run_offboarding_checklist,
    get_silo_health,
)
from aaif_mcp_server.resources.rules import (
    get_provisioning_rules,
    get_tier_entitlements,
    get_working_groups,
)
from aaif_mcp_server.resources.member import (
    get_member_profile,
    list_members,
)
from aaif_mcp_server.tools.contact_roles import (
    list_contacts,
    add_contact,
    update_contact_role,
    remove_contact,
    transfer_voting_rights,
)
from aaif_mcp_server.tools.calendar import (
    provision_calendar_invites,
    update_meeting_schedule,
    get_upcoming_meetings,
)
from aaif_mcp_server.tools.wg_enrollment import (
    enroll_in_working_group,
    leave_working_group,
    list_available_working_groups,
    get_wg_members,
    check_wg_eligibility,
)
from aaif_mcp_server.tools.call_scheduling import (
    schedule_onboarding_call,
    reschedule_onboarding_call,
    get_onboarding_call_status,
)
from aaif_mcp_server.tools.elections import (
    create_election,
    validate_candidate_eligibility,
    check_voter_eligibility,
    get_election_status,
    diagnose_ballot_access,
)
from aaif_mcp_server.tools.press_release import (
    draft_press_release,
    get_press_release_status,
    list_press_release_templates,
)
from aaif_mcp_server.tools.logo_brand import (
    validate_logo,
    get_brand_guidelines,
    request_logo_upload,
)
from aaif_mcp_server.tools.renewal_intelligence import (
    get_renewal_status,
    get_engagement_score,
    predict_churn_risk,
    get_renewal_dashboard,
    trigger_renewal_outreach,
)

# Expose tool functions for pytest
__all__ = [
    "validate_membership_tier",
    "check_tier_entitlements",
    "detect_tier_anomalies",
    "check_sanctions",
    "check_tax_exempt_status",
    "get_compliance_report",
    "flag_compliance_issue",
    "provision_mailing_lists",
    "remove_from_mailing_lists",
    "check_mailing_list_membership",
    "remediate_mailing_lists",
    "run_onboarding_checklist",
    "get_onboarding_status",
    "reconcile_silos",
    "run_offboarding_checklist",
    "get_silo_health",
    "get_provisioning_rules",
    "get_tier_entitlements",
    "get_working_groups",
    "get_member_profile",
    "list_members",
    "list_contacts",
    "add_contact",
    "update_contact_role",
    "remove_contact",
    "transfer_voting_rights",
    "provision_calendar_invites",
    "update_meeting_schedule",
    "get_upcoming_meetings",
    "enroll_in_working_group",
    "leave_working_group",
    "list_available_working_groups",
    "get_wg_members",
    "check_wg_eligibility",
    "schedule_onboarding_call",
    "reschedule_onboarding_call",
    "get_onboarding_call_status",
    "create_election",
    "validate_candidate_eligibility",
    "check_voter_eligibility",
    "get_election_status",
    "diagnose_ballot_access",
    "draft_press_release",
    "get_press_release_status",
    "list_press_release_templates",
    "validate_logo",
    "get_brand_guidelines",
    "request_logo_upload",
    "get_renewal_status",
    "get_engagement_score",
    "predict_churn_risk",
    "get_renewal_dashboard",
    "trigger_renewal_outreach",
]


# ── Pytest Configuration ────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async (pytest-asyncio)"
    )


# ── Connector Registry Initialization ─────────────────────────────

@pytest_asyncio.fixture(autouse=True, scope="session")
async def _init_connectors():
    """Initialize the connector registry once for the entire test session.

    This fixture is auto-used (applies to every test) and session-scoped
    (runs once). It ensures all 7 connectors are created and initialized
    (in mock mode) before any tool function is called.
    """
    from aaif_mcp_server.connectors.registry import initialize_connectors, shutdown_connectors
    await initialize_connectors()
    yield
    await shutdown_connectors()


# ── Fixtures: Foundation and Org IDs ────────────────────────────────

@pytest.fixture
def foundation_id() -> str:
    """Default foundation ID for AAIF tests."""
    return "aaif"


@pytest.fixture
def org_hitachi() -> str:
    """Hitachi Gold tier org ID."""
    return "0017V00001HITACHI"


@pytest.fixture
def org_bloomberg() -> str:
    """Bloomberg Gold tier org ID."""
    return "0017V00001BLOOMBERG"


@pytest.fixture
def org_natoma() -> str:
    """Natoma Silver tier org ID."""
    return "0017V00001NATOMA"


@pytest.fixture
def org_iproov() -> str:
    """iProov Silver tier org ID."""
    return "0017V00001IPROOV"


@pytest.fixture
def org_openai() -> str:
    """OpenAI Platinum tier org ID."""
    return "0017V00001OPENAI"


@pytest.fixture
def org_sanctioned() -> str:
    """TestCorp Sanctioned LLC (test entity for sanctions screening)."""
    return "0017V00001SANCTIONED"


@pytest.fixture
def org_invalid() -> str:
    """Invalid org ID for error testing."""
    return "0017V00001INVALID"


# ── Fixtures: Contact Data ──────────────────────────────────────────

@pytest.fixture
def contact_hitachi_c001() -> str:
    """Hitachi voting contact (Takeshi Yamada)."""
    return "C001"


@pytest.fixture
def contact_hitachi_c002() -> str:
    """Hitachi technical contact (Yuki Tanaka)."""
    return "C002"


@pytest.fixture
def contact_bloomberg_c003() -> str:
    """Bloomberg voting contact (Sambhav Kothari)."""
    return "C003"


@pytest.fixture
def contact_bloomberg_c004() -> str:
    """Bloomberg alternate contact (Ania Musial)."""
    return "C004"


@pytest.fixture
def contact_natoma_c005() -> str:
    """Natoma primary contact (Paresh Bhaya)."""
    return "C005"


@pytest.fixture
def contact_iproov_c006() -> str:
    """iProov primary contact (Andrew Bud)."""
    return "C006"


@pytest.fixture
def contact_openai_c007() -> str:
    """OpenAI voting contact (Sam Altman)."""
    return "C007"


@pytest.fixture
def contact_sanctioned_c099() -> str:
    """Sanctioned org test contact."""
    return "C099"


# ── Fixtures: Email Addresses ───────────────────────────────────────

@pytest.fixture
def email_hitachi_yamada() -> str:
    """Hitachi voting contact email."""
    return "t.yamada@hitachi.com"


@pytest.fixture
def email_hitachi_tanaka() -> str:
    """Hitachi technical contact email."""
    return "y.tanaka@hitachi.com"


@pytest.fixture
def email_bloomberg_kothari() -> str:
    """Bloomberg voting contact email."""
    return "skothari@bloomberg.net"


@pytest.fixture
def email_bloomberg_musial() -> str:
    """Bloomberg alternate contact email."""
    return "amusial@bloomberg.net"


@pytest.fixture
def email_natoma_paresh() -> str:
    """Natoma primary contact email (not yet provisioned)."""
    return "paresh@natoma.com"


@pytest.fixture
def email_iproov_bud() -> str:
    """iProov primary contact email."""
    return "abud@iproov.com"


@pytest.fixture
def email_openai_altman() -> str:
    """OpenAI voting contact email."""
    return "sam@openai.com"


# ── Fixtures: Tier Names ────────────────────────────────────────────

@pytest.fixture
def tier_platinum() -> str:
    """Platinum tier name."""
    return "platinum"


@pytest.fixture
def tier_gold() -> str:
    """Gold tier name."""
    return "gold"


@pytest.fixture
def tier_silver() -> str:
    """Silver tier name."""
    return "silver"


# ── Fixtures: Country Codes ────────────────────────────────────────

@pytest.fixture
def country_us() -> str:
    """United States country code."""
    return "US"


@pytest.fixture
def country_jp() -> str:
    """Japan country code."""
    return "JP"


@pytest.fixture
def country_gb() -> str:
    """United Kingdom country code."""
    return "GB"


@pytest.fixture
def country_ru() -> str:
    """Russia country code (high-risk sanctions country)."""
    return "RU"


# ── Fixtures: Org Names ─────────────────────────────────────────────

@pytest.fixture
def org_name_hitachi() -> str:
    """Hitachi legal name."""
    return "Hitachi, Ltd."


@pytest.fixture
def org_name_bloomberg() -> str:
    """Bloomberg legal name."""
    return "Bloomberg LP"


@pytest.fixture
def org_name_natoma() -> str:
    """Natoma legal name."""
    return "Natoma"


@pytest.fixture
def org_name_iproov() -> str:
    """iProov legal name."""
    return "iProov"


@pytest.fixture
def org_name_openai() -> str:
    """OpenAI legal name."""
    return "OpenAI"


@pytest.fixture
def org_name_sanctioned() -> str:
    """Sanctioned entity legal name."""
    return "TestCorp Sanctioned LLC"


# ── Pytest Asyncio Marker Configuration ────────────────────────────

pytest_plugins = ("pytest_asyncio",)
