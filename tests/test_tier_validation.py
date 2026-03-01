"""Tests for Domain 4: Membership Tier Validation (3 tools).

Tests validate_membership_tier, check_tier_entitlements, and detect_tier_anomalies
against mock data covering Platinum, Gold, and Silver tiers.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.tier_validation import (
    validate_membership_tier,
    check_tier_entitlements,
    detect_tier_anomalies,
)


@pytest.mark.asyncio
async def test_validate_membership_tier_gold(
    org_hitachi: str,
    foundation_id: str,
):
    """Test Gold tier validation — Hitachi should return tier=gold with entitlements."""
    result = await validate_membership_tier(org_hitachi, foundation_id)

    assert "error" not in result
    assert result["org_id"] == org_hitachi
    assert result["tier"] == "gold"
    assert result["org_name"] == "Hitachi, Ltd."
    assert result["status"] == "active"
    assert result["foundation_id"] == foundation_id

    # Gold entitlements should be present
    entitlements = result.get("entitlements", {})
    assert entitlements.get("gb_seats") == 1
    assert entitlements.get("voting_rights") is True
    assert entitlements.get("wg_chair_eligible") is True
    assert entitlements.get("tc_eligible") is True


@pytest.mark.asyncio
async def test_validate_membership_tier_platinum(
    org_openai: str,
    foundation_id: str,
):
    """Test Platinum tier validation — OpenAI should have top entitlements."""
    result = await validate_membership_tier(org_openai, foundation_id)

    assert "error" not in result
    assert result["org_id"] == org_openai
    assert result["tier"] == "platinum"
    assert result["org_name"] == "OpenAI"

    # Platinum should have highest entitlements
    entitlements = result.get("entitlements", {})
    assert entitlements.get("gb_seats") == 2
    assert entitlements.get("voting_rights") is True
    assert entitlements.get("tc_eligible") is True
    assert entitlements.get("wg_chair_eligible") is True


@pytest.mark.asyncio
async def test_validate_membership_tier_not_found(
    org_invalid: str,
    foundation_id: str,
):
    """Test error handling for invalid org_id."""
    result = await validate_membership_tier(org_invalid, foundation_id)

    assert "error" in result
    assert result["error"] == "ORG_NOT_FOUND"
    assert org_invalid in result.get("message", "")


@pytest.mark.asyncio
async def test_check_tier_entitlements_gold(
    tier_gold: str,
    foundation_id: str,
):
    """Test Gold tier entitlements matrix."""
    result = await check_tier_entitlements(tier_gold, foundation_id)

    assert "error" not in result
    assert result["tier"] == "gold"
    assert result["gb_seats"] == 1
    assert result["voting_rights"] is True
    assert result["wg_chair_eligible"] is True
    assert result["tc_eligible"] is True

    # Verify mailing lists
    mailing_lists = result.get("mailing_lists", [])
    assert "governing-board@lists.aaif.io" in mailing_lists
    assert "members-all@lists.aaif.io" in mailing_lists


@pytest.mark.asyncio
async def test_check_tier_entitlements_silver(
    tier_silver: str,
    foundation_id: str,
):
    """Test Silver tier entitlements — limited access."""
    result = await check_tier_entitlements(tier_silver, foundation_id)

    assert "error" not in result
    assert result["tier"] == "silver"
    assert result["gb_seats"] == 0
    assert result["voting_rights"] is False
    assert result["wg_chair_eligible"] is False
    assert result["tc_eligible"] is False

    # Silver only gets members-all list
    mailing_lists = result.get("mailing_lists", [])
    assert "members-all@lists.aaif.io" in mailing_lists
    assert "governing-board@lists.aaif.io" not in mailing_lists


@pytest.mark.asyncio
async def test_check_tier_entitlements_platinum(
    tier_platinum: str,
    foundation_id: str,
):
    """Test Platinum tier entitlements — full access."""
    result = await check_tier_entitlements(tier_platinum, foundation_id)

    assert "error" not in result
    assert result["tier"] == "platinum"
    assert result["gb_seats"] == 2
    assert result["voting_rights"] is True
    assert result["tc_eligible"] is True

    # Platinum gets all mailing lists
    mailing_lists = result.get("mailing_lists", [])
    assert "governing-board@lists.aaif.io" in mailing_lists
    assert "technical-committee@lists.aaif.io" in mailing_lists
    assert "members-all@lists.aaif.io" in mailing_lists


@pytest.mark.asyncio
async def test_check_tier_entitlements_invalid_tier():
    """Test error handling for invalid tier name."""
    result = await check_tier_entitlements("invalid_tier", "aaif")

    assert "error" in result
    assert result["error"] == "TIER_NOT_FOUND"


@pytest.mark.asyncio
async def test_check_tier_entitlements_deprecated_tier():
    """Test deprecated tier names are flagged."""
    result = await check_tier_entitlements("associate", "aaif")

    assert "error" in result
    assert result["error"] == "DEPRECATED_TIER"


@pytest.mark.asyncio
async def test_detect_tier_anomalies(
    foundation_id: str,
):
    """Test tier anomaly detection — should find Natoma's paresh not provisioned."""
    result = await detect_tier_anomalies(foundation_id)

    assert "error" not in result
    assert result["foundation_id"] == foundation_id
    assert "anomalies_found" in result
    assert "anomalies" in result

    # Should detect Natoma's paresh missing members-all list
    anomalies = result.get("anomalies", [])
    found_natoma_gap = False
    for anomaly in anomalies:
        if (anomaly.get("org_id") == "0017V00001NATOMA" and
                anomaly.get("anomaly_type") == "MISSING_ACCESS"):
            found_natoma_gap = True
            assert "members-all" in anomaly.get("description", "")
            assert anomaly.get("severity") == "medium"

    assert found_natoma_gap, "Should detect Natoma paresh missing access"


@pytest.mark.asyncio
async def test_detect_tier_anomalies_returns_statistics(
    foundation_id: str,
):
    """Test anomaly detection includes statistics."""
    result = await detect_tier_anomalies(foundation_id)

    assert result["total_members_scanned"] > 0
    assert result["anomalies_found"] >= 0
    assert isinstance(result["anomalies"], list)
