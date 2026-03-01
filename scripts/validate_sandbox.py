#!/usr/bin/env python3
"""AAIF MCP Server — Sandbox Validation Script

Runs a systematic check of every connector and tool against the sandbox.
Designed for the 3-4 day validation sprint.

Usage:
    # From the repo root, with .env loaded or env vars set:
    python scripts/validate_sandbox.py

    # Run specific phases:
    python scripts/validate_sandbox.py --phase 1     # Connector health only
    python scripts/validate_sandbox.py --phase 2     # All 16 tools
    python scripts/validate_sandbox.py --phase 3     # End-to-end onboarding flow
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("validate")

# ── Result tracking ─────────────────────────────────────────────


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration_ms: float
    detail: str = ""
    error: str = ""


@dataclass
class ValidationReport:
    phase: str
    results: list[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult):
        self.results.append(result)
        icon = "✅" if result.passed else "❌"
        ms = f"{result.duration_ms:.0f}ms"
        logger.info(f"  {icon} {result.name} ({ms}) {result.detail}")
        if result.error:
            logger.error(f"     ↳ {result.error}")

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    def summary(self):
        total = len(self.results)
        logger.info("")
        logger.info(f"{'═' * 60}")
        logger.info(f"  {self.phase}: {self.passed}/{total} passed, {self.failed} failed")
        logger.info(f"{'═' * 60}")
        if self.failed > 0:
            logger.info("  Failed checks:")
            for r in self.results:
                if not r.passed:
                    logger.info(f"    ❌ {r.name}: {r.error}")
        logger.info("")


async def timed(name: str, coro):
    """Run a coroutine and return a CheckResult."""
    t0 = time.monotonic()
    try:
        result = await coro
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(name=name, passed=True, duration_ms=ms, detail=_summarize(result))
    except Exception as e:
        ms = (time.monotonic() - t0) * 1000
        return CheckResult(name=name, passed=False, duration_ms=ms, error=str(e)[:200])


def _summarize(result) -> str:
    """Create a short summary of a tool result."""
    if isinstance(result, dict):
        keys = list(result.keys())[:4]
        return f"keys={keys}"
    if isinstance(result, list):
        return f"items={len(result)}"
    if isinstance(result, str) and len(result) > 80:
        return result[:80] + "..."
    return str(result)[:80]


# ═══════════════════════════════════════════════════════════════════
# PHASE 1: Connector Health Checks
# ═══════════════════════════════════════════════════════════════════

async def phase1_connector_health():
    """Verify raw connectivity to SFDC, Groups.io, and OFAC."""
    report = ValidationReport(phase="Phase 1: Connector Health")

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  Phase 1: Connector Health Checks                       ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")

    # ── Check env vars ──────────────────────────────────────────
    sfdc_vars = ["SFDC_INSTANCE_URL", "SFDC_CLIENT_ID", "SFDC_CLIENT_SECRET", "SFDC_USERNAME"]
    gio_vars = ["GROUPSIO_API_TOKEN"]

    logger.info("  Checking environment variables...")
    for var in sfdc_vars:
        val = os.environ.get(var, "")
        if val:
            report.add(CheckResult(name=f"env:{var}", passed=True, duration_ms=0, detail=f"set ({len(val)} chars)"))
        else:
            report.add(CheckResult(name=f"env:{var}", passed=False, duration_ms=0, error="NOT SET — required for live SFDC"))

    for var in gio_vars:
        val = os.environ.get(var, "")
        if val:
            report.add(CheckResult(name=f"env:{var}", passed=True, duration_ms=0, detail=f"set ({len(val)} chars)"))
        else:
            report.add(CheckResult(name=f"env:{var}", passed=False, duration_ms=0, error="NOT SET — required for live Groups.io"))

    logger.info("")

    # ── SFDC OAuth test ─────────────────────────────────────────
    logger.info("  Testing Salesforce OAuth...")
    try:
        import httpx

        instance_url = os.environ.get("SFDC_INSTANCE_URL", "")
        if instance_url:
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{instance_url}/services/oauth2/token",
                    data={
                        "grant_type": "password",
                        "client_id": os.environ.get("SFDC_CLIENT_ID", ""),
                        "client_secret": os.environ.get("SFDC_CLIENT_SECRET", ""),
                        "username": os.environ.get("SFDC_USERNAME", ""),
                        "password": os.environ.get("SFDC_PASSWORD", ""),
                    },
                )
                ms = (time.monotonic() - t0) * 1000
                if resp.status_code == 200:
                    token_data = resp.json()
                    report.add(CheckResult(
                        name="sfdc:oauth",
                        passed=True,
                        duration_ms=ms,
                        detail=f"token obtained, instance={token_data.get('instance_url', 'unknown')}",
                    ))
                    # Quick SOQL test
                    t0 = time.monotonic()
                    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                    q = await client.get(
                        f"{token_data['instance_url']}/services/data/v59.0/query",
                        params={"q": "SELECT COUNT() FROM Account"},
                        headers=headers,
                    )
                    ms2 = (time.monotonic() - t0) * 1000
                    if q.status_code == 200:
                        count = q.json().get("totalSize", "?")
                        report.add(CheckResult(name="sfdc:soql", passed=True, duration_ms=ms2, detail=f"Account count={count}"))
                    else:
                        report.add(CheckResult(name="sfdc:soql", passed=False, duration_ms=ms2, error=f"HTTP {q.status_code}: {q.text[:100]}"))
                else:
                    report.add(CheckResult(name="sfdc:oauth", passed=False, duration_ms=ms, error=f"HTTP {resp.status_code}: {resp.text[:150]}"))
        else:
            report.add(CheckResult(name="sfdc:oauth", passed=False, duration_ms=0, error="SFDC_INSTANCE_URL not set"))
    except Exception as e:
        report.add(CheckResult(name="sfdc:oauth", passed=False, duration_ms=0, error=str(e)[:200]))

    logger.info("")

    # ── Groups.io API test ──────────────────────────────────────
    logger.info("  Testing Groups.io API...")
    try:
        token = os.environ.get("GROUPSIO_API_TOKEN", "")
        if token:
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://groups.io/api/v1/getgroups",
                    headers={"Authorization": f"Bearer {token}"},
                )
                ms = (time.monotonic() - t0) * 1000
                if resp.status_code == 200:
                    data = resp.json()
                    group_count = len(data.get("data", []))
                    report.add(CheckResult(name="groupsio:getgroups", passed=True, duration_ms=ms, detail=f"groups={group_count}"))
                else:
                    report.add(CheckResult(name="groupsio:getgroups", passed=False, duration_ms=ms, error=f"HTTP {resp.status_code}: {resp.text[:150]}"))
        else:
            report.add(CheckResult(name="groupsio:getgroups", passed=False, duration_ms=0, error="GROUPSIO_API_TOKEN not set"))
    except Exception as e:
        report.add(CheckResult(name="groupsio:getgroups", passed=False, duration_ms=0, error=str(e)[:200]))

    logger.info("")

    # NOTE: OFAC/sanctions screening handled by Descartes integration in SFDC.
    # No separate OFAC download needed.

    report.summary()
    return report


# ═══════════════════════════════════════════════════════════════════
# PHASE 2: Smoke Test All 16 Tools
# ═══════════════════════════════════════════════════════════════════

async def phase2_tool_smoke_tests():
    """Call every tool with sandbox-safe parameters."""
    report = ValidationReport(phase="Phase 2: Tool Smoke Tests (16 tools)")

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  Phase 2: Smoke Test All 16 Tools                       ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")

    # Import all tool functions
    from aaif_mcp_server.tools.tier_validation import (
        validate_membership_tier,
        check_tier_entitlements,
        detect_tier_anomalies,
    )
    from aaif_mcp_server.tools.compliance import (
        check_sanctions,
        check_tax_exempt_status,
        get_compliance_report,
        flag_compliance_issue,
    )
    from aaif_mcp_server.tools.mailing_list import (
        provision_mailing_lists,
        remove_from_mailing_lists,
        check_mailing_list_membership,
        remediate_mailing_lists,
    )
    from aaif_mcp_server.tools.orchestrator import (
        run_onboarding_checklist,
        get_onboarding_status,
        reconcile_silos,
        run_offboarding_checklist,
        get_silo_health,
    )
    from aaif_mcp_server.resources.member import get_member_profile, list_members
    from aaif_mcp_server.resources.rules import (
        get_provisioning_rules,
        get_tier_entitlements as get_tier_ent_resource,
        get_working_groups,
    )

    # ── Domain 4: Tier Validation (3 tools) ─────────────────────
    logger.info("  Domain 4: Tier Validation")
    # Use a known sandbox org_id — try the first one from list_members
    try:
        members = await list_members("aaif")
        if members and len(members) > 0:
            sample_org_id = members[0].get("org_id", "0017V00001HITACHI")
            sample_org_name = members[0].get("org_name", "Hitachi")
            sample_country = members[0].get("country", "JP")
            logger.info(f"  Using sample org: {sample_org_name} ({sample_org_id})")
        else:
            sample_org_id = "0017V00001HITACHI"
            sample_org_name = "Hitachi"
            sample_country = "JP"
    except Exception:
        sample_org_id = "0017V00001HITACHI"
        sample_org_name = "Hitachi"
        sample_country = "JP"

    report.add(await timed("validate_membership_tier", validate_membership_tier(sample_org_id)))
    report.add(await timed("check_tier_entitlements", check_tier_entitlements("platinum")))
    report.add(await timed("detect_tier_anomalies", detect_tier_anomalies()))

    logger.info("")

    # ── Domain 3: Compliance (4 tools) ──────────────────────────
    # NOTE: check_sanctions reads from SFDC/Descartes, not a separate OFAC screener
    logger.info("  Domain 3: Compliance")
    report.add(await timed("check_sanctions", check_sanctions(sample_org_name, sample_country, sample_org_id)))
    report.add(await timed("check_tax_exempt_status", check_tax_exempt_status(sample_org_id)))
    report.add(await timed("get_compliance_report", get_compliance_report(sample_org_id)))
    report.add(await timed("flag_compliance_issue", flag_compliance_issue(sample_org_id, "other", "Sandbox validation test — ignore")))

    logger.info("")

    # ── Domain 1: Mailing Lists (4 tools) ───────────────────────
    logger.info("  Domain 1: Mailing Lists")
    # Use dry_run=True for safety
    report.add(await timed("provision_mailing_lists (dry)", provision_mailing_lists(sample_org_id, "test@example.com", dry_run=True)))
    report.add(await timed("remove_from_mailing_lists (dry)", remove_from_mailing_lists(sample_org_id, "test@example.com", dry_run=True)))
    report.add(await timed("check_mailing_list_membership", check_mailing_list_membership("test@example.com")))
    report.add(await timed("remediate_mailing_lists (dry)", remediate_mailing_lists(dry_run=True)))

    logger.info("")

    # ── Domain 12: Orchestration (5 tools) ──────────────────────
    logger.info("  Domain 12: Orchestration")
    report.add(await timed("run_onboarding_checklist (dry)", run_onboarding_checklist(sample_org_id, "CONTACT001", dry_run=True)))
    report.add(await timed("get_onboarding_status", get_onboarding_status(sample_org_id, "CONTACT001")))
    report.add(await timed("reconcile_silos", reconcile_silos(sample_org_id)))
    report.add(await timed("run_offboarding_checklist (dry)", run_offboarding_checklist(sample_org_id, "test@example.com", dry_run=True)))
    report.add(await timed("get_silo_health", get_silo_health()))

    logger.info("")

    # ── Resources (5 functions) ─────────────────────────────────
    logger.info("  Resources")
    report.add(await timed("get_member_profile", get_member_profile(sample_org_id)))
    report.add(await timed("list_members", list_members("aaif")))
    report.add(await timed("get_provisioning_rules", get_provisioning_rules()))
    report.add(await timed("get_tier_entitlements_resource", get_tier_ent_resource()))
    report.add(await timed("get_working_groups", get_working_groups()))

    report.summary()
    return report


# ═══════════════════════════════════════════════════════════════════
# PHASE 3: End-to-End Onboarding Flow
# ═══════════════════════════════════════════════════════════════════

async def phase3_e2e_flow():
    """Run a complete onboarding + reconciliation for a sandbox org."""
    report = ValidationReport(phase="Phase 3: End-to-End Onboarding Flow")

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  Phase 3: End-to-End Onboarding Validation              ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")

    from aaif_mcp_server.tools.tier_validation import validate_membership_tier
    from aaif_mcp_server.tools.compliance import check_sanctions, get_compliance_report
    from aaif_mcp_server.tools.mailing_list import provision_mailing_lists, check_mailing_list_membership
    from aaif_mcp_server.tools.orchestrator import run_onboarding_checklist, reconcile_silos, get_silo_health
    from aaif_mcp_server.resources.member import list_members

    # Step 1: List all members
    logger.info("  Step 1: List all AAIF members")
    report.add(await timed("list_all_members", list_members("aaif")))

    # Step 2: Pick first member, validate their tier
    logger.info("  Step 2: Validate member tier")
    try:
        result = await list_members("aaif")
        member_list = result.get("members", []) if isinstance(result, dict) else result
        if member_list and len(member_list) > 0:
            org = member_list[0]
            org_id = org.get("org_id", "unknown")
            org_name = org.get("org_name", "Unknown")
            tier = org.get("tier", "unknown")
            logger.info(f"    → Testing with: {org_name} ({tier})")
            report.add(await timed(f"validate_tier:{org_name}", validate_membership_tier(org_id)))
        else:
            report.add(CheckResult(name="validate_tier", passed=False, duration_ms=0, error="No members returned"))
            return report
    except Exception as e:
        report.add(CheckResult(name="validate_tier", passed=False, duration_ms=0, error=str(e)[:200]))
        return report

    # Step 3: Compliance check
    logger.info("  Step 3: Compliance screening")
    country = org.get("country", "JP")
    report.add(await timed(f"compliance:{org_name}", get_compliance_report(org_id)))
    report.add(await timed(f"sanctions:{org_name}", check_sanctions(org_name, country)))

    # Step 4: Onboarding checklist (dry run)
    logger.info("  Step 4: Onboarding checklist (dry run)")
    report.add(await timed(f"onboard:{org_name}", run_onboarding_checklist(org_id, "SANDBOX_CONTACT", dry_run=True)))

    # Step 5: Silo reconciliation
    logger.info("  Step 5: Silo reconciliation")
    report.add(await timed(f"reconcile:{org_name}", reconcile_silos(org_id)))

    # Step 6: Foundation-wide health
    logger.info("  Step 6: Silo health check")
    report.add(await timed("silo_health", get_silo_health()))

    report.summary()
    return report


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="AAIF MCP Server Sandbox Validator")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], default=0,
                        help="Run specific phase (1=connectors, 2=tools, 3=e2e). Default: all")
    args = parser.parse_args()

    # Check if we're in mock mode
    sfdc_url = os.environ.get("SFDC_INSTANCE_URL", "")
    gio_token = os.environ.get("GROUPSIO_API_TOKEN", "")
    if not sfdc_url and not gio_token:
        logger.warning("⚠️  No credentials detected — running against MOCK DATA")
        logger.warning("   Set SFDC_INSTANCE_URL + GROUPSIO_API_TOKEN for live validation")
        logger.warning("")
    elif sfdc_url and gio_token:
        logger.info("🔗 Live mode: SFDC + Groups.io credentials detected")
        logger.info("")
    else:
        if sfdc_url:
            logger.info("🔗 SFDC live, Groups.io mock")
        else:
            logger.info("🔗 SFDC mock, Groups.io live")
        logger.info("")

    reports = []

    if args.phase == 0 or args.phase == 1:
        reports.append(await phase1_connector_health())

    if args.phase == 0 or args.phase == 2:
        reports.append(await phase2_tool_smoke_tests())

    if args.phase == 0 or args.phase == 3:
        reports.append(await phase3_e2e_flow())

    # ── Final Summary ───────────────────────────────────────────
    total_pass = sum(r.passed for r in reports)
    total_fail = sum(r.failed for r in reports)
    total = total_pass + total_fail

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  FINAL VALIDATION SUMMARY                               ║")
    logger.info("╠══════════════════════════════════════════════════════════╣")
    for r in reports:
        status = "✅ ALL PASS" if r.failed == 0 else f"❌ {r.failed} FAILED"
        logger.info(f"║  {r.phase:40s} {status:>15s} ║")
    logger.info("╠══════════════════════════════════════════════════════════╣")
    status = "✅ SANDBOX VALIDATED" if total_fail == 0 else f"❌ {total_fail}/{total} CHECKS FAILED"
    logger.info(f"║  {'OVERALL':40s} {status:>15s} ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
