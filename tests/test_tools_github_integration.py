"""Tests for MCP tool-level PIS GitHub integration.

Verifies that wg_enrollment.py, orchestrator.py correctly route to
PISGitHubConnector for repo discovery/verification when PIS is configured,
and fall back gracefully when not.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aaif_mcp_server.config import WorkingGroup, WgAccessPolicy


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def mock_sfdc():
    """Mock SFDC connector returning a Gold org with one contact."""
    connector = AsyncMock()

    contact = MagicMock()
    contact.contact_id = "C001"
    contact.name = "Kenji Tanaka"
    contact.email = "kenji@hitachi.test"
    contact.role = MagicMock()
    contact.role.value = "voting_contact"
    contact.discord_handle = "kenji#1234"
    contact.github_username = "kenji-tanaka"

    org = MagicMock()
    org.org_id = "ORG001"
    org.org_name = "Hitachi"
    org.tier = MagicMock()
    org.tier.value = "gold"
    org.status = "active"
    org.contacts = [contact]

    connector.get_org.return_value = org
    connector.list_orgs.return_value = [org]
    return connector


@pytest.fixture
def mock_wgs():
    """Mock working groups config with one WG."""
    return {"aaif": [WorkingGroup(
        wg_id="wg-agentic-commerce",
        name="Agentic Commerce",
        slug="agentic-commerce",
        meeting_schedule="Wed 10am PT",
        mailing_list="wg-agentic-commerce@lists.aaif.io",
        discord_channel="#wg-agentic-commerce",
        github_repo="aaif/wg-agentic-commerce",
        access_policy=WgAccessPolicy.any_member,
    )]}


@pytest.fixture
def mock_pis_github():
    """Mock PISGitHubConnector for tool-level tests."""
    connector = AsyncMock()

    # list_orgs returns github orgs tracked by PIS
    connector.list_orgs.return_value = [
        {"organization": "aaif", "repos_count": 3},
    ]

    # list_repos returns repos in an org
    connector.list_repos.return_value = [
        {"name": "wg-agentic-commerce", "dco_enabled": True, "archived": False},
        {"name": "wg-foundation-models", "dco_enabled": True, "archived": False},
    ]

    # get_repo returns details for a specific repo
    connector.get_repo.return_value = {
        "name": "wg-agentic-commerce",
        "dco_enabled": True,
        "archived": False,
        "has_issues": True,
    }

    return connector


@pytest.fixture
def mock_github():
    """Mock direct GitHub connector for collaborator operations."""
    connector = AsyncMock()
    connector.add_collaborator.return_value = {"status": "added"}
    connector.remove_collaborator.return_value = {"status": "removed"}
    return connector


@pytest.fixture
def mock_groupsio():
    connector = AsyncMock()
    connector.add_member.return_value = {"status": "added"}
    connector.remove_member.return_value = {"status": "removed"}
    connector.get_lists.return_value = ["general@lists.aaif.io"]
    connector.is_member.return_value = True
    return connector


@pytest.fixture
def mock_discord():
    connector = AsyncMock()
    connector.add_role.return_value = {"status": "added"}
    connector.remove_role.return_value = {"status": "removed"}
    return connector


# ── Tests: WG enrollment with PIS GitHub ─────────────────────────

@pytest.mark.asyncio
async def test_wg_enroll_with_pis_github_verifies_repo(mock_sfdc, mock_pis_github, mock_github, mock_groupsio, mock_discord, mock_wgs):
    """When PIS GitHub is configured, enrollment verifies repo exists in PIS."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_discord", return_value=mock_discord), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_github", return_value=mock_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=mock_pis_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {}):
        from aaif_mcp_server.tools.wg_enrollment import enroll_in_working_group
        result = await enroll_in_working_group("C001", "wg-agentic-commerce", dry_run=False)

    assert result["github_source"] == "pis_github_v2"
    assert result["pis_repo_verified"] is True
    # Should have called PIS to verify repo
    mock_pis_github.get_repo.assert_called_once_with("aaif", "wg-agentic-commerce")
    # Should have called direct GitHub to add collaborator
    mock_github.add_collaborator.assert_called_once_with("kenji-tanaka", "aaif/wg-agentic-commerce")
    # GitHub result should include PIS metadata
    assert result["enrollment_results"]["github"]["pis_repo_verified"] is True
    assert result["enrollment_results"]["github"]["dco_enabled"] is True


