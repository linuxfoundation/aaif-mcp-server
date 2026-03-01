# AAIF Member Onboarding MCP Server

16 tools for automating Linux Foundation AAIF member onboarding — tier validation, compliance screening, mailing list provisioning, and D1-D5 checklist orchestration.

Runs in **Claude Desktop**, **Claude Code**, **Goose**, or any MCP client.

## Quick Start (5 minutes)

### 1. Clone and install

```bash
git clone git@github.com:LF-Engineering/aaif-mcp-server.git
cd aaif-mcp-server
pip install -e ".[test]"
```

### 2. Add to Claude Desktop

Open **Settings > Developer > Edit Config** in Claude Desktop, then add this to `mcpServers`:

```json
{
  "mcpServers": {
    "aaif-onboarding": {
      "command": "python",
      "args": ["-m", "aaif_mcp_server.server"],
      "cwd": "/path/to/aaif-mcp-server/src"
    }
  }
}
```

> **Alternative** if you ran `pip install -e .`:
> ```json
> {
>   "mcpServers": {
>     "aaif-onboarding": {
>       "command": "aaif-mcp-server"
>     }
>   }
> }
> ```

### 3. Restart Claude Desktop

After restarting, you should see 16 tools available. The server runs against **mock data** by default — no credentials needed to test.

## Verify it works

In Claude Desktop, try:

- "Validate Hitachi's membership tier" → calls `validate_membership_tier`
- "Check silo health for AAIF" → calls `get_silo_health`
- "Run the onboarding checklist for Sam Altman at OpenAI" → calls `run_onboarding_checklist`
- "Find mailing list gaps across all members" → calls `remediate_mailing_lists`

## Run tests

```bash
pytest tests/ -v
# 57 tests, all against mock data
```

## Connect to live SFDC/Groups.io (optional)

```bash
cp .env.example .env
# Fill in your credentials, then:
source .env
```

| Variable | Description |
|---|---|
| `SFDC_INSTANCE_URL` | e.g. `https://aaif--sandbox.my.salesforce.com` |
| `SFDC_CLIENT_ID` | Connected App consumer key |
| `SFDC_CLIENT_SECRET` | Connected App consumer secret |
| `SFDC_USERNAME` | API user email |
| `SFDC_PASSWORD` | Password + security token |
| `GROUPSIO_API_TOKEN` | Groups.io API bearer token |
| `GROUPSIO_ORG_ID` | Groups.io org slug (e.g. `aaif`) |

Without these, the server auto-falls back to mock data.

## Tools (16)

| Domain | Tool | Description |
|---|---|---|
| Tier Validation | `validate_membership_tier` | Look up org tier from SFDC |
| | `check_tier_entitlements` | Return entitlement matrix for a tier |
| | `detect_tier_anomalies` | Scan all members for access mismatches |
| Compliance | `check_sanctions` | Look up Descartes screening status in SFDC |
| | `check_tax_exempt_status` | Verify 501(c)(6) compliance |
| | `get_compliance_report` | Full compliance summary |
| | `flag_compliance_issue` | Create compliance ticket for human review |
| Mailing Lists | `provision_mailing_lists` | Add contact to tier-appropriate lists |
| | `remove_from_mailing_lists` | Remove contact from all lists |
| | `check_mailing_list_membership` | Check subscription status |
| | `remediate_mailing_lists` | Find and fix list gaps foundation-wide |
| Orchestration | `run_onboarding_checklist` | Execute D1-D5 onboarding flow |
| | `get_onboarding_status` | Check checklist progress |
| | `reconcile_silos` | Compare SFDC vs Groups.io vs SSO |
| | `run_offboarding_checklist` | Remove access on departure |
| | `get_silo_health` | Foundation-wide sync health score |

## Architecture

```
src/aaif_mcp_server/
├── server.py              # MCP server (FastMCP) — registers all tools/resources/prompts
├── config.py              # Mock data + provisioning rules + checklist templates
├── models.py              # Pydantic models (MemberOrg, Contact, SanctionsResult, etc.)
├── connectors/
│   ├── salesforce.py      # SFDC REST API v59 (auto-falls back to mock)
│   └── groupsio.py        # Groups.io API v1 (auto-falls back to mock)
├── tools/
│   ├── tier_validation.py # 3 tools: validate, entitlements, anomalies
│   ├── compliance.py      # 4 tools: sanctions, tax-exempt, report, flag
│   ├── mailing_list.py    # 4 tools: provision, remove, check, remediate
│   └── orchestrator.py    # 5 tools: onboard, status, reconcile, offboard, health
└── resources/
    ├── member.py           # member:// resources (profiles, list)
    └── rules.py            # rules:// resources (entitlements, provisioning, WGs)
```

## Mock Members (for testing)

| Org | Tier | Contact(s) |
|---|---|---|
| Hitachi, Ltd. | Gold | Takeshi Yamada, Yuki Tanaka |
| Bloomberg LP | Gold | Sambhav Kothari, Ania Musial |
| Natoma | Silver | Paresh Bhaya |
| iProov | Silver | Andrew Bud |
| OpenAI | Platinum | Sam Altman |

## License

Apache 2.0
