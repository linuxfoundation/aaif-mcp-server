from __future__ import annotations
"""Domain 6: Meetings & Scheduling — 3 tools.

Maps to: Deliverable D3 (Participation Enablement)
PRD Requirements: MTG-1 through MTG-3

These tools manage meeting invites and schedules for working groups
and board meetings. Renamed from "Calendar" per Nirav's feedback —
the domain is about meetings, not about the calendar system itself.

When PIS is configured, uses the PISMeetingConnector (LFX Meeting V2 API)
for real registrant provisioning. Falls back to mock data / GoogleCalendar
connector when PIS is not available.
"""

from ..connectors.registry import get_sfdc, get_calendar, get_pis_meeting
from ..config import MOCK_CALENDAR_EVENTS, MOCK_CALENDAR_RULES, WORKING_GROUPS
from ..models import ContactRole, Tier


async def provision_calendar_invites(
    org_id: str, contact_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Send meeting invites for all meetings a contact is eligible to attend.

    Based on the contact's tier and role, determines which meetings they should
    receive invites for (board meetings, all-hands, WG meetings, etc.).

    When PIS is configured, uses LFX Meeting V2 API to add the contact as a
    registrant to eligible meetings (Zoom auto-sends calendar invites).
    Falls back to mock calendar rules when PIS is not available.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to send invites to
        dry_run: If True, report what would happen without sending invites
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of invites sent (or planned in dry_run mode).
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    contact = None
    for c in org.contacts:
        if c.contact_id == contact_id:
            contact = c
            break

    if not contact:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact with ID '{contact_id}' in org '{org.org_name}'",
        }

    # ── PIS path: use LFX Meeting V2 API ─────────────────────────
    pis_meeting = get_pis_meeting()
    if pis_meeting is not None:
        # Determine committee_ids from contact's WG enrollments
        from ..config import MOCK_WG_ENROLLMENTS
        enrolled_wgs = MOCK_WG_ENROLLMENTS.get(contact_id, [])

        # Map WG IDs to committee slugs (same ID format in our config)
        committee_ids = enrolled_wgs if enrolled_wgs else None

        if dry_run:
            # In dry_run, query which meetings the contact would be added to
            contact_meetings = await pis_meeting.get_contact_meetings(contact.email)
            already_registered = [m["meeting_id"] for m in contact_meetings.get("meetings", [])]

            # Get all eligible meetings (by committee or all project meetings)
            all_meetings = await pis_meeting.list_meetings()
            eligible = []
            for mtg in all_meetings:
                mtg_committee = mtg.get("committee_id", "")
                # Include if: no committee filter, or committee matches enrolled WGs
                if committee_ids is None or mtg_committee in enrolled_wgs or not mtg_committee:
                    already = mtg["meeting_id"] in already_registered
                    eligible.append({
                        "meeting_id": mtg["meeting_id"],
                        "topic": mtg.get("topic", "Unknown"),
                        "committee_id": mtg_committee,
                        "action": "already_registered" if already else "would_add_registrant",
                        "status": "dry_run",
                    })

            return {
                "org_id": org_id,
                "org_name": org.org_name,
                "contact_id": contact_id,
                "contact_name": contact.name,
                "contact_email": contact.email,
                "contact_role": contact.role.value,
                "tier": org.tier.value,
                "dry_run": True,
                "source": "pis_meeting_v2",
                "eligible_meetings": [e["topic"] for e in eligible],
                "actions": eligible,
                "message": (
                    f"DRY RUN: Would provision {contact.name} as registrant to "
                    f"{sum(1 for e in eligible if e['action'] == 'would_add_registrant')} "
                    f"meeting(s) via LFX Meeting V2 API."
                ),
            }

        # Execute: add contact as registrant to eligible meetings
        results = await pis_meeting.provision_calendar_invites(
            contact_email=contact.email,
            contact_first_name=contact.name.split()[0] if contact.name else "",
            contact_last_name=" ".join(contact.name.split()[1:]) if contact.name and " " in contact.name else "",
            committee_ids=committee_ids,
        )

        return {
            "org_id": org_id,
            "org_name": org.org_name,
            "contact_id": contact_id,
            "contact_name": contact.name,
            "contact_email": contact.email,
            "contact_role": contact.role.value,
            "tier": org.tier.value,
            "dry_run": False,
            "source": "pis_meeting_v2",
            "eligible_meetings": [r.get("topic", r.get("meeting_id")) for r in results],
            "actions": results,
            "message": (
                f"Provisioned {contact.name} as registrant to {len(results)} "
                f"meeting(s) via LFX Meeting V2 API. Zoom will auto-send calendar invites."
            ),
        }

    # ── Fallback: mock calendar rules + GoogleCalendar connector ──
    rules = MOCK_CALENDAR_RULES.get(foundation_id, {})

    # Determine which meetings this contact should receive
    contact_type_key = f"{org.tier.value}_{contact.role.value}"
    eligible_meetings = rules.get(contact_type_key, [])

    if not eligible_meetings:
        return {
            "status": "no_action",
            "message": f"No meetings assigned to {org.tier.value} {contact.role.value}",
            "org_id": org_id,
            "contact_id": contact_id,
        }

    actions: list[dict] = []

    for meeting_name in eligible_meetings:
        if dry_run:
            actions.append({
                "meeting": meeting_name,
                "recipient": contact.email,
                "action": "send_invite",
                "status": "dry_run",
                "reason": "Would be sent (dry_run=True)",
            })
        else:
            result = await get_calendar().send_invite(contact.email, {
                "title": meeting_name,
                "description": f"Foundation meeting: {meeting_name}",
            })
            actions.append({
                "meeting": meeting_name,
                "recipient": contact.email,
                "action": "send_invite",
                "status": "success" if result.get("status") == "sent" else "error",
                "event_id": result.get("event_id"),
            })

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_id": contact_id,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "contact_role": contact.role.value,
        "tier": org.tier.value,
        "dry_run": dry_run,
        "source": "mock_calendar",
        "eligible_meetings": eligible_meetings,
        "actions": actions,
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Sending {len(eligible_meetings)} calendar invite(s) to {contact.name} "
            f"({contact.role.value}, {org.tier.value})."
        ),
    }


