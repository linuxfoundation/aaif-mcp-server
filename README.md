# AAIF Member Onboarding MCP Server

48 tools across 12 domains for automating Linux Foundation AAIF member onboarding — tier validation, compliance screening, mailing list provisioning, contact management, calendar scheduling, working group enrollment, elections, press releases, brand validation, renewal intelligence, and D1-D5 checklist orchestration.

Runs in **Claude Desktop**, **Claude Code**, **Goose**, or any MCP client.

> **Sandbox Mode**: This server runs entirely on **mock data** by default. No backend credentials or API access needed to demo all 48 tools. Each connector auto-falls back to mock when its environment variables are unset.

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

After restarting, you should see 48 tools available. The server runs against **mock data** by default — no credentials needed to test.

## Verify it works

In Claude Desktop, try:

- "Validate Hitachi's membership tier" → `validate_membership_tier`
- "List contacts for Bloomberg" → `list_contacts`
- "Enroll Sam Altman in the Agentic Commerce working group" → `enroll_in_working_group`
- "Check election status for Agentic Commerce chair" → `get_election_status`
- "What's the churn risk for Natoma?" → `predict_churn_risk`
- "Draft a press release for OpenAI joining AAIF" → `draft_press_release`
- "Get the renewal dashboard" → `get_renewal_dashboard`
- "Run the onboarding checklist for Sam Altman at OpenAI" → `run_onboarding_checklist`

## Run tests

```bash
pytest tests/ -v
# 57 tests, all against mock data
```

---

## Tools (48 across 12 domains)

### Domain 1: Mailing List Provisioning (4 tools)

| Tool | Description |
|---|---|
| `provision_mailing_lists` | Add contact to tier-appropriate lists (dry_run default) |
| `remove_from_mailing_lists` | Remove contact from all lists |
| `check_mailing_list_membership` | Check subscription status |
| `remediate_mailing_lists` | Find and fix list gaps foundation-wide |

### Domain 2: Calendar & Meeting Management (3 tools)

| Tool | Description |
|---|---|
| `provision_calendar_invites` | Send calendar invites based on tier/role |
| `update_meeting_schedule` | Update WG recurring meeting time/link |
| `get_upcoming_meetings` | Get upcoming meetings for a contact |

### Domain 3: Compliance & Sanctions (4 tools)

| Tool | Description |
|---|---|
| `check_sanctions` | Look up Descartes screening status in SFDC |
| `check_tax_exempt_status` | Verify 501(c)(6) compliance |
| `get_compliance_report` | Full compliance summary |
| `flag_compliance_issue` | Create compliance ticket for human review |

### Domain 4: Tier Validation (3 tools)

| Tool | Description |
|---|---|
| `validate_membership_tier` | Look up org tier from SFDC |
| `check_tier_entitlements` | Return entitlement matrix for a tier |
| `detect_tier_anomalies` | Scan all members for access mismatches |

### Domain 5: Contact Role Management (5 tools)

| Tool | Description |
|---|---|
| `list_contacts` | List all contacts with roles and downstream access |
| `add_contact` | Add contact, trigger downstream provisioning |
| `update_contact_role` | Change role, show downstream effects |
| `remove_contact` | Remove contact, trigger offboarding |
| `transfer_voting_rights` | Transfer voting rights between contacts |

### Domain 6: Working Group Enrollment (5 tools)

| Tool | Description |
|---|---|
| `enroll_in_working_group` | Enroll across Groups.io + Discord + GitHub + Calendar |
| `leave_working_group` | Remove from WG across all systems |
| `list_available_working_groups` | List WGs with enrollment status |
| `get_wg_members` | Get WG member roster |
| `check_wg_eligibility` | Check tier/role eligibility for a WG |

### Domain 7: Election & Voting Operations (5 tools)

| Tool | Description |
|---|---|
| `create_election` | Create WG chair election in LFX Platform |
| `validate_candidate_eligibility` | Check candidate prerequisites |
| `check_voter_eligibility` | Check voting contact status |
| `get_election_status` | Get election timeline, candidates, votes |
| `diagnose_ballot_access` | Diagnose all blockers for ballot access |

### Domain 8: Press Release Drafting (3 tools)

| Tool | Description |
|---|---|
| `draft_press_release` | Generate press release from template + org data |
| `get_press_release_status` | Check approval workflow progress |
| `list_press_release_templates` | List available PR templates |

