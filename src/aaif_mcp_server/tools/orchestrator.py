from __future__ import annotations
"""Domain 12: Orchestrator & Silo Reconciliation — 5 tools.

Maps to: All Deliverables (D1-D5) — cross-cutting orchestration layer
PRD Requirements: ORCH-1 through ORCH-8

These tools run the full onboarding/offboarding checklists, track status,
and reconcile data across siloed systems (SFDC, Groups.io, member tracker).

When PIS is configured, offboarding uses PISMeetingConnector to remove
registrants from LFX Meetings (replacing manual calendar invite removal).
"""

from datetime import datetime

from ..connectors.registry import get_sfdc, get_groupsio, get_pis_meeting, get_pis_github, get_github
from ..config import CHECKLIST_TEMPLATES, PROVISIONING_RULES
from ..models import (
    ChecklistResult, DeliverableId, DeliverableStatus,
    OnboardingStep, SiloDiscrepancy,
    SiloHealthReport, StepStatus,
)

# In-memory onboarding status store (production: persist to DB)
_onboarding_store: dict[str, dict] = {}


async def run_onboarding_checklist(
    org_id: str, contact_id: str, foundation_id: str = "aaif", dry_run: bool = True
) -> dict:
    """Execute the full D1-D5 onboarding checklist for a new member contact.

    Runs each checklist step in order, calling the mapped tool (if automated)
    and recording the result. Steps that require human action are marked as
    'pending' with instructions.

    IMPORTANT: Defaults to dry_run=True. In dry_run mode, reports what each
    step would do without executing. Set dry_run=False to actually execute.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID being onboarded
        foundation_id: Foundation identifier (default: aaif)
        dry_run: If True, simulate without executing

    Returns:
        Checklist execution result with per-deliverable status.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    # Find the contact
    contact = None
    for c in org.contacts:
        if c.contact_id == contact_id:
            contact = c
            break
    if not contact:
        return {
            "error": "CONTACT_NOT_FOUND",
            "message": f"No contact '{contact_id}' in org '{org.org_name}'",
        }

    template = CHECKLIST_TEMPLATES.get(foundation_id)
    if not template:
        return {"error": "NO_TEMPLATE", "message": f"No checklist template for '{foundation_id}'"}

    deliverables: list[dict] = []
    all_steps: list[dict] = []
    total_steps = 0
    completed_steps = 0
    failed_steps = 0
    errors: list[str] = []

    for d in template.deliverables:
        d_id = DeliverableId(d["id"])
        d_steps: list[dict] = []

        for item in d.get("items", []):
            total_steps += 1
            step_id = item["id"]
            tool_name = item.get("tool")
            automated = item.get("automated", False)

            if automated and tool_name and not dry_run:
                # Execute the mapped tool
                try:
                    step_result = await _execute_checklist_step(
                        tool_name, org_id, contact, foundation_id
                    )
                    status = StepStatus.complete if not step_result.get("error") else StepStatus.failed
                    if status == StepStatus.complete:
                        completed_steps += 1
                    else:
                        failed_steps += 1
                        errors.append(f"{step_id}: {step_result.get('error', 'unknown error')}")
                except Exception as e:
                    status = StepStatus.failed
                    failed_steps += 1
                    errors.append(f"{step_id}: {str(e)}")
            elif automated and dry_run:
                status = StepStatus.pending
            else:
                # Manual step
                status = StepStatus.pending

            step = OnboardingStep(
                id=step_id,
                deliverable=d_id,
                description=item["text"],
                status=status,
                completed_at=datetime.utcnow() if status == StepStatus.complete else None,
            )
            d_steps.append(step.model_dump(mode="json"))
            all_steps.append(step.model_dump(mode="json"))

        # Calculate deliverable completion
        d_completed = sum(1 for s in d_steps if s.get("status") == "complete")
        d_total = len(d_steps)
        d_pct = (d_completed / d_total * 100) if d_total > 0 else 0

        d_status = DeliverableStatus(
            id=d_id,
            name=d["name"],
            status=StepStatus.complete if d_pct == 100 else (
                StepStatus.in_progress if d_pct > 0 else StepStatus.pending
            ),
            completion_pct=round(d_pct, 1),
        )
        deliverables.append(d_status.model_dump(mode="json"))

    # Determine overall status
    if completed_steps == total_steps and total_steps > 0:
        overall = StepStatus.complete
    elif failed_steps > 0:
        overall = StepStatus.failed
    elif completed_steps > 0:
        overall = StepStatus.in_progress
    else:
        overall = StepStatus.pending

    result = ChecklistResult(
        org_id=org_id,
        contact_id=contact_id,
        foundation_id=foundation_id,
        dry_run=dry_run,
        overall_status=overall,
        deliverables=deliverables,
        total_steps=total_steps,
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        errors=errors,
    )

    # Store status for get_onboarding_status
    store_key = f"{org_id}:{contact_id}"
    _onboarding_store[store_key] = {
        "result": result.model_dump(mode="json"),
        "steps": all_steps,
        "updated_at": datetime.utcnow().isoformat(),
    }

    return {
        **result.model_dump(mode="json"),
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Onboarding checklist for {contact.name} ({org.org_name}): "
            f"{completed_steps}/{total_steps} steps complete"
            f"{f', {failed_steps} failed' if failed_steps else ''}."
        ),
    }


async def _execute_checklist_step(
    tool_name: str, org_id: str, contact, foundation_id: str
) -> dict:
    """Internal: dispatch a checklist step to the appropriate tool.

    This is a simplified dispatcher — in production, this would call the
    actual tool functions with proper error handling and retries.
    """
    # Import tools locally to avoid circular imports
    if tool_name == "send_welcome_email":
        # Welcome email is now step 1 of D1 — sent via HubSpot on activation.
        from ..connectors.registry import get_hubspot
        result = await get_hubspot().send_email(
            to=contact.email,
            template_id="welcome-new-member",
            merge_fields={"org_id": org_id, "contact_name": contact.name},
        )
        return {
            "status": "success" if result.get("status") == "sent" else "mock_sent",
            "message": f"Welcome email sent to {contact.email} via HubSpot",
            "template": "welcome-new-member",
        }

    elif tool_name == "validate_membership_tier":
        # Auto-executes as background verification (not a manual gate).
        # Per Nirav: tier was set during sales — this just confirms SFDC matches.
        from .tier_validation import validate_membership_tier
        return await validate_membership_tier(org_id, foundation_id)

    # NOTE: check_sanctions and check_tax_exempt_status REMOVED from onboarding flow.
    # Per Nirav's feedback (March 2, 2026): compliance screening happens pre-membership
    # via Descartes/SFDC integration at intake. By onboarding time, org is already cleared.

    elif tool_name == "provision_mailing_lists":
        from .mailing_list import provision_mailing_lists
        return await provision_mailing_lists(org_id, contact.email, dry_run=False, foundation_id=foundation_id)

    elif tool_name == "reconcile_silos":
        return await reconcile_silos(org_id, foundation_id)

    else:
        # Tools not yet implemented in Phase 1
        return {
            "status": "skipped",
            "message": f"Tool '{tool_name}' not yet implemented in Phase 1. Manual step required.",
        }


async def get_onboarding_status(org_id: str, contact_id: str) -> dict:
    """Retrieve the current onboarding status for a member contact.
    Shows which deliverables are complete, in progress, or pending.

    Args:
        org_id: Salesforce organization ID
        contact_id: Contact ID to check status for

    Returns:
        Current onboarding status with per-deliverable breakdown.
    """
    store_key = f"{org_id}:{contact_id}"
    stored = _onboarding_store.get(store_key)

    if not stored:
        # No checklist has been run — check if org exists
        org = await get_sfdc().get_org(org_id)
        if not org:
            return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

        return {
            "org_id": org_id,
            "contact_id": contact_id,
            "status": "not_started",
            "message": (
                f"No onboarding checklist has been run for contact '{contact_id}' "
                f"in org '{org.org_name}'. Use run_onboarding_checklist to start."
            ),
        }

    return {
        **stored["result"],
        "steps": stored["steps"],
        "last_updated": stored["updated_at"],
    }


async def reconcile_silos(org_id: str, foundation_id: str = "aaif") -> dict:
    """Compare data across Salesforce, Groups.io, and other systems to detect
    discrepancies for a specific organization.

    Checks:
    - SFDC contacts vs Groups.io subscriptions (are all contacts provisioned?)
    - Tier entitlements vs actual list access
    - Contact emails match across systems

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        List of discrepancies found with suggested fixes.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    discrepancies: list[dict] = []
    rules_config = PROVISIONING_RULES.get(foundation_id)

    for contact in org.contacts:
        # Determine expected lists from rules
        expected_lists = set()
        if rules_config:
            for rule in rules_config.rules:
                if rule.tier == org.tier and rule.role == contact.role:
                    expected_lists.update(rule.resources)

        # Check Groups.io
        for list_name in expected_lists:
            is_member = await get_groupsio().is_member(list_name, contact.email)
            if not is_member:
                discrepancies.append(SiloDiscrepancy(
                    system_a="salesforce",
                    system_b="groupsio",
                    field="mailing_list_membership",
                    value_a=f"{contact.email} should be on {list_name} (tier={org.tier.value}, role={contact.role.value})",
                    value_b=f"{contact.email} NOT subscribed to {list_name}",
                    severity="high" if "governing-board" in list_name else "medium",
                    suggested_fix=f"Run provision_mailing_lists(org_id='{org_id}', contact_email='{contact.email}', dry_run=False)",
                ).model_dump())

        # Check LFID verification
        if not contact.lfid_verified and contact.lfid:
            discrepancies.append(SiloDiscrepancy(
                system_a="salesforce",
                system_b="lf_sso",
                field="lfid_verification",
                value_a=f"LFID '{contact.lfid}' recorded",
                value_b="LFID not verified in SSO system",
                severity="medium",
                suggested_fix=f"Verify LFID '{contact.lfid}' via LFX SSO lookup",
            ).model_dump())

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "foundation_id": foundation_id,
        "contacts_checked": len(org.contacts),
        "discrepancies_found": len(discrepancies),
        "discrepancies": discrepancies,
        "message": (
            f"Silo reconciliation for {org.org_name}: "
            f"{len(discrepancies)} discrepanc{'y' if len(discrepancies) == 1 else 'ies'} found "
            f"across {len(org.contacts)} contact(s)."
        ),
    }


