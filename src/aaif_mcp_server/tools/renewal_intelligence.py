"""Domain 11: Renewal & Engagement Intelligence — 5 tools.

Tracks contract renewal status, engagement scoring, churn risk prediction,
and renewal outreach planning.
"""

import logging
from datetime import datetime, timedelta

from ..config import MOCK_MEMBERS, MOCK_ENGAGEMENT_DATA
from ..connectors.registry import get_sfdc

logger = logging.getLogger(__name__)


def _calculate_days_to_renewal(expiry_date: datetime) -> int:
    """Calculate days until contract expiry."""
    delta = expiry_date - datetime.utcnow()
    return max(0, delta.days)


def _get_renewal_stage(days_remaining: int) -> str:
    """Determine renewal stage based on days remaining."""
    if days_remaining > 90:
        return "active"
    elif days_remaining > 60:
        return "watch_90"
    elif days_remaining > 30:
        return "watch_60"
    elif days_remaining > 0:
        return "watch_30"
    else:
        return "expired"


async def get_renewal_status(org_id: str, foundation_id: str = "aaif") -> dict:
    """Get contract renewal status for a member organization.

    Returns renewal stage: active (90+ days), watch_90, watch_60, watch_30, expired.

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Renewal status with contract dates, days remaining, and stage.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {
            "error": "ORG_NOT_FOUND",
            "message": f"No org found with ID '{org_id}'",
        }

    days_remaining = _calculate_days_to_renewal(org.contract_expiry)
    renewal_stage = _get_renewal_stage(days_remaining)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "contract_signed": org.contract_signed.isoformat() if org.contract_signed else None,
        "contract_expiry": org.contract_expiry.isoformat(),
        "days_remaining": days_remaining,
        "renewal_stage": renewal_stage,
        "renewal_status": (
            "active" if renewal_stage == "active"
            else "at_risk" if renewal_stage in ["watch_30", "watch_60"]
            else "critical" if renewal_stage == "watch_90"
            else "expired"
        ),
        "message": (
            f"Renewal in {days_remaining} days ({renewal_stage}): "
            f"{org.org_name} contract expires {org.contract_expiry.strftime('%Y-%m-%d')}"
        ),
    }


async def get_engagement_score(org_id: str, foundation_id: str = "aaif") -> dict:
    """Calculate engagement score (0-100) for a member organization.

    Breakdown:
    - Meeting attendance: 0-25 points
    - WG participation: 0-25 points
    - GitHub commits (30d): 0-25 points
    - Slack activity (30d): 0-25 points

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Engagement score with component breakdown.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {
            "error": "ORG_NOT_FOUND",
            "message": f"No org found with ID '{org_id}'",
        }

    engagement = MOCK_ENGAGEMENT_DATA.get(org_id, {})

    # Calculate component scores
    attendance_score = int(engagement.get("meeting_attendance_rate", 0) * 25)

    wg_count = engagement.get("wg_participation_count", 0)
    wg_score = min(25, wg_count * 12)  # 2 WGs = 25 points

    github_commits = engagement.get("github_commits_30d", 0)
    github_score = min(25, max(0, (github_commits - 1) / 2))  # Scale: 1-50+ commits

    slack_messages = engagement.get("slack_messages_30d", 0)
    slack_score = min(25, max(0, (slack_messages - 1) / 5))  # Scale: 1-120+ messages

    total_score = int(attendance_score + wg_score + github_score + slack_score)

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "total_score": total_score,
        "components": {
            "meeting_attendance": {
                "rate": engagement.get("meeting_attendance_rate", 0),
                "score": attendance_score,
                "max": 25,
            },
            "wg_participation": {
                "count": wg_count,
                "score": int(wg_score),
                "max": 25,
            },
            "github_commits_30d": {
                "commits": github_commits,
                "score": int(github_score),
                "max": 25,
            },
            "slack_messages_30d": {
                "messages": slack_messages,
                "score": int(slack_score),
                "max": 25,
            },
        },
        "last_activity": engagement.get("last_activity"),
        "engagement_level": (
            "high" if total_score >= 75
            else "medium" if total_score >= 50
            else "low"
        ),
        "message": f"Engagement score: {total_score}/100 ({['low', 'medium', 'high'][(total_score >= 50) + (total_score >= 75)]} engagement)",
    }


