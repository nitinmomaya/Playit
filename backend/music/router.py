# Import Annotated, Literal.
from typing import Annotated, Literal

# Import APIRouter, Depends, Response.
from fastapi import APIRouter, Depends, Response

# Import ConversationRequest.
from gemini_setup.conversation import ConversationRequest
# Import PlaylistPreview, PlaylistProposal, PlaylistResult, RecommendationPreview.
from music.models import PlaylistPreview, PlaylistProposal, PlaylistResult, RecommendationPreview
# Import SESSION_TTL, playlist_service.
from music.service import SESSION_TTL, playlist_service
# Import prepare_recommendations, recommendation_context.
from recommendations.langgraph_workflow import prepare_recommendations, recommendation_context
# Import access_token.
from spotify.router import access_token
# Import get_user.
from spotify.web_api import get_user

# Set router.
router = APIRouter(prefix="/music", tags=["Music playlists"])
# Set Token.
Token = Annotated[str, Depends(access_token)]


# Define recommend as an awaited operation.
@router.post("/recommendations", response_model=RecommendationPreview)
async def recommend(
    body: ConversationRequest,
    token: Token,
    response: Response,
    provider: Literal["spotify", "youtube"] = "spotify",
) -> RecommendationPreview:
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Wait for the operation and keep (preview, recommendations).
    preview, recommendations = await prepare_recommendations(body, token, provider)
    # Return RecommendationPreview(preview=preview, context_text=recommendation_context(....
    return RecommendationPreview(preview=preview, context_text=recommendation_context(recommendations))


@router.post("/sessions")
async def connect(token: Token, response: Response) -> dict[str, str | int]:
    """Create a short-lived application credential for a trusted MCP client."""
    # Wait for get_user(token).
    await get_user(token)
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Return the assembled result to the caller.
    return {"session_id": playlist_service.connect(token), "expires_in": SESSION_TTL}


# Define prepare as an awaited operation.
@router.post("/drafts", response_model=PlaylistPreview)
async def prepare(body: PlaylistProposal, token: Token, response: Response) -> PlaylistPreview:
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Return await playlist_service.prepare(body, token).
    return await playlist_service.prepare(body, token)


# Define preview as an awaited operation.
@router.get("/drafts/{draft_id}", response_model=PlaylistPreview)
async def preview(draft_id: str, token: Token, response: Response) -> PlaylistPreview:
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Return playlist_service.preview(draft_id, token).
    return playlist_service.preview(draft_id, token)


@router.post("/drafts/{draft_id}/approve", status_code=204)
async def approve(draft_id: str, token: Token) -> None:
    """UI-only approval; deliberately not exposed as an MCP tool."""
    # Call playlist_service.approve.
    playlist_service.approve(draft_id, token)


# Define create as an awaited operation.
@router.post("/drafts/{draft_id}/create", response_model=PlaylistResult)
async def create(draft_id: str, token: Token, response: Response) -> PlaylistResult:
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Return await playlist_service.create(draft_id, token).
    return await playlist_service.create(draft_id, token)

# File summary
# - Exposes graph-backed recommendations and shared draft HTTP APIs.
# - Keeps preview, approval, and creation as separate operations.
# - Bootstraps Spotify-bound sessions for trusted MCP clients.
