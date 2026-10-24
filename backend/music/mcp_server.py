"""Local/trusted-client MCP transport. Never forward Spotify tokens to a model."""

# Import os.
import os
# Import secrets.
import secrets

# Import HTTPException.
from fastapi import HTTPException
# Import Context, FastMCP.
from mcp.server.fastmcp import Context, FastMCP
# Import ToolError.
from mcp.server.fastmcp.exceptions import ToolError
# Import ToolAnnotations.
from mcp.types import ToolAnnotations
# Import Request.
from starlette.requests import Request
# Import JSONResponse.
from starlette.responses import JSONResponse
# Import ASGIApp, Receive, Scope, Send.
from starlette.types import ASGIApp, Receive, Scope, Send

# Import PlaylistProposal.
from music.models import PlaylistProposal
# Import playlist_service.
from music.service import playlist_service

# Set mcp.
mcp = FastMCP(
    "Playit Music",
    instructions=(
        "Submit independently generated song titles and artists with prepare_playlist. "
        "The user must preview and approve the draft in Playit before create_playlist. "
        "Catalog data is intentionally not returned to the model. Never request Spotify tokens."
    ),
    stateless_http=True, json_response=True, streamable_http_path="/",
)


# Define session_token.
def session_token(ctx: Context) -> str:
    # Set request.
    request = ctx.request_context.request
    # Check not isinstance(request, Request).
    if not isinstance(request, Request):
        # Propagate this failure instead of continuing.
        raise ToolError("An authenticated HTTP music session is required.")
    # Handle failures from this operation below.
    try:
        # Return playlist_service.session_token(request.headers.get('x-playit-session', '')).
        return playlist_service.session_token(request.headers.get("x-playit-session", ""))
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise ToolError(str(exc.detail)) from None


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True,
))
async def prepare_playlist(proposal: PlaylistProposal, ctx: Context) -> dict[str, str]:
    """Resolve LLM-recommended songs into a draft. Does not create a Spotify playlist.

    The trusted Playit UI fetches the preview using draft_id and displays it to the
    user. No Spotify catalog metadata is included in this tool response.
    """
    # Set token.
    token = session_token(ctx)
    # Handle failures from this operation below.
    try:
        # Wait for the operation and keep preview.
        preview = await playlist_service.prepare(proposal, token)
        # Return the assembled result to the caller.
        return {"draft_id": preview.draft_id, "status": "awaiting_user_approval"}
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise ToolError(f"Request failed ({exc.status_code}): {exc.detail}") from None


@mcp.tool(annotations=ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True,
))
async def create_playlist(draft_id: str, ctx: Context) -> dict[str, str]:
    """Create an already user-approved draft. Approval cannot be granted through MCP.

    Repeated calls return the recorded status without repeating uncertain writes.
    The UI retrieves the actual playlist link through its authenticated preview API.
    """
    # Set token.
    token = session_token(ctx)
    # Handle failures from this operation below.
    try:
        # Wait for the operation and keep result.
        result = await playlist_service.create(draft_id, token)
        # Return the assembled result to the caller.
        return {"draft_id": draft_id, "status": result.status}
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise ToolError(f"Request failed ({exc.status_code}): {exc.detail}") from None


class MCPAccessGuard:
    """Separate MCP app authentication from Spotify OAuth; no token passthrough.

    This is a trusted/local application-key deployment, not a public MCP OAuth
    authorization server. Keep the key out of browser code and model prompts.
    """

    # Define __init__.
    def __init__(self, app: ASGIApp) -> None:
        # Set self.app.
        self.app = app

    # Define __call__ as an awaited operation.
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Check scope['type'] != 'http'.
        if scope["type"] != "http":
            # Wait for self.app(scope, receive, send).
            await self.app(scope, receive, send)
            return
        # Read key from server configuration.
        key = os.getenv("PLAYIT_MCP_API_KEY", "")
        # Set request.
        request = Request(scope)
        # Check not key or len(key) < 32.
        if not key or len(key) < 32:
            # Set response.
            response = JSONResponse({"detail": "MCP is disabled. Configure PLAYIT_MCP_API_KEY (32+ characters)."}, status_code=503)
        # Check not secrets.compare_digest(request.headers.get('authorization', ''), f'Bear....
        elif not secrets.compare_digest(request.headers.get("authorization", ""), f"Bearer {key}"):
            # Set response.
            response = JSONResponse({"detail": "Invalid MCP application credential."}, status_code=401)
        else:
            # Handle failures from this operation below.
            try:
                # Call playlist_service.session_token.
                playlist_service.session_token(request.headers.get("x-playit-session", ""))
            except HTTPException:
                # Set response.
                response = JSONResponse({"detail": "Invalid or expired Playit music session."}, status_code=401)
            else:
                # Wait for self.app(scope, receive, send).
                await self.app(scope, receive, send)
                return
        # Set response.headers['Cache-Control'].
        response.headers["Cache-Control"] = "no-store"
        # Wait for response(scope, receive, send).
        await response(scope, receive, send)


# Set mcp_app.
mcp_app = MCPAccessGuard(mcp.streamable_http_app())

# File summary
# - Exposes prepare_playlist and already-approved create_playlist tools.
# - Requires an application key and valid Playit music session.
# - Keeps tokens/catalog results out of model-facing tool data.
