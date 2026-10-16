"""Trusted backend MCP client for recommendations produced by any LLM.

Import MusicMCPClient in a server-side orchestration layer. Never run this in
browser code or pass its headers/credentials as Gemini tool arguments.
"""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from music.models import PlaylistProposal


class MusicMCPClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self.base_url = base_url.rstrip("/")

    @asynccontextmanager
    async def connect(self, spotify_access_token: str) -> AsyncIterator[ClientSession]:
        """Bootstrap an owner-bound session using existing Spotify OAuth."""
        key = os.environ.get("PLAYIT_MCP_API_KEY", "")
        if len(key) < 32:
            raise ValueError("Configure PLAYIT_MCP_API_KEY with at least 32 characters.")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/music/sessions",
                headers={"Authorization": f"Bearer {spotify_access_token}"},
            )
            response.raise_for_status()
            session_id = response.json()["session_id"]
        async with httpx.AsyncClient(timeout=180, headers={
            "Authorization": f"Bearer {key}", "X-Playit-Session": session_id,
        }) as client:
            async with streamable_http_client(
                f"{self.base_url}/mcp/", http_client=client,
            ) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    async def prepare(self, proposal: PlaylistProposal, spotify_access_token: str) -> str:
        """Return a draft ID that the user can preview/approve in Playit."""
        async with self.connect(spotify_access_token) as session:
            result = await session.call_tool("prepare_playlist", {"proposal": proposal.model_dump()})
            if result.isError or not result.structuredContent:
                raise RuntimeError("MCP could not prepare the playlist; inspect the tool error.")
            return str(result.structuredContent["draft_id"])