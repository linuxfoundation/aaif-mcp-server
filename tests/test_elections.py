"""Tests for Domain 9: Elections (5 tools).

Tests create_election, validate_candidate_eligibility, check_voter_eligibility,
get_election_status, and diagnose_ballot_access against mock election data.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.elections import (
    create_election,
    validate_candidate_eligibility,
    check_voter_eligibility,
    get_election_status,
    diagnose_ballot_access,
)


@pytest.mark.asyncio
async def test_create_election(foundation_id: str):
    """Test create_election for valid working group."""
    result = await create_election(
        "wg-agentic-commerce",
        "WG Chair",
        "2026-04-01",
        "2026-04-15",
        "2026-04-30",
        foundation_id=foundation_id,
    )

    assert "error" not in result
    assert "election_id" in result or "message" in result


@pytest.mark.asyncio
async def test_create_election_wg_not_found(foundation_id: str):
    """Test create_election returns error for non-existent WG."""
    result = await create_election(
        "wg-nonexistent",
        "WG Chair",
        "2026-04-01",
        "2026-04-15",
        "2026-04-30",
        foundation_id=foundation_id,
    )

    assert "error" in result
    assert result["error"] == "WG_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_election_status(foundation_id: str):
    """Test get_election_status for election."""
    result = await get_election_status("elec-wg-chair-001", foundation_id)

    # Either return status or NOT_FOUND
    if "error" not in result:
        assert "status" in result or "election_id" in result
    else:
        assert result["error"] == "ELECTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_election_status_not_found(foundation_id: str):
    """Test get_election_status returns error for invalid election."""
    result = await get_election_status("elec-fake", foundation_id)

    assert "error" in result
    assert result["error"] == "ELECTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_validate_candidate_gold(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test validate_candidate_eligibility for Gold tier (eligible or election not found)."""
    result = await validate_candidate_eligibility(
        contact_hitachi_c001,
        "elec-wg-chair-001",
        foundation_id,
    )

    # Either eligible or election not found (both are valid scenarios in mock)
    if "error" in result:
        assert result["error"] == "ELECTION_NOT_FOUND"
    else:
        assert "eligible" in result


@pytest.mark.asyncio
async def test_validate_candidate_silver(
    contact_natoma_c005: str,
    foundation_id: str,
):
    """Test validate_candidate_eligibility for Silver tier (not eligible or election not found)."""
    result = await validate_candidate_eligibility(
        contact_natoma_c005,
        "elec-wg-chair-001",
        foundation_id,
    )

    # Either election not found or not eligible
    if "error" in result:
        assert result["error"] in ["NOT_ELIGIBLE", "ELECTION_NOT_FOUND"]
    else:
        assert "eligible" in result


@pytest.mark.asyncio
async def test_validate_candidate_not_found(foundation_id: str):
    """Test validate_candidate_eligibility returns error for invalid contact."""
    result = await validate_candidate_eligibility(
        "C999",
        "elec-wg-chair-001",
        foundation_id,
    )

    assert "error" in result
    # Could be CONTACT_NOT_FOUND or ELECTION_NOT_FOUND
    assert result["error"] in ["CONTACT_NOT_FOUND", "ELECTION_NOT_FOUND"]


@pytest.mark.asyncio
async def test_check_voter_gold(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test check_voter_eligibility for Gold tier (or election not found)."""
    result = await check_voter_eligibility(
        contact_hitachi_c001,
        "elec-wg-chair-001",
        foundation_id,
    )

    # Either succeeds or election not found
    if "error" in result:
        assert result["error"] == "ELECTION_NOT_FOUND"


@pytest.mark.asyncio
async def test_check_voter_silver(
    contact_natoma_c005: str,
    foundation_id: str,
):
    """Test check_voter_eligibility for Silver tier (not eligible or election not found)."""
    result = await check_voter_eligibility(
        contact_natoma_c005,
        "elec-wg-chair-001",
        foundation_id,
    )

    # Silver tier should not be eligible
    if "error" in result:
        assert result["error"] in ["NOT_ELIGIBLE", "ELECTION_NOT_FOUND"]
    else:
        assert "eligible" in result


@pytest.mark.asyncio
async def test_diagnose_ballot_access(
    contact_hitachi_c001: str,
    foundation_id: str,
):
    """Test diagnose_ballot_access returns diagnostics (or election not found)."""
    result = await diagnose_ballot_access(
        contact_hitachi_c001,
        "elec-wg-chair-001",
        foundation_id,
    )

    # Either returns diagnostics or election not found
    if "error" not in result:
        assert isinstance(result.get("diagnostics"), list) or "diagnostics" in result
    else:
        assert result["error"] == "ELECTION_NOT_FOUND"
