"""Tests for PIS (Project Infrastructure Service) connectors.

Tests PISClient, PISGroupsIOConnector, and PISGitHubConnector
with mocked HTTP responses to validate request formation, pagination,
caching, and error handling — without needing real PIS credentials.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from aaif_mcp_server.connectors.pis_client import PISClient
from aaif_mcp_server.connectors.pis_groupsio import PISGroupsIOConnector
from aaif_mcp_server.connectors.pis_github import PISGitHubConnector


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def pis_client():
    """PIS client with test credentials."""
    return PISClient(
        acl_token="test-acl-token",
        username="test-user",
        base_url="https://pis-test.example.com",
    )


@pytest.fixture
def mock_subgroups():
    """Mock PIS subgroup list response (AAIF mailing lists)."""
    return [
        {
            "id": 101,
            "group_id": 101,
            "group_name": "aaif",
            "title": "governing-board",
            "description": "AAIF Governing Board",
            "subscriber_count": 12,
            "type": "sub",
            "visibility": "restricted",
            "url": "https://lists.aaif.io/g/governing-board",
        },
        {
            "id": 102,
            "group_id": 102,
            "group_name": "aaif",
            "title": "members-all",
            "description": "All AAIF Members",
            "subscriber_count": 45,
            "type": "sub",
            "visibility": "restricted",
            "url": "https://lists.aaif.io/g/members-all",
        },
        {
            "id": 103,
            "group_id": 103,
            "group_name": "aaif",
            "title": "wg-agentic-commerce",
            "description": "Agentic Commerce WG",
            "subscriber_count": 8,
            "type": "sub",
            "visibility": "restricted",
            "url": "https://lists.aaif.io/g/wg-agentic-commerce",
        },
    ]


@pytest.fixture
def mock_members():
    """Mock PIS member list for governing-board."""
    return [
        {
            "member_id": 1001,
            "email": "t.yamada@hitachi.com",
            "full_name": "Taro Yamada",
            "user_id": "uid-yamada",
            "group_id": 101,
            "organization": "Hitachi",
            "job_title": "VP Engineering",
            "delivery_mode": "email_delivery_single",
            "mod_status": "none",
            "member_type": "direct",
            "status": "active",
        },
        {
            "member_id": 1002,
            "email": "skothari@bloomberg.net",
            "full_name": "Sanjay Kothari",
            "user_id": "uid-kothari",
            "group_id": 101,
            "organization": "Bloomberg",
            "job_title": "Director",
            "delivery_mode": "email_delivery_single",
            "mod_status": "none",
            "member_type": "direct",
            "status": "active",
        },
    ]


# ── PISClient Tests ──────────────────────────────────────────────


class TestPISClient:
    """Test PIS HTTP client basics."""

    def test_is_configured(self, pis_client):
        assert pis_client.is_configured is True

    def test_not_configured_without_token(self):
        client = PISClient(acl_token="", username="test")
        assert client.is_configured is False

    def test_not_configured_without_username(self):
        client = PISClient(acl_token="test", username="")
        assert client.is_configured is False

    def test_headers_contain_required_fields(self, pis_client):
        headers = pis_client._headers()
        assert headers["X-ACL"] == "test-acl-token"
        assert headers["X-USERNAME"] == "test-user"
        assert "X-REQUEST-ID" in headers
        assert headers["Content-Type"] == "application/json"

    def test_headers_unique_request_id(self, pis_client):
        h1 = pis_client._headers()
        h2 = pis_client._headers()
        assert h1["X-REQUEST-ID"] != h2["X-REQUEST-ID"]

    @pytest.mark.asyncio
    async def test_get_paginated_single_page(self, pis_client):
        """Pagination stops when no page_token in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"id": 1}, {"id": 2}],
            "meta": {},
        }
        mock_response.raise_for_status = MagicMock()

        pis_client._client = AsyncMock()
        pis_client._client.get = AsyncMock(return_value=mock_response)

        items = await pis_client.get_paginated("/v2/test", params={"foo": "bar"})

        assert len(items) == 2
        assert items[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_paginated_multi_page(self, pis_client):
        """Pagination follows page_token across pages."""
        page1 = MagicMock()
        page1.json.return_value = {
            "data": [{"id": 1}],
            "meta": {"page_token": "next-page"},
        }
        page1.raise_for_status = MagicMock()

        page2 = MagicMock()
        page2.json.return_value = {
            "data": [{"id": 2}],
            "meta": {},
        }
        page2.raise_for_status = MagicMock()

        pis_client._client = AsyncMock()
        pis_client._client.get = AsyncMock(side_effect=[page1, page2])

        items = await pis_client.get_paginated("/v2/test")

        assert len(items) == 2
        assert pis_client._client.get.call_count == 2


# ── PISGroupsIOConnector Tests ───────────────────────────────────


class TestPISGroupsIOConnector:
    """Test Groups.io connector via PIS."""

    @pytest.fixture
    def connector(self, pis_client, mock_subgroups):
        """PIS Groups.io connector with pre-populated cache."""
        conn = PISGroupsIOConnector(
            pis_client=pis_client,
            project_id="test-aaif-project",
        )
        # Pre-populate cache (skip actual API call)
        for sg in mock_subgroups:
            title = sg["title"]
            domain = sg["url"].split("//")[1].split("/")[0]
            list_name = f"{title}@{domain}"
            conn._subgroup_cache[list_name] = sg["id"]
            conn._id_to_name[sg["id"]] = list_name
        conn._cache_built = True
        return conn

    def test_resolve_exact_match(self, connector):
        """Resolve by exact list name."""
        sg_id = connector._resolve_subgroup_id("governing-board@lists.aaif.io")
        assert sg_id == 101

    def test_resolve_prefix_match(self, connector):
        """Resolve by prefix (without domain)."""
        sg_id = connector._resolve_subgroup_id("governing-board")
        assert sg_id == 101

    def test_resolve_unknown_returns_none(self, connector):
        """Unknown list returns None."""
        sg_id = connector._resolve_subgroup_id("nonexistent-list@lists.aaif.io")
        assert sg_id is None

    @pytest.mark.asyncio
    async def test_get_lists(self, connector):
        """get_lists returns sorted list names from cache."""
        lists = await connector.get_lists("aaif")
        assert len(lists) == 3
        assert lists[0] == "governing-board@lists.aaif.io"
        assert lists[1] == "members-all@lists.aaif.io"
        assert lists[2] == "wg-agentic-commerce@lists.aaif.io"

    @pytest.mark.asyncio
    async def test_is_member_true(self, connector, mock_members):
        """is_member returns True when email found in member list."""
        connector._pis.get_paginated = AsyncMock(return_value=mock_members)

        result = await connector.is_member(
            "governing-board@lists.aaif.io", "t.yamada@hitachi.com"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_is_member_false(self, connector, mock_members):
        """is_member returns False when email not in member list."""
        connector._pis.get_paginated = AsyncMock(return_value=mock_members)

        result = await connector.is_member(
            "governing-board@lists.aaif.io", "unknown@example.com"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_is_member_unknown_list(self, connector):
        """is_member returns False for unknown list."""
        result = await connector.is_member(
            "nonexistent@lists.aaif.io", "t.yamada@hitachi.com"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_add_member_success(self, connector):
        """add_member calls POST and returns success."""
        connector._pis.post = AsyncMock(
            return_value={"member_id": 9999, "email": "new@example.com"}
        )

        result = await connector.add_member(
            "governing-board@lists.aaif.io", "new@example.com"
        )
        assert result["status"] == "added"
        assert result["email"] == "new@example.com"
        assert result["mode"] == "pis_live"

        # Verify the POST was called with correct path
        connector._pis.post.assert_called_once()
        call_args = connector._pis.post.call_args
        assert "/v2/groupsio_subgroup/101/members" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_add_member_already_exists(self, connector):
        """add_member returns already_member on 409."""
        resp = MagicMock()
        resp.status_code = 409
        connector._pis.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Conflict", request=MagicMock(), response=resp
            )
        )

        result = await connector.add_member(
            "governing-board@lists.aaif.io", "existing@example.com"
        )
        assert result["status"] == "already_member"

    @pytest.mark.asyncio
    async def test_add_member_unknown_list(self, connector):
        """add_member returns error for unknown list."""
        result = await connector.add_member(
            "nonexistent@lists.aaif.io", "new@example.com"
        )
        assert result["status"] == "error"
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_remove_member_success(self, connector, mock_members):
        """remove_member finds member_id then DELETEs."""
        connector._pis.get_paginated = AsyncMock(return_value=mock_members)
        connector._pis.delete = AsyncMock(return_value={"status": "deleted"})

        result = await connector.remove_member(
            "governing-board@lists.aaif.io", "t.yamada@hitachi.com"
        )
        assert result["status"] == "removed"

        # Verify DELETE was called with correct member ID
        connector._pis.delete.assert_called_once()
        call_path = connector._pis.delete.call_args[0][0]
        assert "/v2/groupsio_subgroup/101/members/1001" in call_path

    @pytest.mark.asyncio
    async def test_remove_member_not_found(self, connector, mock_members):
        """remove_member returns not_member when email not in list."""
        connector._pis.get_paginated = AsyncMock(return_value=mock_members)

        result = await connector.remove_member(
            "governing-board@lists.aaif.io", "nobody@example.com"
        )
        assert result["status"] == "not_member"

    @pytest.mark.asyncio
    async def test_get_members(self, connector, mock_members):
        """get_members returns list of email strings."""
        connector._pis.get_paginated = AsyncMock(return_value=mock_members)

        members = await connector.get_members("governing-board@lists.aaif.io")
        assert len(members) == 2
        assert "t.yamada@hitachi.com" in members
        assert "skothari@bloomberg.net" in members

    @pytest.mark.asyncio
    async def test_get_member_count(self, connector):
        """get_member_count calls the count endpoint."""
        connector._pis.get = AsyncMock(return_value={"count": 12})

        count = await connector.get_member_count("governing-board@lists.aaif.io")
        assert count == 12

    @pytest.mark.asyncio
    async def test_add_member_enriched(self, connector):
        """add_member_enriched sends full profile to PIS."""
        connector._pis.post = AsyncMock(
            return_value={"member_id": 9999}
        )

        result = await connector.add_member_enriched(
            list_name="governing-board@lists.aaif.io",
            email="new@example.com",
            full_name="Jane Doe",
            organization="Acme Corp",
            job_title="CTO",
        )
        assert result["status"] == "added"

        # Verify body includes enriched fields
        call_body = connector._pis.post.call_args[1]["json_body"]
        assert call_body["full_name"] == "Jane Doe"
        assert call_body["organization"] == "Acme Corp"
        assert call_body["job_title"] == "CTO"


# ── PISGitHubConnector Tests ────────────────────────────────────


class TestPISGitHubConnector:
    """Test GitHub connector via PIS."""

    @pytest.fixture
    def connector(self, pis_client):
        """PIS GitHub connector with pre-populated cache."""
        conn = PISGitHubConnector(
            pis_client=pis_client,
            project_id="test-aaif-project",
        )
        conn._org_cache = {"aaif-org": "org-uuid-123"}
        return conn

    @pytest.mark.asyncio
    async def test_list_orgs(self, connector):
        """list_orgs calls GET /v2/github with project filter."""
        mock_orgs = [
            {"id": "org-1", "organization": "aaif-org", "web_url": "https://github.com/aaif-org"},
        ]
        connector._pis.get_paginated = AsyncMock(return_value=mock_orgs)

        orgs = await connector.list_orgs()
        assert len(orgs) == 1
        assert orgs[0]["organization"] == "aaif-org"

    @pytest.mark.asyncio
    async def test_list_repos(self, connector):
        """list_repos calls GET /v2/github/{org}/repos."""
        mock_repos = [
            {"name": "wg-agentic-commerce", "dco_enabled": True},
            {"name": "wg-identity-trust", "dco_enabled": True},
        ]
        connector._pis.get_paginated = AsyncMock(return_value=mock_repos)

        repos = await connector.list_repos("aaif-org")
        assert len(repos) == 2

    @pytest.mark.asyncio
    async def test_get_repo(self, connector):
        """get_repo calls GET /v2/github/{org}/repos/{repo}."""
        mock_repo = {
            "name": "wg-agentic-commerce",
            "organization": "aaif-org",
            "dco_enabled": True,
        }
        connector._pis.get = AsyncMock(return_value=mock_repo)

        repo = await connector.get_repo("aaif-org", "wg-agentic-commerce")
        assert repo is not None
        assert repo["name"] == "wg-agentic-commerce"

    @pytest.mark.asyncio
    async def test_get_repo_not_found(self, connector):
        """get_repo returns None for unknown repo."""
        connector._pis.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )
        )

        repo = await connector.get_repo("aaif-org", "nonexistent")
        assert repo is None

    @pytest.mark.asyncio
    async def test_create_repo(self, connector):
        """create_repo calls POST /v2/github/{org}/repos."""
        connector._pis.post = AsyncMock(
            return_value={"name": "new-repo", "dco_enabled": True}
        )

        result = await connector.create_repo(
            org_name="aaif-org",
            repo_name="new-repo",
            description="Test repo",
            dco_enabled=True,
        )
        assert result["status"] == "created"
        assert result["mode"] == "pis_live"

    @pytest.mark.asyncio
    async def test_track_org(self, connector):
        """track_org calls POST /v2/github."""
        connector._pis.post = AsyncMock(
            return_value={"id": "new-org-uuid", "organization": "new-org"}
        )

        result = await connector.track_org("new-org")
        assert result["status"] == "tracked"
        assert "new-org" in connector._org_cache

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, connector):
        """health_check returns healthy when API responds."""
        connector._pis.get_paginated = AsyncMock(return_value=[{"id": "1"}])

        health = await connector.health_check()
        assert health["status"] == "healthy"
        assert health["connector"] == "pis_github"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, connector):
        """health_check returns unhealthy on API error."""
        connector._pis.get_paginated = AsyncMock(
            side_effect=Exception("Connection refused")
        )

        health = await connector.health_check()
        assert health["status"] == "unhealthy"


# ── Registry Integration Tests ───────────────────────────────────


class TestRegistryPISIntegration:
    """Test that registry properly switches between mock and PIS modes."""

    @pytest.mark.asyncio
    async def test_mock_mode_without_pis_env(self):
        """Without PIS env vars, registry uses mock GroupsIOConnector."""
        with patch.dict("os.environ", {}, clear=True):
            from aaif_mcp_server.connectors.registry import _pis_is_configured
            assert _pis_is_configured() is False

    @pytest.mark.asyncio
    async def test_pis_mode_with_env(self):
        """With PIS env vars, registry detects PIS mode."""
        with patch.dict(
            "os.environ",
            {"PIS_ACL_TOKEN": "test-token", "PIS_USERNAME": "test-user"},
        ):
            from aaif_mcp_server.connectors.registry import _pis_is_configured
            assert _pis_is_configured() is True