### Domain 9: Logo & Brand Validation (3 tools)

| Tool | Description |
|---|---|
| `validate_logo` | Validate logo against brand guidelines |
| `get_brand_guidelines` | Retrieve brand specs and requirements |
| `request_logo_upload` | Generate secure upload URL for logo submission |

### Domain 10: Onboarding Call Scheduling (3 tools)

| Tool | Description |
|---|---|
| `schedule_onboarding_call` | Schedule call with contacts and LF staff |
| `reschedule_onboarding_call` | Reschedule an existing call |
| `get_onboarding_call_status` | Check call status (scheduled/pending/done) |

### Domain 11: Renewal & Engagement Intelligence (5 tools)

| Tool | Description |
|---|---|
| `get_renewal_status` | Contract renewal timeline and stage |
| `get_engagement_score` | Calculate engagement score (0-100) |
| `predict_churn_risk` | Predict churn risk (0-100) |
| `get_renewal_dashboard` | Foundation-wide renewal pipeline view |
| `trigger_renewal_outreach` | Generate outreach plan with email template |

### Domain 12: Orchestration (5 tools)

| Tool | Description |
|---|---|
| `run_onboarding_checklist` | Execute D1-D5 onboarding flow |
| `get_onboarding_status` | Check checklist progress |
| `reconcile_silos` | Compare SFDC vs Groups.io vs SSO |
| `run_offboarding_checklist` | Remove access on departure |
| `get_silo_health` | Foundation-wide sync health score |

---

## API Access Required for Production

This server connects to **7 external systems**. In sandbox mode, all connectors auto-fall back to mock data when their environment variables are unset.

### Connector Status

| # | Connector | Service | Auth Type | Sandbox | Production |
|---|-----------|---------|-----------|---------|------------|
| 1 | **Salesforce** | CRM (accounts, contacts) | OAuth 2.0 | Mock | Implemented |
| 2 | **Groups.io** | Mailing lists | Bearer token | Mock | Implemented |
| 3 | **Google Calendar** | Meeting scheduling | Service account JWT | Mock | Stub |
| 4 | **Discord** | Community channels/roles | Bot token | Mock | Stub |
| 5 | **GitHub** | Repo collaborator access | PAT (Bearer) | Mock | Stub |
| 6 | **LFX Platform** | LFID, elections, voting | API key | Mock | Stub |
| 7 | **HubSpot** | Email templates, outreach | Private app key | Mock | Stub |

### Environment Variables

```bash
# 1. Salesforce CRM — OAuth 2.0 username-password flow
#    API: REST v59.0 — SOQL queries on Account, Contact objects
#    Used by: Tier Validation, Compliance, Contact Roles, Orchestrator
SFDC_INSTANCE_URL=https://aaif--sandbox.my.salesforce.com
SFDC_CLIENT_ID=<connected-app-consumer-key>
SFDC_CLIENT_SECRET=<connected-app-consumer-secret>
SFDC_USERNAME=<api-user-email>
SFDC_PASSWORD=<password+security-token>

# 2. Groups.io — Bearer token
#    API: v1 — directadd, removemember, getmembers, getgroups
#    Used by: Mailing List Provisioning, WG Enrollment
GROUPSIO_API_TOKEN=<bearer-token>
GROUPSIO_ORG_ID=aaif

# 3. Google Calendar — Service account JWT
#    API: Calendar v3 — events.insert, events.list, events.patch, events.delete
#    Used by: Calendar Management, Call Scheduling, WG Enrollment
GOOGLE_CALENDAR_CREDENTIALS=</path/to/service-account.json>
GOOGLE_CALENDAR_ADMIN_EMAIL=<admin@linuxfoundation.org>

# 4. Discord — Bot token
#    API: Bot API v10 — guild member roles, channel access
#    Used by: WG Enrollment (channel/role provisioning)
DISCORD_BOT_TOKEN=<bot-token>
DISCORD_SERVER_ID=<guild-id>

# 5. GitHub — Personal access token
#    API: REST v3 — repos collaborators (add/remove/list)
#    Used by: WG Enrollment (repo access)
GITHUB_TOKEN=<pat-with-repo-scope>
GITHUB_ORG=aaif

# 6. LFX Platform — API key
#    API: OpenProfile v1 — elections, LFID verification, ballots
#    Used by: Elections & Voting, LFID checks
LFX_API_URL=https://api.lfx.platform/v1
LFX_API_KEY=<api-key>

# 7. HubSpot — Private app API key
#    API: v3 — transactional email, templates
#    Used by: Press Release distribution, Renewal Outreach
HUBSPOT_API_KEY=<private-app-key>
```

