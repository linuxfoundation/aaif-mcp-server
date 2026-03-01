from __future__ import annotations
"""Domain 10: Onboarding Call Scheduling — 3 tools.

Maps to: Deliverable D4 (Orientation & Initial Outreach)
PRD Requirements: SCHED-1 through SCHED-3

These tools schedule, reschedule, and track onboarding calls between LF staff
and new member contacts. Uses the Calendar connector for sending invites.
"""

from datetime import datetime
from typing import Optional

from ..connectors.registry import get_sfdc, get_calendar
from ..config import MOCK_LF_STAFF, MOCK_ONBOARDING_CALLS


async def schedule_onboarding_call(
    org_id: str, contact_ids_str: str, lf_staff_ids_str: str = "", foundation_id: str = "aaif"
) -> dict:
    """Schedule an onboarding call with member contacts and LF staff.

    Args:
        org_id: Salesforce organization ID
        contact_ids_str: Comma-separated contact IDs (e.g., "C001,C002")
        lf_staff_ids_str: Comma-separated LF staff IDs. If empty, auto-assigns based on role.
                          (e.g., "staff-001,staff-002")
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Confirmation of scheduled call with meeting details.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    # Parse contact IDs
    contact_ids = [c.strip() for c in contact_ids_str.split(",") if c.strip()]
    contacts = []
    for contact_id in contact_ids:
        found = False
        for c in org.contacts:
            if c.contact_id == contact_id:
                contacts.append(c)
                found = True
                break
        if not found:
            return {
                "error": "CONTACT_NOT_FOUND",
                "message": f"Contact '{contact_id}' not found in org",
            }

    # Assign LF staff
    if lf_staff_ids_str:
        staff_ids = [s.strip() for s in lf_staff_ids_str.split(",") if s.strip()]
        staff = []
        for staff_id in staff_ids:
            if staff_id not in MOCK_LF_STAFF:
                return {
                    "error": "STAFF_NOT_FOUND",
                    "message": f"LF staff '{staff_id}' not found",
                }
            staff.append(MOCK_LF_STAFF[staff_id])
    else:
        # Auto-assign based on onboarding role: Membership for primary, Coordinator for technical
        staff = []
        for c in contacts:
            if c.role.value == "voting_contact":
                staff.append(MOCK_LF_STAFF["staff-001"])  # Jennifer Tarnate
            elif c.role.value == "primary_contact":
                staff.append(MOCK_LF_STAFF["staff-002"])  # Candy Tan
            else:
                staff.append(MOCK_LF_STAFF["staff-003"])  # Christina Harter

    # Generate meeting ID
    meeting_id = f"mtg-{org_id[-6:]}"

    # Prepare attendees list
    attendees = [c.email for c in contacts] + [s["email"] for s in staff]
    zoom_link = f"https://zoom.us/j/onboard-{org.org_name.lower().replace(' ', '-')}"

    # Create event
    event = {
        "title": f"Onboarding Call: {org.org_name}",
        "description": f"AAIF Onboarding for {org.org_name}. Participants: {', '.join([c.name for c in contacts])}",
        "start_time": "2026-03-10T14:00:00Z",  # Mock time
        "end_time": "2026-03-10T15:00:00Z",
        "zoom_link": zoom_link,
    }

    # Send invites
    invite_results = []
    for email in attendees:
        result = await get_calendar().send_invite(email, event)
        invite_results.append({
            "email": email,
            "status": result.get("status"),
            "event_id": result.get("event_id"),
        })

    # Update mock onboarding calls
    MOCK_ONBOARDING_CALLS[org_id] = {
        "meeting_id": meeting_id,
        "status": "scheduled",
        "scheduled_at": "2026-03-10T14:00:00Z",
        "attendees": attendees,
        "zoom_link": zoom_link,
    }

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "meeting_id": meeting_id,
        "scheduled_at": "2026-03-10T14:00:00Z",
        "duration_minutes": 60,
        "member_contacts": [
            {"contact_id": c.contact_id, "name": c.name, "email": c.email, "role": c.role.value}
            for c in contacts
        ],
        "lf_staff": [
            {"staff_id": s.get("name"), "name": s.get("name"), "email": s.get("email"), "role": s.get("role")}
            for s in staff
        ],
        "zoom_link": zoom_link,
        "total_attendees": len(attendees),
        "invite_results": invite_results,
        "message": f"Onboarding call scheduled for {org.org_name}. Invites sent to {len(attendees)} participants.",
    }


async def reschedule_onboarding_call(
    meeting_id: str, new_time: str, foundation_id: str = "aaif"
) -> dict:
    """Reschedule an existing onboarding call.

    Args:
        meeting_id: Meeting ID to reschedule (e.g., "mtg-001")
        new_time: New meeting time (ISO 8601 format, e.g., "2026-03-15T10:00:00Z")
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Confirmation of rescheduled call with updated details.
    """
    # Find the call
    org_id = None
    for oid, call in MOCK_ONBOARDING_CALLS.items():
        if call.get("meeting_id") == meeting_id:
            org_id = oid
            break

    if not org_id:
        return {
            "error": "MEETING_NOT_FOUND",
            "message": f"No onboarding call found with meeting_id '{meeting_id}'",
        }

    call = MOCK_ONBOARDING_CALLS[org_id]
    old_time = call.get("scheduled_at")

    # Update call
    call["scheduled_at"] = new_time
    call["status"] = "rescheduled"

    # Send update invites
    update_results = []
    for email in call.get("attendees", []):
        result = await get_calendar().send_invite(email, {
            "title": f"[RESCHEDULED] Onboarding Call",
            "description": f"Meeting rescheduled from {old_time} to {new_time}",
            "start_time": new_time,
        })
        update_results.append({
            "email": email,
            "status": result.get("status"),
        })

    return {
        "meeting_id": meeting_id,
        "org_id": org_id,
        "old_time": old_time,
        "new_time": new_time,
        "status": "rescheduled",
        "attendees_notified": len(call.get("attendees", [])),
        "update_results": update_results,
        "message": f"Onboarding call {meeting_id} rescheduled from {old_time} to {new_time}. All {len(update_results)} participants notified.",
    }


async def get_onboarding_call_status(org_id: str, foundation_id: str = "aaif") -> dict:
    """Get the status of an organization's onboarding call.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Onboarding call status and details.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    call = MOCK_ONBOARDING_CALLS.get(org_id)

    if not call:
        return {
            "org_id": org_id,
            "org_name": org.org_name,
            "status": "pending",
            "meeting_id": None,
            "scheduled_at": None,
            "attendees": [],
            "zoom_link": None,
            "message": f"No onboarding call scheduled for {org.org_name}. Status: PENDING",
        }

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "status": call.get("status"),
        "meeting_id": call.get("meeting_id"),
        "scheduled_at": call.get("scheduled_at"),
        "attendees": call.get("attendees", []),
        "attendee_count": len(call.get("attendees", [])),
        "zoom_link": call.get("zoom_link"),
        "message": f"Onboarding call for {org.org_name}: {call.get('status', 'pending').upper()}. "
                  f"Meeting: {call.get('scheduled_at') or 'Not scheduled'}",
    }
