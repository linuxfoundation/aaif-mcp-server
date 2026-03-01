"""Pydantic models for the AAIF MCP Server.

These models define the structured data types used across all tools,
resources, and connectors. They map directly to the PRD's schema definitions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────

class Tier(str, Enum):
    platinum = "platinum"
    gold = "gold"
    silver = "silver"


class ContactRole(str, Enum):
    voting_contact = "voting_contact"
    alternate_contact = "alternate_contact"
    technical_contact = "technical_contact"
    billing_contact = "billing_contact"
    marketing_contact = "marketing_contact"
    primary_contact = "primary_contact"


class DeliverableId(str, Enum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"
    D5 = "D5"


class StepStatus(str, Enum):
    complete = "complete"
    in_progress = "in_progress"
    pending = "pending"
    blocked = "blocked"
    failed = "failed"
    skipped = "skipped"


class WgAccessPolicy(str, Enum):
    role_restricted = "role_restricted"
    any_member = "any_member"
    public = "public"


class OffboardingReason(str, Enum):
    membership_cancelled = "membership_cancelled"
    tier_downgrade = "tier_downgrade"
    contact_inactive = "contact_inactive"


# ── Core Models ────────────────────────────────────────────────────

class Contact(BaseModel):
    contact_id: str
    name: str
    email: str
    role: ContactRole
    lfid: Optional[str] = None
    lfid_verified: bool = False
    github_username: Optional[str] = None
    discord_handle: Optional[str] = None


class MemberOrg(BaseModel):
    org_id: str
    org_name: str
    tier: Tier
    foundation_id: str = "aaif"
    status: str = "active"  # active, pending, cancelled, suspended
    contract_signed: Optional[datetime] = None
    contract_expiry: Optional[datetime] = None
    headcount_tier: Optional[str] = None  # For Silver pricing: "1-99", "100-499", etc.
    is_lf_member: bool = False
    country: str = "US"
    contacts: list[Contact] = Field(default_factory=list)


class WorkingGroup(BaseModel):
    wg_id: str
    name: str
    slug: str
    meeting_schedule: str
    mailing_list: str
    discord_channel: str
    github_repo: str
    access_policy: WgAccessPolicy = WgAccessPolicy.any_member
    chairs: list[str] = Field(default_factory=list)  # contact_ids


# ── Onboarding Status ─────────────────────────────────────────────

class OnboardingStep(BaseModel):
    id: str
    deliverable: DeliverableId
    description: str
    status: StepStatus = StepStatus.pending
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    blocked_by: Optional[str] = None


class DeliverableStatus(BaseModel):
    id: DeliverableId
    name: str
    status: StepStatus = StepStatus.pending
    steps: list[OnboardingStep] = Field(default_factory=list)
    completion_pct: float = 0.0


class OnboardingStatus(BaseModel):
    org_id: str
    contact_id: str
    overall: StepStatus = StepStatus.pending
    current_deliverable: Optional[DeliverableId] = None
    deliverables: dict[str, StepStatus] = Field(default_factory=dict)
    checklist_completion: float = 0.0
    steps: list[OnboardingStep] = Field(default_factory=list)


# ── Tier & Entitlements ────────────────────────────────────────────

class TierEntitlements(BaseModel):
    tier: Tier
    foundation_id: str
    gb_seats: int = 0
    voting_rights: bool = False
    wg_chair_eligible: bool = False
    wg_participation: bool = True
    tc_eligible: bool = False
    event_member_pricing: bool = True
    max_contacts: int = 5
    mailing_lists: list[str] = Field(default_factory=list)
    pricing: Optional[str] = None


class TierValidationResult(BaseModel):
    org_id: str
    org_name: str
    tier: Tier
    foundation_id: str
    status: str
    contract_expiry: Optional[datetime] = None
    entitlements: TierEntitlements
    anomalies: list[str] = Field(default_factory=list)


class TierAnomaly(BaseModel):
    org_id: str
    org_name: str
    tier: Tier
    anomaly_type: str
    description: str
    severity: str  # high, medium, low


# ── Sanctions & Compliance ─────────────────────────────────────────

class SanctionsResult(BaseModel):
    org_name: str
    country: str
    status: str  # "clear", "flagged", "blocked"
    requires_human_review: bool = False
    matches: list[dict] = Field(default_factory=list)
    checked_lists: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = ""


class ComplianceReport(BaseModel):
    org_id: str
    org_name: str
    sanctions_status: str
    tax_exempt_status: str
    open_issues: list[dict] = Field(default_factory=list)
    last_screened: Optional[datetime] = None


# ── Mailing List ───────────────────────────────────────────────────

class MailingListAction(BaseModel):
    list_name: str
    email: str
    action: str  # "add", "remove", "skip_duplicate", "skip_not_found"
    status: str  # "success", "dry_run", "error", "skipped"
    reason: Optional[str] = None


class MailingListMembership(BaseModel):
    email: str
    lists: dict[str, bool] = Field(default_factory=dict)  # list_name → is_member


class MailingListGap(BaseModel):
    org_id: str
    org_name: str
    contact_email: str
    expected_lists: list[str]
    actual_lists: list[str]
    missing: list[str]
    extra: list[str]


# ── Orchestrator ───────────────────────────────────────────────────

class ChecklistResult(BaseModel):
    org_id: str
    contact_id: str
    foundation_id: str
    dry_run: bool
    overall_status: StepStatus
    deliverables: list[DeliverableStatus] = Field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    errors: list[str] = Field(default_factory=list)


class SiloDiscrepancy(BaseModel):
    system_a: str
    system_b: str
    field: str
    value_a: str
    value_b: str
    severity: str
    suggested_fix: str


class SiloHealthReport(BaseModel):
    foundation_id: str
    overall_score: float  # 0.0 - 1.0
    total_members: int
    members_in_sync: int
    members_with_issues: int
    discrepancies_by_system: dict[str, int] = Field(default_factory=dict)
    top_issues: list[str] = Field(default_factory=list)


# ── Checklist Template ─────────────────────────────────────────────

class ChecklistItem(BaseModel):
    id: str
    deliverable: DeliverableId
    text: str
    effort: str
    automated: bool = False
    tool: Optional[str] = None


class ChecklistTemplate(BaseModel):
    foundation_id: str
    deliverables: list[dict] = Field(default_factory=list)


# ── Rules ──────────────────────────────────────────────────────────

class ProvisioningRule(BaseModel):
    tier: Tier
    role: ContactRole
    resources: list[str]  # list names, channels, repos to provision


class RulesConfig(BaseModel):
    foundation_id: str
    rules: list[ProvisioningRule] = Field(default_factory=list)
