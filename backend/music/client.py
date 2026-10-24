"""Trusted backend MCP client for recommendations produced by any LLM.

Import MusicMCPClient in a server-side orchestration layer. Never run this in
browser code or pass its headers/credentials as Gemini tool arguments.
"""

# Import os.
import os
# Import asynccontextmanager.
from contextlib import asynccontextmanager
# Import AsyncIterator.
from collections.abc import AsyncIterator

# Import httpx.
import httpx
# Import ClientSession.
from mcp import ClientSession
# Import streamable_http_client.
from mcp.client.streamable_http import streamable_http_client

# Import PlaylistProposal.
from music.models import PlaylistProposal


# Group the fields/behavior of MusicMCPClient.
class MusicMCPClient:
    # Define __init__.
    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        # Set self.base_url.
        self.base_url = base_url.rstrip("/")

    @asynccontextmanager
    async def connect(self, spotify_access_token: str) -> AsyncIterator[ClientSession]:
        """Bootstrap an owner-bound session using existing Spotify OAuth."""
        # Read key from server configuration.
        key = os.environ.get("PLAYIT_MCP_API_KEY", "")
        # Check len(key) < 32.
        if len(key) < 32:
            # Propagate this failure instead of continuing.
            raise ValueError("Configure PLAYIT_MCP_API_KEY with at least 32 characters.")
        # Manage httpx.AsyncClient(timeout=30) with automatic cleanup.
        async with httpx.AsyncClient(timeout=30) as client:
            # Wait for the operation and keep response.
            response = await client.post(
                f"{self.base_url}/music/sessions",
                headers={"Authorization": f"Bearer {spotify_access_token}"},
            )
            # Call response.raise_for_status.
            response.raise_for_status()
            # Set session_id.
            session_id = response.json()["session_id"]
        # Manage httpx.AsyncClient(timeout=180, headers={'Authorization': f'Bearer {key}', '... with automatic cleanup.
        async with httpx.AsyncClient(timeout=180, headers={
            "Authorization": f"Bearer {key}", "X-Playit-Session": session_id,
        }) as client:
            # Manage streamable_http_client(f'{self.base_url}/mcp/', http_client=client) with automatic cleanup.
            async with streamable_http_client(
                f"{self.base_url}/mcp/", http_client=client,
            ) as (read, write, _):
                # Manage ClientSession(read, write) with automatic cleanup.
                async with ClientSession(read, write) as session:
                    # Wait for session.initialize().
                    await session.initialize()
                    yield session

    async def prepare(self, proposal: PlaylistProposal, spotify_access_token: str) -> str:
        """Return a draft ID that the user can preview/approve in Playit."""
        # Manage self.connect(spotify_access_token) with automatic cleanup.
        async with self.connect(spotify_access_token) as session:
            # Wait for the operation and keep result.
            result = await session.call_tool("prepare_playlist", {"proposal": proposal.model_dump()})
            # Check result.isError or not result.structuredContent.
            if result.isError or not result.structuredContent:
                # Propagate this failure instead of continuing.
                raise RuntimeError("MCP could not prepare the playlist; inspect the tool error.")
            # Return str(result.structuredContent['draft_id']).
            return str(result.structuredContent["draft_id"])

# File summary
# - Connects trusted Python hosts to the HTTP MCP server.
# - Bootstraps a Spotify-bound session and attaches server-side headers.
# - Returns prepared draft IDs for separate human review.
