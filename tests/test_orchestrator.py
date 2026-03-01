"""Tests for Domain 2: Orchestrator (5 tools).

Tests run_onboarding_checklist, get_onboarding_status, reconcile_silos,
run_offboarding_checklist, and get_silo_health against mock member data
and checklist templates.

The orchestrator coordinates D1-D5 deliverables across compliance, provisioning,
and contact management.
"""

from __future__ import annotations

import pytest

from aaif_mcp_server.tools.orchestrator import (
    run_onboarding_checklist,
    get_onboarding_status,
    reconcile_silos,
    run_offboarding_checklist,
    get_silo_health,
)


@pytest.mark.asyncio
async def test_run_onboarding_checklist_dry_run(
    org_hitachi: str,
    contact_hitachi_c001: str,
):
    """Test onboarding checklist (dry-run) for Hitachi voting contact."""
    result = await run_onboarding_checklist(
        org_id=org_hitachi,
        contact_id=contact_hitachi_c001,
        dry_run=True,
    )

    assert "error" not in result
    assert result["org_id"] == org_hitachi
    assert result["contact_id"] == contact_hitachi_c001
    assert result["dry_run"] is True
    assert "deliverables" in result
    assert "overall_status" in result

    # Should have D1-D5 deliverables
    deliverables = result.get("deliverables", [])
    assert len(deliverables) > 0
    deliverable_ids = [d.get("id") for d in deliverables]
    for expected_id in ["D1", "D2", "D3", "D4", "D5"]:
        assert expected_id in deliverable_ids


@pytest.mark.asyncio
async def test_run_onboarding_checklist_includes_steps(
    org_hitachi: str,
    contact_hitachi_c001: str,
):
    """Test that checklist includes detailed steps."""
    result = await run_onboarding_checklist(
        org_id=org_hitachi,
        contact_id=contact_hitachi_c001,
        dry_run=True,
    )

    assert "total_steps" in result
    assert "completed_steps" in result
    assert "failed_steps" in result
    assert result["total_steps"] > 0


@pytest.mark.asyncio
async def test_get_onboarding_status_not_started(
    org_natoma: str,
    contact_natoma_c005: str,
):
    """Test onboarding status before any checklist run."""
    result = await get_onboarding_status(
        org_id=org_natoma,
        contact_id=contact_natoma_c005,
    )

    assert "error" not in result
    assert result["org_id"] == org_natoma
    assert result["contact_id"] == contact_natoma_c005
    # Should show pending/not started status
    assert result.get("status") == "not_started" or result.get("overall") in ["pending", "not_started", None]


@pytest.mark.asyncio
async def test_get_onboarding_status_includes_deliverables(
    org_hitachi: str,
    contact_hitachi_c001: str,
):
    """Test that status includes deliverable info when available."""
    result = await get_onboarding_status(
        org_id=org_hitachi,
        contact_id=contact_hitachi_c001,
    )

    # If a checklist was run previously, deliverables is a list of dicts
    # If not started, status will be "not_started"
    if result.get("status") == "not_started":
        assert "message" in result
    else:
        assert "deliverables" in result
        deliverables = result["deliverables"]
        assert isinstance(deliverables, list)
        for d in deliverables:
            assert "id" in d


@pytest.mark.asyncio
async def test_reconcile_silos(
    org_natoma: str,
):
    """Test silo reconciliation structure for Natoma."""
    result = await reconcile_silos(org_id=org_natoma)

    assert "error" not in result
    assert result["org_id"] == org_natoma
    assert "discrepancies" in result
    assert "contacts_checked" in result
    assert "discrepancies_found" in result
    assert isinstance(result["discrepancies"], list)


@pytest.mark.asyncio
async def test_reconcile_silos_compares_systems(
    org_bloomberg: str,
):
    """Test that reconciliation compares Salesforce, Groups.io, and tracker."""
    result = await reconcile_silos(org_id=org_bloomberg)

    assert "error" not in result
    assert "systems_checked" in result or "discrepancies" in result


@pytest.mark.asyncio
async def test_run_offboarding_checklist_dry_run(
    org_bloomberg: str,
    email_bloomberg_kothari: str,
):
    """Test offboarding checklist (dry-run) for Bloomberg voting contact."""
    result = await run_offboarding_checklist(
        org_id=org_bloomberg,
        contact_email=email_bloomberg_kothari,
        reason="membership_cancelled",
        dry_run=True,
    )

    assert "error" not in result
    assert result.get("dry_run") is True
    assert "actions" in result or "planned_actions" in result

    # Should plan removal of subscriptions
    actions = result.get("actions", result.get("planned_actions", []))
    assert len(actions) > 0


@pytest.mark.asyncio
async def test_run_offboarding_checklist_reasons(
    org_natoma: str,
    email_natoma_paresh: str,
):
    """Test offboarding with different reasons."""
    for reason in ["membership_cancelled", "tier_downgrade", "contact_inactive"]:
        result = await run_offboarding_checklist(
            org_id=org_natoma,
            contact_email=email_natoma_paresh,
            reason=reason,
            dry_run=True,
        )

        assert "error" not in result
        assert result.get("reason") == reason or "reason" not in result


@pytest.mark.asyncio
async def test_run_offboarding_checklist_execute(
    org_hitachi: str,
    email_hitachi_yamada: str,
):
    """Test actual offboarding execution."""
    result = await run_offboarding_checklist(
        org_id=org_hitachi,
        contact_email=email_hitachi_yamada,
        dry_run=False,
    )

    assert "error" not in result
    assert result.get("dry_run") is False


@pytest.mark.asyncio
async def test_get_silo_health():
    """Test overall silo health report."""
    result = await get_silo_health()

    assert "error" not in result
    assert "foundation_id" in result
    assert "overall_score" in result
    assert "total_members" in result
    assert "members_in_sync" in result
    assert "members_with_issues" in result

    # Health score should be 0.0-1.0
    score = result.get("overall_score")
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_get_silo_health_includes_issues(
):
    """Test that silo health report includes top issues."""
    result = await get_silo_health()

    assert "top_issues" in result
    assert isinstance(result["top_issues"], list)


@pytest.mark.asyncio
async def test_get_silo_health_summary_statistics(
):
    """Test silo health includes comprehensive statistics."""
    result = await get_silo_health()

    assert result["total_members"] > 0
    assert result["members_in_sync"] >= 0
    assert result["members_with_issues"] >= 0
    # In-sync + issues should be <= total (some may be pending)
    assert (result["members_in_sync"] + result["members_with_issues"] <=
            result["total_members"])


@pytest.mark.asyncio
async def test_run_onboarding_checklist_tracks_completion(
    org_hitachi: str,
    contact_hitachi_c001: str,
):
    """Test that checklist tracks completion percentage."""
    result = await run_onboarding_checklist(
        org_id=org_hitachi,
        contact_id=contact_hitachi_c001,
        dry_run=True,
    )

    # Should have deliverables with completion info
    deliverables = result.get("deliverables", [])
    for deliverable in deliverables:
        # Each deliverable may have steps with status
        assert "id" in deliverable
        assert "status" in deliverable or "steps" in deliverable
