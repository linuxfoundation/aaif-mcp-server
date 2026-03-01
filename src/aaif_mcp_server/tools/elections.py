"""Domain 7: Election & Voting Operations — 5 tools.

Manages WG Chair elections, voter eligibility, candidate qualification, and
ballot access diagnostics.
"""

import logging
from datetime import datetime

from ..config import MOCK_MEMBERS, MOCK_ELECTIONS, WORKING_GROUPS
from ..connectors.registry import get_sfdc, get_lfx
from ..models import Tier

logger = logging.getLogger(__name__)


async def create_election(
    wg_id: str, position: str, nomination_end: str,
    voting_start: str, voting_end: str, foundation_id: str = "aaif"
) -> dict:
    """Create a new election in LFX Platform.

    Args:
        wg_id: Working group ID
        position: Position title (e.g., "WG Chair")
        nomination_end: Nomination end date (YYYY-MM-DD)
        voting_start: Voting start date (YYYY-MM-DD)
        voting_end: Voting end date (YYYY-MM-DD)
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Election creation result with election_id.
    """
    # Validate WG exists
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = next((w for w in wgs if w.wg_id == wg_id), None)
    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"Working group '{wg_id}' not found",
        }

    result = await get_lfx().create_election(
        wg_id, position, nomination_end, voting_start, voting_end
    )
    return result


async def validate_candidate_eligibility(
    contact_id: str, election_id: str, foundation_id: str = "aaif"
) -> dict:
    """Check if a contact is eligible to be a candidate for an election.

    For WG Chair elections, only Gold+ members are eligible.

    Args:
        contact_id: Salesforce contact ID
        election_id: Election ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Eligibility result with eligible flag and blockers.
    """
    election = MOCK_ELECTIONS.get(election_id)
    if not election:
        return {
            "error": "ELECTION_NOT_FOUND",
            "contact_id": contact_id,
            "election_id": election_id,
        }

    # Find contact and their org
    contact_info = None
    org_info = None
    for org in MOCK_MEMBERS.values():
        for contact in org.contacts:
            if contact.contact_id == contact_id:
                contact_info = contact
                org_info = org
                break
        if contact_info:
            break

    if not contact_info:
        return {
            "error": "CONTACT_NOT_FOUND",
            "contact_id": contact_id,
            "message": f"Contact {contact_id} not found",
        }

    blockers = []
    eligible = True

    # Check tier eligibility (Gold+ only for WG Chair)
    if election.get("position") == "WG Chair":
        if org_info.tier not in [Tier.gold, Tier.platinum]:
            eligible = False
            blockers.append(
                f"Tier requirement: Gold+ required; {org_info.tier.value} not eligible"
            )

    # Check LFID
    lfid_check = await get_lfx().check_lfid(contact_id)
    if not lfid_check.get("verified"):
        eligible = False
        blockers.append("LFID not verified")

    return {
        "contact_id": contact_id,
        "election_id": election_id,
        "name": contact_info.name,
        "org": org_info.org_name,
        "tier": org_info.tier.value,
        "position": election.get("position"),
        "eligible": eligible,
        "blockers": blockers,
        "message": (
            f"Candidate eligibility: {'eligible' if eligible else 'NOT ELIGIBLE'} "
            f"for {election.get('position')}"
        ),
    }


async def check_voter_eligibility(
    contact_id: str, election_id: str, foundation_id: str = "aaif"
) -> dict:
    """Check if a contact is eligible to vote in an election.

    Voters must:
    - Be from a Gold+ member org
    - Have verified LFID
    - Be on the org's voting contacts list

    Args:
        contact_id: Salesforce contact ID
        election_id: Election ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Voter eligibility result with eligible flag and blockers.
    """
    election = MOCK_ELECTIONS.get(election_id)
    if not election:
        return {
            "error": "ELECTION_NOT_FOUND",
            "contact_id": contact_id,
            "election_id": election_id,
        }

    # Find contact and their org
    contact_info = None
    org_info = None
    for org in MOCK_MEMBERS.values():
        for contact in org.contacts:
            if contact.contact_id == contact_id:
                contact_info = contact
                org_info = org
                break
        if contact_info:
            break

    if not contact_info:
        return {
            "error": "CONTACT_NOT_FOUND",
            "contact_id": contact_id,
            "message": f"Contact {contact_id} not found",
        }

    blockers = []
    eligible = True

    # Check tier eligibility (Gold+ only)
    if org_info.tier not in [Tier.gold, Tier.platinum]:
        eligible = False
        blockers.append(f"Tier requirement: Gold+ required; {org_info.tier.value} not eligible")

    # Check LFID
    lfid_check = await get_lfx().check_lfid(contact_id)
    if not lfid_check.get("verified"):
        eligible = False
        blockers.append("LFID not verified")

    return {
        "contact_id": contact_id,
        "election_id": election_id,
        "name": contact_info.name,
        "org": org_info.org_name,
        "tier": org_info.tier.value,
        "eligible": eligible,
        "blockers": blockers,
        "message": (
            f"Voter eligibility: {'eligible' if eligible else 'NOT ELIGIBLE'} "
            f"to vote in {election.get('wg_name')} {election.get('position')} election"
        ),
    }