async def predict_churn_risk(org_id: str, foundation_id: str = "aaif") -> dict:
    """Predict churn risk (0-100) based on engagement and renewal timeline.

    Risk factors:
    - Days to renewal (30 days or less = high risk)
    - Engagement score (low score = high risk)
    - Recent activity (>30 days inactive = risk)

    Args:
        org_id: Salesforce organization ID
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Churn risk score with component analysis.
    """
    renewal = await get_renewal_status(org_id, foundation_id)
    if "error" in renewal:
        return renewal

    engagement = await get_engagement_score(org_id, foundation_id)
    if "error" in engagement:
        return engagement

    org = await get_sfdc().get_org(org_id)

    # Calculate risk components
    days_remaining = renewal["days_remaining"]
    renewal_risk = (
        100 if days_remaining <= 0
        else 75 if days_remaining <= 30
        else 50 if days_remaining <= 60
        else 25 if days_remaining <= 90
        else 0
    )

    engagement_risk = 100 - engagement["total_score"]

    # Check recency
    last_activity = engagement.get("last_activity")
    days_since_activity = 0
    if last_activity:
        try:
            last_date = datetime.strptime(last_activity, "%Y-%m-%d")
            days_since_activity = (datetime.utcnow() - last_date).days
        except (ValueError, TypeError):
            days_since_activity = 0

    recency_risk = (
        75 if days_since_activity > 30
        else 50 if days_since_activity > 14
        else 25 if days_since_activity > 7
        else 0
    )

    # Weighted average
    total_risk = int((renewal_risk * 0.4) + (engagement_risk * 0.4) + (recency_risk * 0.2))

    return {
        "org_id": org_id,
        "org_name": org.org_name,
        "churn_risk_score": total_risk,
        "risk_level": (
            "critical" if total_risk >= 75
            else "high" if total_risk >= 50
            else "medium" if total_risk >= 25
            else "low"
        ),
        "risk_factors": {
            "renewal_timeline": {
                "days_remaining": days_remaining,
                "risk": renewal_risk,
                "weight": 0.4,
            },
            "engagement_gap": {
                "score": engagement["total_score"],
                "risk": engagement_risk,
                "weight": 0.4,
            },
            "activity_recency": {
                "days_since_activity": days_since_activity,
                "risk": recency_risk,
                "weight": 0.2,
            },
        },
        "message": f"Churn risk: {total_risk}/100 ({['low', 'medium', 'high', 'critical'][(total_risk >= 25) + (total_risk >= 50) + (total_risk >= 75)]})",
    }


async def get_renewal_dashboard(foundation_id: str = "aaif") -> dict:
    """Get foundation-wide renewal and engagement dashboard.

    Returns aggregate metrics: at-risk count, upcoming renewals, engagement distribution.

    Args:
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Dashboard with aggregate renewal and engagement metrics.
    """
    orgs = list(MOCK_MEMBERS.values())

    at_risk_count = 0
    upcoming_renewals = []
    engagement_scores = []
    churn_risks = []

    for org in orgs:
        if org.status != "active":
            continue

        days_remaining = _calculate_days_to_renewal(org.contract_expiry)
        renewal_stage = _get_renewal_stage(days_remaining)

        if renewal_stage in ["watch_30", "watch_60", "watch_90"]:
            at_risk_count += 1

        if days_remaining <= 90:
            upcoming_renewals.append({
                "org_id": org.org_id,
                "org_name": org.org_name,
                "tier": org.tier.value,
                "days_remaining": days_remaining,
                "expiry_date": org.contract_expiry.strftime("%Y-%m-%d"),
            })

        engagement = MOCK_ENGAGEMENT_DATA.get(org.org_id, {})
        score = int(
            (engagement.get("meeting_attendance_rate", 0) * 25) +
            min(25, engagement.get("wg_participation_count", 0) * 12) +
            min(25, max(0, (engagement.get("github_commits_30d", 0) - 1) / 2)) +
            min(25, max(0, (engagement.get("slack_messages_30d", 0) - 1) / 5))
        )
        engagement_scores.append(score)
        churn_risks.append(100 - score - (days_remaining / 365 * 20))

    avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
    avg_churn_risk = sum(churn_risks) / len(churn_risks) if churn_risks else 0

    return {
        "foundation_id": foundation_id,
        "active_members": len(orgs),
        "at_risk_members": at_risk_count,
        "upcoming_renewals": sorted(
            upcoming_renewals,
            key=lambda x: x["days_remaining"]
        ),
        "average_engagement_score": round(avg_engagement, 1),
        "average_churn_risk": round(avg_churn_risk, 1),
        "engagement_distribution": {
            "high": sum(1 for s in engagement_scores if s >= 75),
            "medium": sum(1 for s in engagement_scores if 50 <= s < 75),
            "low": sum(1 for s in engagement_scores if s < 50),
        },
        "message": (
            f"Foundation dashboard: {at_risk_count} at-risk, "
            f"{len(upcoming_renewals)} upcoming renewals, "
            f"avg engagement {round(avg_engagement, 1)}/100"
        ),
    }