### API Operations by Connector

**Salesforce** (REST v59.0):
- `POST /services/oauth2/token` — authenticate
- `GET /services/data/v59.0/query?q={SOQL}` — query accounts, contacts
- Custom fields: `Membership_Tier__c`, `Membership_Status__c`, `Contract_Signed_Date__c`, `LFID__c`

**Groups.io** (v1):
- `POST /directadd` — add member to group
- `POST /removemember` — remove member from group
- `GET /getmembers` — list group members (paginated)
- `GET /getmember` — check single membership

**Google Calendar** (v3):
- `POST /calendars/{id}/events` — create event/invite
- `GET /calendars/{id}/events` — list events
- `PATCH /calendars/{id}/events/{eventId}` — update event
- `DELETE /calendars/{id}/events/{eventId}` — cancel event

**Discord** (Bot API v10):
- `PUT /guilds/{id}/members/{userId}/roles/{roleId}` — add role
- `DELETE /guilds/{id}/members/{userId}/roles/{roleId}` — remove role
- `GET /guilds/{id}/members` — list members

**GitHub** (REST v3):
- `PUT /repos/{owner}/{repo}/collaborators/{username}` — add collaborator
- `DELETE /repos/{owner}/{repo}/collaborators/{username}` — remove collaborator
- `GET /repos/{owner}/{repo}/collaborators` — list collaborators

**LFX Platform** (v1):
- `POST /elections` — create election
- `GET /elections/{id}` — get election status
- `GET /contacts/{id}/lfid` — verify LFID
- `GET /elections/{id}/ballot/{contactId}` — check ballot status

**HubSpot** (v3):
- `POST /transactional/email` — send email from template
- `GET /marketing/emails/templates` — list templates

---

## Architecture

```
src/aaif_mcp_server/
├── server.py                  # MCP server (FastMCP) — registers 48 tools, 7 resources, 3 prompts
├── config.py                  # Mock data + provisioning rules + checklist templates
├── models.py                  # Pydantic models (MemberOrg, Contact, SanctionsResult, etc.)
├── connectors/
│   ├── base.py                # Abstract base classes (BaseConnector, BaseCRMConnector, etc.)
│   ├── salesforce.py          # Salesforce REST API v59 (auto-falls back to mock)
│   ├── groupsio.py            # Groups.io API v1 (auto-falls back to mock)
│   ├── calendar.py            # Google Calendar API v3 (mock)
│   ├── discord.py             # Discord Bot API v10 (mock)
│   ├── github_connector.py    # GitHub REST API v3 (mock)
│   ├── lfx_platform.py        # LFX Platform / OpenProfile API (mock)
│   └── hubspot.py             # HubSpot Marketing API (mock)
├── tools/
│   ├── tier_validation.py     # 3 tools: validate, entitlements, anomalies
│   ├── compliance.py          # 4 tools: sanctions, tax-exempt, report, flag
│   ├── mailing_list.py        # 4 tools: provision, remove, check, remediate
│   ├── orchestrator.py        # 5 tools: onboard, status, reconcile, offboard, health
│   ├── contact_roles.py       # 5 tools: list, add, update, remove, transfer
│   ├── calendar.py            # 3 tools: provision invites, update schedule, upcoming
│   ├── wg_enrollment.py       # 5 tools: enroll, leave, list, members, eligibility
│   ├── call_scheduling.py     # 3 tools: schedule, reschedule, status
│   ├── elections.py           # 5 tools: create, candidate, voter, status, diagnose
│   ├── press_release.py       # 3 tools: draft, status, templates
│   ├── logo_brand.py          # 3 tools: validate, guidelines, upload
│   └── renewal_intelligence.py # 5 tools: renewal, engagement, churn, dashboard, outreach
└── resources/
    ├── member.py              # member:// resources (profiles, list)
    ├── checklist.py           # checklist:// resources (D1-D5 templates)
    └── rules.py               # rules:// resources (entitlements, provisioning, WGs)
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