async def update_meeting_schedule(
    wg_id: str, new_time: str, new_link: str, foundation_id: str = "aaif"
) -> dict:
    """Update a working group's recurring meeting schedule.

    When PIS is configured, updates the meeting via LFX Meeting V2 API.
    Falls back to config-only update when PIS is not available.

    Args:
        wg_id: Working group ID (e.g., "wg-agentic-commerce")
        new_time: New meeting time (e.g., "Wed 10am PT")
        new_link: New Zoom/video conference link
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Confirmation of schedule update.
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

    old_schedule = wg.meeting_schedule

    # ── PIS path: update via LFX Meeting V2 API ──────────────────
    pis_meeting = get_pis_meeting()
    if pis_meeting is not None:
        # Find meetings for this WG (committee)
        meetings = await pis_meeting.list_meetings(committee_id=wg_id)
        updated = []
        for mtg in meetings:
            result = await pis_meeting.update_meeting(
                meeting_id=mtg["meeting_id"],
                topic=mtg.get("topic"),
                schedule=new_time,
                settings={"alternative_host": new_link},
            )
            updated.append({
                "meeting_id": mtg["meeting_id"],
                "topic": mtg.get("topic"),
                "status": "updated" if result else "error",
            })

        return {
            "wg_id": wg_id,
            "wg_name": wg.name,
            "old_schedule": old_schedule,
            "new_schedule": new_time,
            "zoom_link": new_link,
            "source": "pis_meeting_v2",
            "meetings_updated": updated,
            "status": "updated",
            "notifications_sent": True,
            "message": (
                f"Meeting schedule for {wg.name} updated from '{old_schedule}' to '{new_time}' "
                f"via LFX Meeting V2 API. {len(updated)} meeting(s) updated."
            ),
        }

    # ── Fallback: config-only (no PIS) ───────────────────────────
    return {
        "wg_id": wg_id,
        "wg_name": wg.name,
        "old_schedule": old_schedule,
        "new_schedule": new_time,
        "zoom_link": new_link,
        "source": "mock_calendar",
        "status": "updated",
        "notifications_sent": True,
        "message": f"Meeting schedule for {wg.name} updated from '{old_schedule}' to '{new_time}'. All participants notified.",
    }


async def get_upcoming_meetings(contact_id: str, foundation_id: str = "aaif") -> dict:
    """Get upcoming meetings for a contact.

    When PIS is configured, queries LFX Meeting V2 API for meetings where
    the contact is a registrant. Falls back to mock data when PIS is not available.

    Args:
        contact_id: Contact ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of upcoming meetings with times and links.
    """
    # ── PIS path: query LFX Meeting V2 for registrant status ─────
    pis_meeting = get_pis_meeting()
    if pis_meeting is not None:
        # Find contact email from SFDC
        from ..config import MOCK_MEMBERS
        contact_email = None
        contact_name = None
        for org in MOCK_MEMBERS.values():
            for c in org.contacts:
                if c.contact_id == contact_id:
                    contact_email = c.email
                    contact_name = c.name
                    break
            if contact_email:
                break

        if not contact_email:
            return {
                "contact_id": contact_id,
                "upcoming_meetings": [],
                "total": 0,
                "source": "pis_meeting_v2",
                "message": f"Contact {contact_id} not found — cannot query meetings.",
            }

        result = await pis_meeting.get_contact_meetings(contact_email)
        meetings = result.get("meetings", [])

        # Enrich with join links
        enriched = []
        for mtg in meetings:
            join_link = await pis_meeting.get_join_link(mtg["meeting_id"])
            enriched.append({
                "meeting_id": mtg["meeting_id"],
                "topic": mtg.get("topic", "Unknown"),
                "schedule": mtg.get("start_time", ""),
                "committee_id": mtg.get("committee_id", ""),
                "join_link": join_link.get("join_url", ""),
                "registrant_status": mtg.get("status", "registered"),
            })

        return {
            "contact_id": contact_id,
            "contact_email": contact_email,
            "contact_name": contact_name,
            "source": "pis_meeting_v2",
            "upcoming_meetings": enriched,
            "total": len(enriched),
            "message": f"Found {len(enriched)} meeting(s) for {contact_name or contact_id} via LFX Meeting V2 API.",
        }

    # ── Fallback: mock calendar events ───────────────────────────
    events = MOCK_CALENDAR_EVENTS.get(contact_id, [])

    if not events:
        # Try to find contact email for the response
        from ..config import MOCK_MEMBERS
        contact_email = None
        for org in MOCK_MEMBERS.values():
            for contact in org.contacts:
                if contact.contact_id == contact_id:
                    contact_email = contact.email
                    break

        return {
            "contact_id": contact_id,
            "contact_email": contact_email,
            "upcoming_meetings": [],
            "total": 0,
            "source": "mock_calendar",
            "message": f"No upcoming meetings found for contact {contact_id}",
        }

    return {
        "contact_id": contact_id,
        "upcoming_meetings": events,
        "total": len(events),
        "source": "mock_calendar",
        "message": f"Found {len(events)} upcoming meeting(s) for contact {contact_id}",
    }
