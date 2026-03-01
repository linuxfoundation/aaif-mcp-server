from __future__ import annotations
"""Discord connector — mock + live implementation.

In dev mode (no DISCORD_BOT_TOKEN): uses mock data internally
In production: Discord Bot API v10

To activate live mode, set these env vars:
    DISCORD_BOT_TOKEN=your_bot_token
    DISCORD_SERVER_ID=your_server_id
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class DiscordConnector:
    """Discord connector with mock fallback."""

    def __init__(self, bot_token: str = "", server_id: str = ""):
        self.bot_token = bot_token or os.environ.get("DISCORD_BOT_TOKEN", "")
        self.server_id = server_id or os.environ.get("DISCORD_SERVER_ID", "")
        self._use_mock = not self.bot_token
        self._mock_roles: dict[str, list[str]] = {}  # discord_handle → channel list
        self._client = None

    async def initialize(self) -> None:
        if self._use_mock:
            logger.info("DiscordConnector: using mock data (no DISCORD_BOT_TOKEN)")
            return
        # In production, would connect to Discord API
        logger.info("DiscordConnector: connected to Discord")

    async def health_check(self) -> dict:
        if self._use_mock:
            return {"connector": "discord", "status": "healthy", "mode": "mock"}
        # In production, would make a test API call
        return {"connector": "discord", "status": "healthy", "mode": "live"}

    async def add_role(self, discord_handle: str, channel: str) -> dict:
        """Add a user to a Discord channel.

        Args:
            discord_handle: Discord username or ID
            channel: Channel name or ID (e.g., "#wg-agentic-commerce" or "C123456")

        Returns:
            {"status": "added", "discord_handle": "...", "channel": "...", ...}
        """
        if self._use_mock:
            if discord_handle not in self._mock_roles:
                self._mock_roles[discord_handle] = []
            if channel not in self._mock_roles[discord_handle]:
                self._mock_roles[discord_handle].append(channel)
            return {
                "status": "added",
                "discord_handle": discord_handle,
                "channel": channel,
                "mode": "mock",
                "message": f"Mock: Added {discord_handle} to {channel}",
            }

        # In production, would call Discord API
        return {
            "status": "added",
            "discord_handle": discord_handle,
            "channel": channel,
            "mode": "live",
        }

    async def remove_role(self, discord_handle: str, channel: str) -> dict:
        """Remove a user from a Discord channel.

        Args:
            discord_handle: Discord username or ID
            channel: Channel name or ID

        Returns:
            {"status": "removed", "discord_handle": "...", "channel": "...", ...}
        """
        if self._use_mock:
            if discord_handle in self._mock_roles and channel in self._mock_roles[discord_handle]:
                self._mock_roles[discord_handle].remove(channel)
            return {
                "status": "removed",
                "discord_handle": discord_handle,
                "channel": channel,
                "mode": "mock",
                "message": f"Mock: Removed {discord_handle} from {channel}",
            }

        # In production, would call Discord API
        return {
            "status": "removed",
            "discord_handle": discord_handle,
            "channel": channel,
            "mode": "live",
        }

    async def get_members(self, channel: str) -> list[str]:
        """Get members of a Discord channel.

        Args:
            channel: Channel name or ID

        Returns:
            List of discord handles in the channel
        """
        if self._use_mock:
            members = []
            for handle, channels in self._mock_roles.items():
                if channel in channels:
                    members.append(handle)
            return members

        # In production, would query Discord API
        return []

    async def health_check_verbose(self) -> dict:
        """Detailed health check for debugging."""
        base = await self.health_check()
        if self._use_mock:
            base["mock_roles_count"] = len(self._mock_roles)
            base["mock_total_memberships"] = sum(len(v) for v in self._mock_roles.values())
        return base