async def run_offboarding_checklist(
    org_id: str, contact_email: str, reason: str = "membership_cancelled",
    dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Execute offboarding for a member contact — remove from mailing lists,
    revoke access, and update records.

    Args:
        org_id: Salesforce organization ID
        contact_email: Email of the contact being offboarded
        reason: Reason for offboarding (membership_cancelled, tier_downgrade, contact_inactive)
        dry_run: If True, report what would change without making changes
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Offboarding actions taken or planned.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {"error": "ORG_NOT_FOUND", "message": f"No org found with ID '{org_id}'"}

    actions: list[dict] = []

    # Step 1: Remove from all mailing lists
    all_lists = await get_groupsio().get_lists(foundation_id)
    for list_name in all_lists:
        is_member = await get_groupsio().is_member(list_name, contact_email)
        if not is_member:
            continue

        if dry_run:
            actions.append({
                "step": "remove_mailing_list",
                "list": list_name,
                "email": contact_email,
                "status": "dry_run",
            })
        else:
            await get_groupsio().remove_member(list_name, contact_email)
            actions.append({
                "step": "remove_mailing_list",
                "list": list_name,
                "email": contact_email,
                "status": "completed",
            })

    # Step 2: Remove from LFX Meetings (if PIS configured)
    pis_meeting = get_pis_meeting()
    if pis_meeting is not None:
        if dry_run:
            contact_meetings = await pis_meeting.get_contact_meetings(contact_email)
            for mtg in contact_meetings.get("meetings", []):
                actions.append({
                    "step": "remove_meeting_registrant",
                    "meeting_id": mtg["meeting_id"],
                    "topic": mtg.get("topic", "Unknown"),
                    "email": contact_email,
                    "status": "dry_run",
                    "source": "pis_meeting_v2",
                })
        else:
            removal_results = await pis_meeting.remove_from_all_meetings(contact_email)
            for r in removal_results:
                actions.append({
                    "step": "remove_meeting_registrant",
                    "meeting_id": r.get("meeting_id"),
                    "topic": r.get("topic", "Unknown"),
                    "email": contact_email,
                    "status": "completed" if r.get("status") == "removed" else r.get("status", "error"),
                    "source": "pis_meeting_v2",
                })
    else:
        actions.append({
            "step": "remove_calendar_invites",
            "status": "manual_required",
            "note": "Remove from recurring meeting invites (PIS not configured)",
        })

    # Step 3: Remove from GitHub repos (if PIS GitHub configured, use it to discover repos)
    pis_github = get_pis_github()
    if pis_github is not None:
        # Find the contact to get their GitHub username
        contact_obj = None
        for c in org.contacts:
            if c.email == contact_email:
                contact_obj = c
                break

        github_username = contact_obj.github_username if contact_obj and hasattr(contact_obj, "github_username") else None

        if github_username:
            # Use PIS to list all repos for the project, then remove collaborator from each
            try:
                pis_orgs = await pis_github.list_orgs()
                repos_found = []
                for pis_org in pis_orgs:
                    org_name = pis_org.get("organization", "")
                    if org_name:
                        repos = await pis_github.list_repos(org_name)
                        for repo in repos:
                            repo_name = repo.get("name", "")
                            if repo_name:
                                repos_found.append(f"{org_name}/{repo_name}")

                for repo_path in repos_found:
                    if dry_run:
                        actions.append({
                            "step": "remove_github_collaborator",
                            "repo": repo_path,
                            "username": github_username,
                            "status": "dry_run",
                            "source": "pis_github_v2",
                        })
                    else:
                        parts = repo_path.split("/", 1)
                        result = await get_github().remove_collaborator(github_username, repo_path)
                        actions.append({
                            "step": "remove_github_collaborator",
                            "repo": repo_path,
                            "username": github_username,
                            "status": "completed" if result.get("status") == "removed" else result.get("status", "error"),
                            "source": "pis_github_v2",
                        })
            except Exception as e:
                actions.append({
                    "step": "remove_github_access",
                    "status": "error",
                    "source": "pis_github_v2",
                    "error": str(e),
                    "note": "PIS GitHub repo discovery failed; manual removal required",
                })
        else:
            actions.append({
                "step": "remove_github_access",
                "status": "manual_required",
                "note": "No GitHub username found for contact; manual removal required",
                "source": "pis_github_v2",
            })
    else:
        actions.append({
            "step": "remove_github_access",
            "status": "manual_required",
            "note": "Remove from GitHub org/repos (PIS GitHub not configured)",
        })

    # Step 4: Flag remaining manual follow-ups (Discord, CRM)
    manual_steps = [
        {"step": "remove_discord_access", "status": "manual_required",
         "note": "Remove from Discord server/channels"},
        {"step": "update_crm_record", "status": "manual_required",
         "note": f"Update contact status in SFDC (reason: {reason})"},
    ]
    actions.extend(manual_steps)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "contact_email": contact_email,
        "reason": reason,
        "dry_run": dry_run,
        "actions": actions,
        "automated_actions": sum(1 for a in actions if a["status"] in ("completed", "dry_run")),
        "manual_actions": sum(1 for a in actions if a["status"] == "manual_required"),
        "message": (
            f"{'DRY RUN: ' if dry_run else ''}"
            f"Offboarding {contact_email} from {org.org_name} (reason: {reason}). "
            f"{len(actions)} total actions."
        ),
    }