@pytest.mark.asyncio
async def test_wg_enroll_dry_run_with_pis_github(mock_sfdc, mock_pis_github, mock_wgs):
    """Dry run enrollment shows PIS-enriched GitHub info."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=mock_pis_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs):
        from aaif_mcp_server.tools.wg_enrollment import enroll_in_working_group
        result = await enroll_in_working_group("C001", "wg-agentic-commerce", dry_run=True)

    assert result["github_source"] == "pis_github_v2"
    assert result["pis_repo_verified"] is True
    assert "PIS-verified" in result["enrollment_actions"]["github"]
    assert "DCO=enabled" in result["enrollment_actions"]["github"]


@pytest.mark.asyncio
async def test_wg_enroll_without_pis_github(mock_sfdc, mock_github, mock_groupsio, mock_discord, mock_wgs):
    """Without PIS GitHub, enrollment falls back to mock source."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_discord", return_value=mock_discord), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_github", return_value=mock_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {}):
        from aaif_mcp_server.tools.wg_enrollment import enroll_in_working_group
        result = await enroll_in_working_group("C001", "wg-agentic-commerce", dry_run=False)

    assert result["github_source"] == "mock_github"
    assert result["pis_repo_verified"] is False
    # Should NOT have called PIS
    mock_github.add_collaborator.assert_called_once()


@pytest.mark.asyncio
async def test_wg_enroll_dry_run_without_pis_github(mock_sfdc, mock_wgs):
    """Dry run without PIS GitHub shows mock source in actions."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs):
        from aaif_mcp_server.tools.wg_enrollment import enroll_in_working_group
        result = await enroll_in_working_group("C001", "wg-agentic-commerce", dry_run=True)

    assert result["github_source"] == "mock_github"
    assert result["pis_repo_verified"] is False
    # Should NOT mention PIS-verified
    assert "PIS-verified" not in result["enrollment_actions"]["github"]


# ── Tests: WG leave with PIS GitHub ──────────────────────────────

@pytest.mark.asyncio
async def test_wg_leave_with_pis_github_source(mock_sfdc, mock_github, mock_groupsio, mock_discord, mock_wgs):
    """WG leave tracks PIS GitHub source when configured."""
    mock_pis_gh = AsyncMock()

    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_discord", return_value=mock_discord), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_github", return_value=mock_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=mock_pis_gh), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.wg_enrollment import leave_working_group
        result = await leave_working_group("C001", "wg-agentic-commerce", dry_run=False)

    assert result["github_source"] == "pis_github_v2"
    assert result["dry_run"] is False
    mock_github.remove_collaborator.assert_called_once_with("kenji-tanaka", "aaif/wg-agentic-commerce")


@pytest.mark.asyncio
async def test_wg_leave_dry_run_with_pis_github(mock_sfdc, mock_wgs):
    """Dry run leave shows PIS GitHub source."""
    mock_pis_gh = AsyncMock()

    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=mock_pis_gh), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.wg_enrollment import leave_working_group
        result = await leave_working_group("C001", "wg-agentic-commerce", dry_run=True)

    assert result["github_source"] == "pis_github_v2"
    assert "PIS-tracked" in result["unenrollment_actions"]["github"]


@pytest.mark.asyncio
async def test_wg_leave_without_pis_github(mock_sfdc, mock_github, mock_groupsio, mock_discord, mock_wgs):
    """WG leave without PIS GitHub falls back to mock."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_discord", return_value=mock_discord), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_github", return_value=mock_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.wg_enrollment import leave_working_group
        result = await leave_working_group("C001", "wg-agentic-commerce", dry_run=False)

    assert result["github_source"] == "mock_github"


# ── Tests: get_wg_members with PIS GitHub ────────────────────────