async def get_election_status(
    election_id: str, foundation_id: str = "aaif"
) -> dict:
    """Retrieve election status, timeline, and candidate information.

    Args:
        election_id: Election ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Election status with state, candidates, timeline, and voter info.
    """
    election = MOCK_ELECTIONS.get(election_id)
    if not election:
        return {
            "error": "ELECTION_NOT_FOUND",
            "election_id": election_id,
            "message": f"Election {election_id} not found",
        }

    return {
        "election_id": election_id,
        "wg_id": election.get("wg_id"),
        "wg_name": election.get("wg_name"),
        "position": election.get("position"),
        "state": election.get("state"),
        "nomination_end": election.get("nomination_end"),
        "voting_start": election.get("voting_start"),
        "voting_end": election.get("voting_end"),
        "candidates": election.get("candidates", []),
        "total_eligible_voters": election.get("total_eligible_voters", 0),
        "votes_cast": election.get("votes_cast", 0),
        "winner": election.get("winner"),
        "participation_rate": (
            f"{(election.get('votes_cast', 0) / election.get('total_eligible_voters', 1) * 100):.1f}%"
            if election.get("total_eligible_voters", 0) > 0
            else "0%"
        ),
        "message": f"Election status: {election.get('state')} ({election.get('votes_cast', 0)}/{election.get('total_eligible_voters', 0)} votes)",
    }


async def diagnose_ballot_access(
    contact_id: str, election_id: str, foundation_id: str = "aaif"
) -> dict:
    """Diagnostic tool: check all prerequisites for ballot access.

    Returns detailed diagnostics including LFID status, tier check, ballot
    visibility, and troubleshooting suggestions.

    Args:
        contact_id: Salesforce contact ID
        election_id: Election ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Diagnostic result with detailed status of each requirement.
    """
    election = MOCK_ELECTIONS.get(election_id)
    if not election:
        return {
            "error": "ELECTION_NOT_FOUND",
            "contact_id": contact_id,
            "election_id": election_id,
        }

    # Find contact and org
    contact_info = None
    org_info = None
    for org in MOCK_MEMBERS.values():
        for contact in org.contacts:
            if contact.contact_id == contact_id:
                contact_info = contact
                org_info = org
                break
        if contact_info:
            break

    if not contact_info:
        return {
            "error": "CONTACT_NOT_FOUND",
            "contact_id": contact_id,
            "diagnostics": [],
        }

    diagnostics = []

    # Check 1: LFID status
    lfid_check = await get_lfx().check_lfid(contact_id)
    diagnostics.append({
        "check": "LFID Status",
        "status": "pass" if lfid_check.get("verified") else "fail",
        "detail": lfid_check.get("message"),
    })

    # Check 2: Tier eligibility
    tier_ok = org_info.tier in [Tier.gold, Tier.platinum]
    diagnostics.append({
        "check": "Tier Eligibility",
        "status": "pass" if tier_ok else "fail",
        "detail": f"{org_info.tier.value} member" + (
            " (Gold+ required)" if not tier_ok else ""
        ),
    })

    # Check 3: Election state
    election_open = election.get("state") in ["voting", "nominations"]
    diagnostics.append({
        "check": "Election Open",
        "status": "pass" if election_open else "fail",
        "detail": f"Election state: {election.get('state')}",
    })

    # Check 4: Ballot visibility
    ballot_check = await get_lfx().get_ballot_status(contact_id, election_id)
    ballot_visible = ballot_check.get("eligible")
    diagnostics.append({
        "check": "Ballot Visible",
        "status": "pass" if ballot_visible else "fail",
        "detail": ballot_check.get("message"),
    })

    overall_ok = all(d["status"] == "pass" for d in diagnostics)

    return {
        "contact_id": contact_id,
        "election_id": election_id,
        "name": contact_info.name,
        "org": org_info.org_name,
        "election": election.get("wg_name"),
        "can_vote": overall_ok,
        "diagnostics": diagnostics,
        "troubleshooting": (
            []
            if overall_ok
            else [d["detail"] for d in diagnostics if d["status"] == "fail"]
        ),
        "message": (
            f"Ballot access: {'OK' if overall_ok else 'BLOCKED'} "
            f"({sum(1 for d in diagnostics if d['status'] == 'pass')}/{len(diagnostics)} checks passed)"
        ),
    }