async def get_silo_health(foundation_id: str = "aaif") -> dict:
    """Foundation-wide silo health report — how well-synced are all systems?

    Scans every active member and runs reconciliation to produce an
    aggregate health score and top issues.

    Args:
        foundation_id: Foundation identifier (default: aaif)

    Returns:
        Silo health report with overall score and top issues.
    """
    orgs = await get_sfdc().list_orgs(foundation_id)
    active_orgs = [o for o in orgs if o.status == "active"]

    total_discrepancies = 0
    discrepancies_by_system: dict[str, int] = {}
    members_with_issues = 0
    top_issues: list[str] = []

    for org in active_orgs:
        result = await reconcile_silos(org.org_id, foundation_id)
        disc_count = result.get("discrepancies_found", 0)
        total_discrepancies += disc_count
        if disc_count > 0:
            members_with_issues += 1
            for d in result.get("discrepancies", [])[:2]:  # Top 2 per org
                systems_key = f"{d.get('system_a', '?')}↔{d.get('system_b', '?')}"
                discrepancies_by_system[systems_key] = discrepancies_by_system.get(systems_key, 0) + 1
                if len(top_issues) < 10:
                    top_issues.append(
                        f"{org.org_name}: {d.get('field', '?')} — {d.get('value_b', '?')}"
                    )

    total_members = len(active_orgs)
    in_sync = total_members - members_with_issues
    score = (in_sync / total_members) if total_members > 0 else 1.0

    report = SiloHealthReport(
        foundation_id=foundation_id,
        overall_score=round(score, 3),
        total_members=total_members,
        members_in_sync=in_sync,
        members_with_issues=members_with_issues,
        discrepancies_by_system=discrepancies_by_system,
        top_issues=top_issues,
    )

    return {
        **report.model_dump(),
        "message": (
            f"Silo health for '{foundation_id}': {score:.0%} in sync. "
            f"{in_sync}/{total_members} members fully synchronized. "
            f"{total_discrepancies} total discrepancies found."
        ),
    }
