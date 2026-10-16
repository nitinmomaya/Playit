"""Local/trusted-client MCP transport. Never forward Spotify tokens to a model."""

import os
import secrets

from fastapi import HTTPException
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from music.models import PlaylistProposal
from music.service import playlist_service

mcp = FastMCP(
    "Playit Music",
    instructions=(
        "Submit independently generated song titles and artists with prepare_playlist. "
        "The user must preview and approve the draft in Playit before create_playlist. "
        "Catalog data is intentionally not returned to the model. Never request Spotify tokens."
    ),
    stateless_http=True, json_response=True, streamable_http_path="/",
)


def session_token(ctx: Context) -> str:
    request = ctx.request_context.request
    if not isinstance(request, Request):
        raise ToolError("An authenticated HTTP music session is required.")
    try:
        return playlist_service.session_token(request.headers.get("x-playit-session", ""))
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from None


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True,
))
async def prepare_playlist(proposal: PlaylistProposal, ctx: Context) -> dict[str, str]:
    """Resolve LLM-recommended songs into a draft. Does not create a Spotify playlist.

    The trusted Playit UI fetches the preview using draft_id and displays it to the
    user. No Spotify catalog metadata is included in this tool response.
    """
    token = session_token(ctx)
    try:
        preview = await playlist_service.prepare(proposal, token)
        return {"draft_id": preview.draft_id, "status": "awaiting_user_approval"}
    except HTTPException as exc:
        raise ToolError(f"Request failed ({exc.status_code}): {exc.detail}") from None


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True,
))
async def create_playlist(draft_id: str, ctx: Context) -> dict[str, str]:
    """Create an already user-approved draft. Approval cannot be granted through MCP.

    Repeated calls return the recorded status without repeating uncertain writes.
    The UI retrieves the actual playlist link through its authenticated preview API.
    """
    token = session_token(ctx)
    try:
        result = await playlist_service.create(draft_id, token)
        return {"draft_id": draft_id, "status": result.status}
    except HTTPException as exc:
        raise ToolError(f"Request failed ({exc.status_code}): {exc.detail}") from None


class MCPAccessGuard:
    """Separate MCP app authentication from Spotify OAuth; no token passthrough.

    This is a trusted/local application-key deployment, not a public MCP OAuth
    authorization server. Keep the key out of browser code and model prompts.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        key = os.getenv("PLAYIT_MCP_API_KEY", "")
        request = Request(scope)
        if not key or len(key) < 32:
            response = JSONResponse({"detail": "MCP is disabled. Configure PLAYIT_MCP_API_KEY (32+ characters)."}, status_code=503)
        elif not secrets.compare_digest(request.headers.get("authorization", ""), f"Bearer {key}"):
            response = JSONResponse({"detail": "Invalid MCP application credential."}, status_code=401)
        else:
            try:
                playlist_service.session_token(request.headers.get("x-playit-session", ""))
            except HTTPException:
                response = JSONResponse({"detail": "Invalid or expired Playit music session."}, status_code=401)
            else:
                await self.app(scope, receive, send)
                return
        response.headers["Cache-Control"] = "no-store"
        await response(scope, receive, send)


mcp_app = MCPAccessGuard(mcp.streamable_http_app())