async def trigger_renewal_outreach(
    org_id: str, dry_run: bool = True, foundation_id: str = "aaif"
) -> dict:
    """Generate renewal outreach plan with email template, talking points, and timeline.

    Args:
        org_id: Salesforce organization ID
        dry_run: If True, show what would happen without executing (default: True)
        foundation_id: Foundation ID (default: aaif)

    Returns:
        Outreach plan with email draft, talking points, and next steps.
    """
    org = await get_sfdc().get_org(org_id)
    if not org:
        return {
            "error": "ORG_NOT_FOUND",
            "message": f"No org found with ID '{org_id}'",
        }

    renewal = await get_renewal_status(org_id, foundation_id)
    if "error" in renewal:
        return renewal

    churn = await predict_churn_risk(org_id, foundation_id)

    days_remaining = renewal["days_remaining"]

    # Generate email draft
    email_draft = f"""Subject: {org.org_name} — AAIF Membership Renewal Opportunity

Dear {org.contacts[0].name if org.contacts else "Valued Partner"},

We hope you've found value in your {org.tier.value.title()}-level membership with the AI & Agentic Infrastructure Foundation. Your participation in our working groups and initiatives has been instrumental in advancing responsible AI development.

With your contract expiring in {days_remaining} days, we wanted to reach out to discuss renewal and explore how we can deepen our collaboration.

Key highlights of your engagement:
- Active in {len(MOCK_ENGAGEMENT_DATA.get(org_id, {}).get('wg_participation_count', 0))} working groups
- {MOCK_ENGAGEMENT_DATA.get(org_id, {}).get('github_commits_30d', 0)} GitHub contributions in the past month
- Strong meeting attendance and Slack participation

We'd love to schedule a brief call to discuss:
1. Your experience with AAIF to date
2. Priorities for the coming year
3. Any ways we can better support your team's objectives

Please let me know your availability for a 30-minute call in the next week.

Best regards,
The AAIF Membership Team
membership@aaif.io
"""

    talking_points = [
        f"Contract expires in {days_remaining} days — plan for continuity",
        "Recent engagement metrics show strong participation",
        "New working groups launching in 2026 — opportunity to expand involvement",
        "Member benefits: governance participation, exclusive events, training access",
        "Tiered options available based on organizational scale and objectives",
    ]

    next_steps = []
    if days_remaining > 60:
        next_steps.append("Send initial renewal inquiry email (this month)")
        next_steps.append("Schedule executive briefing call")
    elif days_remaining > 30:
        next_steps.append("Send renewal proposal with terms")
        next_steps.append("Prepare executive summary of engagement ROI")
    else:
        next_steps.append("Urgent: Contact executive sponsor immediately")
        next_steps.append("Offer 30-day extension if needed for approval process")

    result = {
        "org_id": org_id,
        "org_name": org.org_name,
        "tier": org.tier.value,
        "days_remaining": days_remaining,
        "churn_risk": churn.get("churn_risk_score", 0),
        "dry_run": dry_run,
        "email_draft": email_draft,
        "talking_points": talking_points,
        "next_steps": next_steps,
        "suggested_actions": [
            {"action": "Send email", "timing": "ASAP", "responsibility": "Membership team"},
            {"action": "Schedule call", "timing": "Within 5 days", "responsibility": "Account manager"},
            {"action": "Prepare renewal proposal", "timing": "By end of week", "responsibility": "Legal"},
        ],
        "message": (
            f"Renewal outreach plan generated for {org.org_name} "
            f"(churn risk: {churn.get('churn_risk_score', 0)}/100). "
            f"{'[DRY RUN - not executed]' if dry_run else '[EXECUTED]'}"
        ),
    }

    return result