@pytest.mark.asyncio
async def test_wg_members_enriched_with_pis_github(mock_sfdc, mock_pis_github, mock_wgs):
    """get_wg_members returns PIS GitHub repo metadata when configured."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=mock_pis_github), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.wg_enrollment import get_wg_members
        result = await get_wg_members("wg-agentic-commerce")

    assert "github_repo" in result
    assert result["github_repo"]["source"] == "pis_github_v2"
    assert result["github_repo"]["dco_enabled"] is True
    assert result["github_repo"]["archived"] is False
    mock_pis_github.get_repo.assert_called_once_with("aaif", "wg-agentic-commerce")


@pytest.mark.asyncio
async def test_wg_members_without_pis_github(mock_sfdc, mock_wgs):
    """get_wg_members omits github_repo when PIS not configured."""
    with patch("aaif_mcp_server.tools.wg_enrollment.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.wg_enrollment.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.wg_enrollment.WORKING_GROUPS", mock_wgs), \
         patch("aaif_mcp_server.tools.wg_enrollment.MOCK_WG_ENROLLMENTS", {"C001": ["wg-agentic-commerce"]}):
        from aaif_mcp_server.tools.wg_enrollment import get_wg_members
        result = await get_wg_members("wg-agentic-commerce")

    assert "github_repo" not in result
    assert result["total_members"] == 1


# ── Tests: offboarding with PIS GitHub ───────────────────────────

@pytest.mark.asyncio
async def test_offboarding_pis_github_discovers_repos(mock_sfdc, mock_pis_github, mock_github, mock_groupsio):
    """Offboarding discovers repos via PIS GitHub and removes collaborator from each."""
    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=mock_pis_github), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=False)

    github_actions = [a for a in result["actions"] if a["step"] == "remove_github_collaborator"]
    # PIS returns 2 repos, so 2 collaborator removals
    assert len(github_actions) == 2
    assert all(a["source"] == "pis_github_v2" for a in github_actions)
    assert all(a["status"] == "completed" for a in github_actions)
    assert mock_github.remove_collaborator.call_count == 2
    # Verify PIS was used for discovery
    mock_pis_github.list_orgs.assert_called_once()
    mock_pis_github.list_repos.assert_called_once_with("aaif")


@pytest.mark.asyncio
async def test_offboarding_pis_github_dry_run(mock_sfdc, mock_pis_github, mock_github, mock_groupsio):
    """Offboarding dry run with PIS GitHub shows planned repo removals."""
    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=mock_pis_github), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=True)

    github_actions = [a for a in result["actions"] if a["step"] == "remove_github_collaborator"]
    assert len(github_actions) == 2
    assert all(a["status"] == "dry_run" for a in github_actions)
    # Should NOT have called remove_collaborator
    mock_github.remove_collaborator.assert_not_called()


@pytest.mark.asyncio
async def test_offboarding_without_pis_github_flags_manual(mock_sfdc, mock_github, mock_groupsio):
    """Without PIS GitHub, offboarding flags GitHub removal as manual."""
    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=True)

    github_manual = [a for a in result["actions"] if a["step"] == "remove_github_access"]
    assert len(github_manual) == 1
    assert github_manual[0]["status"] == "manual_required"
    # Should NOT have called any GitHub operations
    mock_github.remove_collaborator.assert_not_called()


@pytest.mark.asyncio
async def test_offboarding_pis_github_no_username(mock_sfdc, mock_pis_github, mock_github, mock_groupsio):
    """With PIS GitHub but no GitHub username, flags manual removal."""
    # Override contact to have no GitHub username
    mock_sfdc.get_org.return_value.contacts[0].github_username = None

    with patch("aaif_mcp_server.tools.orchestrator.get_sfdc", return_value=mock_sfdc), \
         patch("aaif_mcp_server.tools.orchestrator.get_groupsio", return_value=mock_groupsio), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_meeting", return_value=None), \
         patch("aaif_mcp_server.tools.orchestrator.get_pis_github", return_value=mock_pis_github), \
         patch("aaif_mcp_server.tools.orchestrator.get_github", return_value=mock_github):
        from aaif_mcp_server.tools.orchestrator import run_offboarding_checklist
        result = await run_offboarding_checklist("ORG001", "kenji@hitachi.test", dry_run=False)

    github_manual = [a for a in result["actions"] if a["step"] == "remove_github_access"]
    assert len(github_manual) == 1
    assert github_manual[0]["status"] == "manual_required"
    assert "No GitHub username" in github_manual[0]["note"]
    mock_github.remove_collaborator.assert_not_called()
