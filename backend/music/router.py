from typing import Annotated

from fastapi import APIRouter, Depends, Response

from music.models import PlaylistPreview, PlaylistProposal, PlaylistResult
from music.service import SESSION_TTL, playlist_service
from spotify.router import access_token
from spotify.web_api import get_user

router = APIRouter(prefix="/music", tags=["Music playlists"])
Token = Annotated[str, Depends(access_token)]


@router.post("/sessions")
async def connect(token: Token, response: Response) -> dict[str, str | int]:
    """Create a short-lived application credential for a trusted MCP client."""
    await get_user(token)
    response.headers["Cache-Control"] = "no-store"
    return {"session_id": playlist_service.connect(token), "expires_in": SESSION_TTL}


@router.post("/drafts", response_model=PlaylistPreview)
async def prepare(body: PlaylistProposal, token: Token, response: Response) -> PlaylistPreview:
    response.headers["Cache-Control"] = "no-store"
    return await playlist_service.prepare(body, token)


@router.get("/drafts/{draft_id}", response_model=PlaylistPreview)
async def preview(draft_id: str, token: Token, response: Response) -> PlaylistPreview:
    response.headers["Cache-Control"] = "no-store"
    return playlist_service.preview(draft_id, token)


@router.post("/drafts/{draft_id}/approve", status_code=204)
async def approve(draft_id: str, token: Token) -> None:
    """UI-only approval; deliberately not exposed as an MCP tool."""
    playlist_service.approve(draft_id, token)


@router.post("/drafts/{draft_id}/create", response_model=PlaylistResult)
async def create(draft_id: str, token: Token, response: Response) -> PlaylistResult:
    response.headers["Cache-Control"] = "no-store"
    return await playlist_service.create(draft_id, token)