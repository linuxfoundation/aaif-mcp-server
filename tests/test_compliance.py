"""Tests for Domain 3: Compliance (4 tools).

Tests check_sanctions, check_tax_exempt_status, get_compliance_report, and
flag_compliance_issue.

NOTE: OFAC/sanctions screening is handled by the Descartes integration in
Salesforce at membership intake. The check_sanctions tool retrieves the
screening status from SFDC rather than performing its own screening.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.compliance import (
    check_sanctions,
    check_tax_exempt_status,
    get_compliance_report,
    flag_compliance_issue,
)


@pytest.mark.asyncio
async def test_check_sanctions_known_org(
    org_name_bloomberg: str,
    country_us: str,
    org_bloomberg: str,
):
    """Test sanctions status lookup for known org (Bloomberg, US)."""
    result = await check_sanctions(org_name_bloomberg, country_us, org_bloomberg)

    assert "error" not in result
    assert result["status"] == "clear"
    assert result["requires_human_review"] is False
    assert result["org_name"] == org_name_bloomberg


@pytest.mark.asyncio
async def test_check_sanctions_unknown_org():
    """Test sanctions lookup for unknown org returns unknown + requires review."""
    result = await check_sanctions("Unknown Corp XYZ", "US")

    # No org_id provided, can't look up in SFDC
    assert result["status"] == "unknown"
    assert result["requires_human_review"] is True
    assert "Descartes" in result.get("message", "")


@pytest.mark.asyncio
async def test_check_sanctions_includes_checked_lists(
    org_bloomberg: str,
):
    """Test sanctions result includes list of checked sources."""
    result = await check_sanctions("Bloomberg LP", "US", org_bloomberg)

    assert "checked_lists" in result
    assert len(result["checked_lists"]) > 0
    # Should reference SFDC/Descartes
    assert any("Descartes" in cl or "SFDC" in cl for cl in result["checked_lists"])


@pytest.mark.asyncio
async def test_check_sanctions_with_org_id(
    org_hitachi: str,
):
    """Test sanctions lookup with org_id returns clear for known org."""
    result = await check_sanctions("Hitachi, Ltd.", "JP", org_hitachi)

    assert result["status"] == "clear"
    assert result["org_name"] == "Hitachi, Ltd."


@pytest.mark.asyncio
async def test_check_tax_exempt_status(
    org_hitachi: str,
):
    """Test 501(c)(6) tax-exempt status verification."""
    result = await check_tax_exempt_status(org_hitachi)

    assert "error" not in result
    assert "org_id" in result
    assert "tax_exempt_status" in result
    assert result.get("tax_exempt_status") in ["compliant", "exempt", "verified"]


@pytest.mark.asyncio
async def test_check_tax_exempt_status_not_found():
    """Test tax-exempt check for nonexistent org."""
    result = await check_tax_exempt_status("NONEXISTENT_ORG_999")

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_compliance_report_clean(
    org_bloomberg: str,
):
    """Test compliance report for known organization."""
    result = await get_compliance_report(org_bloomberg)

    assert "error" not in result
    assert result["org_id"] == org_bloomberg
    assert result["org_name"] == "Bloomberg LP"
    assert result["sanctions_status"] == "clear"
    assert "tax_exempt_status" in result
    assert "open_issues" in result


@pytest.mark.asyncio
async def test_get_compliance_report_not_found():
    """Test compliance report for nonexistent org."""
    result = await get_compliance_report("NONEXISTENT_ORG_999")

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"


@pytest.mark.asyncio
async def test_flag_compliance_issue(
    org_bloomberg: str,
):
    """Test creating a compliance issue ticket."""
    result = await flag_compliance_issue(
        org_id=org_bloomberg,
        issue_type="legal_question",
        details="Verify foreign affiliate structure",
    )

    assert "error" not in result
    assert "ticket_id" in result
    assert result.get("org_id") == org_bloomberg
    assert result.get("issue_type") == "legal_question"
    assert result.get("status") == "open"


@pytest.mark.asyncio
async def test_flag_compliance_issue_sanctions_match(
    org_sanctioned: str,
):
    """Test flagging a sanctions match issue."""
    result = await flag_compliance_issue(
        org_id=org_sanctioned,
        issue_type="sanctions_match",
        details="Descartes flagged this entity during intake; requires legal review",
    )

    assert "error" not in result
    assert result.get("issue_type") == "sanctions_match"
    assert "ticket_id" in result


@pytest.mark.asyncio
async def test_compliance_report_includes_timestamp(
    org_hitachi: str,
):
    """Test that compliance reports include screening timestamp."""
    result = await get_compliance_report(org_hitachi)

    assert "last_screened" in result or "checked_at" in result
