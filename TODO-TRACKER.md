# TODO Tracker

This document tracks all TODO and FIXME comments from the source code, plus pending integration work. Items are organized by file and include line numbers for reference.

**Last updated:** March 3, 2026

## src/aaif_mcp_server/tools/compliance.py

### Lines 46-48: Descartes Screening Field Integration
**Priority:** Production Phase
**Status:** Pending SFDC Sandbox Connection

Once the SFDC sandbox is connected, read the actual Descartes screening result field (e.g., `Screening_Status__c`, `Descartes_Result__c`). Currently returns clear status since Descartes handles sanctions screening at membership intake in Salesforce.

**Related Code:**
- `check_sanctions()` function
- SFDC/Descartes integration point
- Requires field name confirmation during sandbox validation

---

## PIS Connector Integration Status

### PIS Groups.io (`pis_groupsio.py`) — ✅ Built
**Status:** Built, awaiting credentials (PIS_ACL_TOKEN, AAIF_PROJECT_ID)
- Connector: `pis_groupsio.py` (subgroup cache, member CRUD, two-step removal)
- Registry: wired in `registry.py`, env-var toggled
- Tests: 33 tests passing (`test_pis_groupsio.py`)
- MCP tools wired: `provision_mailing_lists`, `remove_from_mailing_lists`, `check_mailing_list_membership`, `remediate_mailing_lists`

### PIS Meeting (`pis_meeting.py`) — ✅ Built + MCP Tools Wired
**Status:** Built, MCP tools updated, awaiting credentials
- Connector: `pis_meeting.py` (meeting cache, registrant CRUD, mailing list sync, bulk ops)
- Registry: wired in `registry.py`, env-var toggled
- Tests: 33 connector tests (`test_pis_meeting.py`) + 13 tool integration tests (`test_tools_meeting_integration.py`)
- MCP tools wired:
  - `provision_calendar_invites` → PIS registrant provisioning (replaces GoogleCalendar)
  - `get_upcoming_meetings` → PIS registrant query with join links
  - `update_meeting_schedule` → PIS meeting update by committee
  - `run_offboarding_checklist` → PIS registrant removal (replaces manual step)
  - `enroll_in_working_group` → PIS committee-scoped registrant provisioning

### PIS GitHub (`pis_github.py`) — ✅ Built
**Status:** Built, read-only, awaiting credentials
- Connector: `pis_github.py` (org/repo listing)
- Registry: wired in `registry.py`, env-var toggled
- Tests: passing in `test_pis_github.py`

---

## Pending Access / Credentials

| Item | Status | Who | Notes |
|------|--------|-----|-------|
| AAIF `project_id` in PIS | **Requested** (Mar 3) | David Deal | Needed for all PIS connectors |
| M2M token for server-to-server | **Requested** (Mar 3) | David Deal | Needed for Cloud Run deployment |
| PIS role assignment for Manish | Pending confirmation with Heather | David/Heather | Needed for user token auth |
| aaif-staging GitHub org invites | Sent by Rudy | Manish | Need to accept at github.com/orgs/aaif-staging |
| Discord access (Chrissy) | Pending outreach | Manish → Chrissy | Per Rudy's suggestion |

---

## Test Suite Summary

**Total:** 176 passing, 28 pre-existing failures

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_pis_groupsio.py` | 33 | ✅ All pass |
| `test_pis_meeting.py` | 33 | ✅ All pass |
| `test_tools_meeting_integration.py` | 13 | ✅ All pass |
| `test_pis_github.py` | ~10 | ✅ All pass |
| `test_onboarding_flow.py` | ~20 | ✅ All pass |
| Others (mock-based) | ~67 | ✅ All pass |
| `test_press_release.py` | 3 | ❌ Pre-existing (registry not init) |
| `test_renewal_intelligence.py` | 8 | ❌ Pre-existing (registry not init) |
| `test_tier_validation.py` | 5 | ❌ Pre-existing (registry not init) |
| `test_wg_enrollment.py` | 12 | ❌ Pre-existing (registry not init) |

*The 28 pre-existing failures are in test files that call tools directly without initializing the connector registry. Fix: add registry init fixture or mock the registry in those tests.*

---

## Summary

**Total TODOs:** 1 (compliance.py)
**PIS Connectors Built:** 3 (Groups.io, Meeting, GitHub)
**MCP Tools Wired to PIS:** 7 tools across 4 tool files
**Pending:** Credentials from David, then incremental live endpoint testing
