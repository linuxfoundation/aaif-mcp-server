from __future__ import annotations
"""Domain 7: Working Group Enrollment — 5 tools.

Maps to: Deliverable D3 (Participation Enablement)
PRD Requirements: WGE-1 through WGE-5

These tools manage enrollment across multiple systems (mailing lists, Discord,
GitHub, calendar). Enrollment happens across all systems; removal is the inverse.

Per Nirav's feedback: WG enrollment may be self-service (member-facing via
Intercom) or manual (PMO staff via PCC). The `caller_role` parameter enables
future routing — when called from a member context, enrollment follows the
self-service flow; when called from PMO context, it follows the manual flow.
"""

from ..connectors.registry import get_sfdc, get_groupsio, get_discord, get_github, get_pis_meeting, get_pis_github
from ..config import MOCK_WG_ENROLLMENTS, WORKING_GROUPS
from ..models import ContactRole, Tier


async def enroll_in_working_group(
    contact_id: str, wg_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Enroll a contact in a working group across all systems.

    Enrolls the contact in:
    - Mailing list
    - Discord channel
    - GitHub repository
    - Meeting invites for WG meetings

    This tool supports both self-service (member-initiated via Intercom)
    and manual (PMO staff via PCC) enrollment flows. The caller context
    determines which flow is used.

    Args:
        contact_id: Contact ID
        wg_id: Working group ID (e.g., "wg-agentic-commerce")
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Enrollment status across all systems.
    """
    # Find contact across all orgs
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    # Find WG
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Check eligibility (any member can join by default, role-restricted WGs would need more logic)
    if org.status != "active":
        return {
            "error": "ORG_NOT_ACTIVE",
            "message": f"Organization must be active to enroll in working groups",
        }

    # Determine connector sources
    pis_meeting = get_pis_meeting()
    pis_github = get_pis_github()
    meeting_source = "pis_meeting_v2" if pis_meeting is not None else "mock_calendar"
    github_source = "pis_github_v2" if pis_github is not None else "mock_github"

    # If PIS GitHub is available, verify WG repo exists in PIS
    pis_repo_info = None
    if pis_github is not None and wg.github_repo:
        # WG repo format is usually "org/repo" or just "repo"
        repo_parts = wg.github_repo.split("/", 1)
        if len(repo_parts) == 2:
            pis_repo_info = await pis_github.get_repo(repo_parts[0], repo_parts[1])
        else:
            # Try listing repos and matching by name
            orgs = await pis_github.list_orgs()
            for org_info in orgs:
                org_name = org_info.get("organization", "")
                if org_name:
                    repo_info = await pis_github.get_repo(org_name, wg.github_repo)
                    if repo_info:
                        pis_repo_info = repo_info
                        break

    # Prepare enrollment actions
    actions = {
        "mailing_list": {"action": "add", "target": wg.mailing_list},
        "discord": {"action": "add", "target": wg.discord_channel},
        "github": {"action": "add", "target": wg.github_repo, "source": github_source},
        "meeting": {"action": "add_registrant" if pis_meeting else "send_invite", "target": wg.meeting_schedule, "source": meeting_source},
    }

    if dry_run:
        meeting_dry_run = f"Would send meeting invite for {wg.meeting_schedule}"
        if pis_meeting is not None:
            meeting_dry_run = f"Would add as registrant to {wg_id} meetings via LFX Meeting V2 API"

        github_dry_run = f"Would add {contact.github_username or 'N/A'} to {wg.github_repo}"
        if pis_github is not None and pis_repo_info:
            dco = pis_repo_info.get("dco_enabled", False)
            github_dry_run = (
                f"Would add {contact.github_username or 'N/A'} to {wg.github_repo} "
                f"(PIS-verified, DCO={'enabled' if dco else 'disabled'})"
            )

        return {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "wg_id": wg_id,
            "wg_name": wg.name,
            "dry_run": True,
            "enrollment_actions": {
                "mailing_list": f"Would add {contact.email} to {wg.mailing_list}",
                "discord": f"Would add {contact.discord_handle or 'N/A'} to {wg.discord_channel}",
                "github": github_dry_run,
                "meeting": meeting_dry_run,
            },
            "meeting_source": meeting_source,
            "github_source": github_source,
            "pis_repo_verified": pis_repo_info is not None,
            "message": f"DRY RUN: Would enroll {contact.name} in {wg.name} across 4 systems.",
        }

    # Execute enrollment
    # GitHub: add collaborator via direct GitHub API, enriched with PIS metadata
    if contact.github_username:
        github_result = await get_github().add_collaborator(contact.github_username, wg.github_repo)
        github_result["source"] = github_source
        if pis_repo_info:
            github_result["pis_repo_verified"] = True
            github_result["dco_enabled"] = pis_repo_info.get("dco_enabled", False)
    else:
        github_result = {"status": "skipped", "reason": "No GitHub username", "source": github_source}

    enrollment_results = {
        "mailing_list": await get_groupsio().add_member(wg.mailing_list, contact.email),
        "discord": await get_discord().add_role(contact.discord_handle or contact.name, wg.discord_channel) if contact.discord_handle else {"status": "skipped", "reason": "No Discord handle"},
        "github": github_result,
    }

    # Meeting invite: PIS or mock
    if pis_meeting is not None:
        meeting_results = await pis_meeting.provision_calendar_invites(
            contact_email=contact.email,
            contact_first_name=contact.name.split()[0] if contact.name else "",
            contact_last_name=" ".join(contact.name.split()[1:]) if contact.name and " " in contact.name else "",
            committee_ids=[wg_id],
        )
        enrollment_results["meeting"] = {
            "status": "provisioned",
            "source": "pis_meeting_v2",
            "meetings_added": len(meeting_results),
        }
    else:
        enrollment_results["meeting"] = {
            "status": "mock_sent",
            "source": "mock_calendar",
            "target": wg.meeting_schedule,
        }

    # Track in mock enrollment data
    if contact_id not in MOCK_WG_ENROLLMENTS:
        MOCK_WG_ENROLLMENTS[contact_id] = []
    if wg_id not in MOCK_WG_ENROLLMENTS[contact_id]:
        MOCK_WG_ENROLLMENTS[contact_id].append(wg_id)

    return {
        "org_id": org.org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "wg_id": wg_id,
        "wg_name": wg.name,
        "dry_run": False,
        "meeting_source": meeting_source,
        "github_source": github_source,
        "pis_repo_verified": pis_repo_info is not None,
        "enrollment_results": enrollment_results,
        "message": f"Enrolled {contact.name} in {wg.name}. Provisioned to mailing list, Discord, GitHub, and meetings.",
    }


async def leave_working_group(
    contact_id: str, wg_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Remove a contact from a working group across all systems.

    Args:
        contact_id: Contact ID
        wg_id: Working group ID
        dry_run: If True, report changes without making them
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Unenrollment status across all systems.
    """
    # Find contact across all orgs
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    # Find WG
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Determine connector sources for leave
    pis_meeting = get_pis_meeting()
    pis_github = get_pis_github()
    meeting_source = "pis_meeting_v2" if pis_meeting is not None else "mock_calendar"
    github_source = "pis_github_v2" if pis_github is not None else "mock_github"

    if dry_run:
        meeting_dry_run = f"Would remove from {wg.meeting_schedule} meeting invites"
        if pis_meeting is not None:
            meeting_dry_run = f"Would remove as registrant from {wg_id} meetings via LFX Meeting V2 API"

        github_dry_run = f"Would remove {contact.github_username or 'N/A'} from {wg.github_repo}"
        if pis_github is not None:
            github_dry_run += " (PIS-tracked repo)"

        return {
            "org_id": org.org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "wg_id": wg_id,
            "wg_name": wg.name,
            "dry_run": True,
            "unenrollment_actions": {
                "mailing_list": f"Would remove {contact.email} from {wg.mailing_list}",
                "discord": f"Would remove {contact.discord_handle or 'N/A'} from {wg.discord_channel}",
                "github": github_dry_run,
                "meeting": meeting_dry_run,
            },
            "meeting_source": meeting_source,
            "github_source": github_source,
            "message": f"DRY RUN: Would remove {contact.name} from {wg.name} across 4 systems.",
        }

    # Execute unenrollment
    # GitHub: remove collaborator, enriched with PIS metadata
    if contact.github_username:
        github_result = await get_github().remove_collaborator(contact.github_username, wg.github_repo)
        github_result["source"] = github_source
    else:
        github_result = {"status": "skipped", "reason": "No GitHub username", "source": github_source}

    unenrollment_results = {
        "mailing_list": await get_groupsio().remove_member(wg.mailing_list, contact.email),
        "discord": await get_discord().remove_role(contact.discord_handle or contact.name, wg.discord_channel) if contact.discord_handle else {"status": "skipped"},
        "github": github_result,
    }

    # Meeting removal: PIS or skip
    if pis_meeting is not None:
        # Remove registrant from WG-scoped meetings
        meeting_removal = await pis_meeting.remove_from_all_meetings(
            contact_email=contact.email,
            committee_ids=[wg_id],
        )
        unenrollment_results["meeting"] = {
            "status": "removed",
            "source": "pis_meeting_v2",
            "meetings_removed": len(meeting_removal),
        }
    else:
        unenrollment_results["meeting"] = {
            "status": "mock_removed",
            "source": "mock_calendar",
            "target": wg.meeting_schedule,
        }

    # Update mock enrollment data
    if contact_id in MOCK_WG_ENROLLMENTS and wg_id in MOCK_WG_ENROLLMENTS[contact_id]:
        MOCK_WG_ENROLLMENTS[contact_id].remove(wg_id)

    return {
        "org_id": org.org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "wg_id": wg_id,
        "wg_name": wg.name,
        "dry_run": False,
        "meeting_source": meeting_source,
        "github_source": github_source,
        "unenrollment_results": unenrollment_results,
        "message": f"Removed {contact.name} from {wg.name}. Removed from mailing list, Discord, GitHub, and meetings.",
    }


async def list_available_working_groups(contact_id: str, foundation_id: str = "aaif") -> dict:
    """List all working groups with contact's current enrollment status.

    Args:
        contact_id: Contact ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of working groups with access levels.
    """
    # Find contact
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    wgs = WORKING_GROUPS.get(foundation_id, [])
    enrolled_wgs = MOCK_WG_ENROLLMENTS.get(contact_id, [])

    available = []
    for wg in wgs:
        available.append({
            "wg_id": wg.wg_id,
            "wg_name": wg.name,
            "meeting_schedule": wg.meeting_schedule,
            "enrolled": wg.wg_id in enrolled_wgs,
            "access_policy": wg.access_policy.value,
        })

    return {
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "org_id": org.org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "available_working_groups": available,
        "enrolled_count": len(enrolled_wgs),
        "total_wgs": len(wgs),
        "message": f"{contact.name} is enrolled in {len(enrolled_wgs)}/{len(wgs)} working groups.",
    }


async def get_wg_members(wg_id: str, foundation_id: str = "aaif") -> dict:
    """Get member roster for a working group.

    Args:
        wg_id: Working group ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of members enrolled in the WG.
    """
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Find all contacts enrolled in this WG
    members = []
    for contact_id, wg_ids in MOCK_WG_ENROLLMENTS.items():
        if wg_id in wg_ids:
            # Find contact details
            all_orgs = await get_sfdc().list_orgs(foundation_id)
            for org in all_orgs:
                for contact in org.contacts:
                    if contact.contact_id == contact_id:
                        members.append({
                            "contact_id": contact.contact_id,
                            "name": contact.name,
                            "email": contact.email,
                            "org_id": org.org_id,
                            "org_name": org.org_name,
                            "tier": org.tier.value,
                            "role": contact.role.value,
                        })
                        break

    # Enrich with PIS GitHub repo info if available
    pis_github = get_pis_github()
    repo_info = None
    if pis_github is not None and wg.github_repo:
        repo_parts = wg.github_repo.split("/", 1)
        if len(repo_parts) == 2:
            repo_info = await pis_github.get_repo(repo_parts[0], repo_parts[1])

    result = {
        "wg_id": wg_id,
        "wg_name": wg.name,
        "members": members,
        "total_members": len(members),
        "message": f"Working group '{wg.name}' has {len(members)} enrolled member(s).",
    }

    if repo_info:
        result["github_repo"] = {
            "name": wg.github_repo,
            "source": "pis_github_v2",
            "dco_enabled": repo_info.get("dco_enabled", False),
            "archived": repo_info.get("archived", False),
            "has_issues": repo_info.get("has_issues", True),
        }

    return result


async def check_wg_eligibility(contact_id: str, wg_id: str, foundation_id: str = "aaif") -> dict:
    """Check if a contact is eligible to join a working group.

    Args:
        contact_id: Contact ID
        wg_id: Working group ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Eligibility status and reason.
    """
    # Find contact
    all_orgs = await get_sfdc().list_orgs(foundation_id)
    contact = None
    org = None

    for o in all_orgs:
        for c in o.contacts:
            if c.contact_id == contact_id:
                contact = c
                org = o
                break
        if contact:
            break

    if not contact or not org:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}'",
        }

    # Find WG
    wgs = WORKING_GROUPS.get(foundation_id, [])
    wg = None
    for w in wgs:
        if w.wg_id == wg_id:
            wg = w
            break

    if not wg:
        return {
            "error": "WG_NOT_FOUND",
            "message": f"No working group with ID '{wg_id}'",
        }

    # Check eligibility
    eligible = True
    reasons = []

    if org.status != "active":
        eligible = False
        reasons.append(f"Organization status is '{org.status}', must be active")

    if wg.access_policy.value == "role_restricted":
        # For demo, only voting_contact and technical_contact can access restricted WGs
        if contact.role not in [ContactRole.voting_contact, ContactRole.technical_contact]:
            eligible = False
            reasons.append(f"Role '{contact.role.value}' not authorized for role-restricted WG")

    already_enrolled = contact_id in MOCK_WG_ENROLLMENTS and wg_id in MOCK_WG_ENROLLMENTS[contact_id]
    if already_enrolled:
        reasons.append("Contact is already enrolled in this WG")

    return {
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "org_id": org.org_id,
        "org_name": org.org_name,
        "wg_id": wg_id,
        "wg_name": wg.name,
        "eligible": eligible,
        "already_enrolled": already_enrolled,
        "reasons": reasons,
        "message": (
            f"{'Eligible' if eligible else 'Not eligible'} to join {wg.name}. "
            f"{', '.join(reasons) if reasons else 'No restrictions.'}"
        ),
    }
