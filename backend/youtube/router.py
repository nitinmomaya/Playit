"""YouTube HTTP routes: validation/dependencies here, implementation in services."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from youtube.service import callback, clear_oauth_cookies, no_store, validate_oauth_state, youtube_login
from youtube.web_api import TokenRequest, get_channels, get_tokens, get_user, get_user_playlists
from youtube.web_api import (
    AddItemRequest, CreatePlaylist, UpdatePlaylist, add_item_to_playlist,
    create_playlist, delete_playlist, remove_item_from_playlist, update_playlist,
)

ResourceId = Annotated[str, Path(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")]

router = APIRouter(prefix="/youtube", tags=["YouTube"])
bearer = HTTPBearer(auto_error=False, scheme_name="YouTubeBearer")


def access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if not credentials:
        raise HTTPException(401, "A Google bearer access token is required.",
                            headers={"WWW-Authenticate": "Bearer"})
    return credentials.credentials


@router.get("/login")
def login() -> RedirectResponse:
    return youtube_login()


@router.get("/callback")
async def youtube_callback(request: Request, code: str | None = None,
                           state: str | None = None, error: str | None = None) -> RedirectResponse:
    return await callback(request, code, state, error)


@router.post("/token")
async def token(body: TokenRequest, request: Request) -> JSONResponse:
    # Build error responses here too, so failed token requests are also non-cacheable.
    try:
        verifier = validate_oauth_state(request, body.state) if body.grant_type == "authorization_code" else None
        response = JSONResponse(await get_tokens(body, verifier))
    except HTTPException as exc:
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    no_store(response)
    if body.grant_type == "authorization_code":
        clear_oauth_cookies(response)
    return response


@router.get("/me")
async def me(response: Response, token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Google profile; use /channels for YouTube channel information."""
    no_store(response)
    return await get_user(token)


@router.get("/channels")
async def channels(
    response: Response, token: Annotated[str, Depends(access_token)],
    page_token: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
    max_results: Annotated[int, Query(ge=1, le=50)] = 50,
) -> dict[str, Any]:
    no_store(response)
    return await get_channels(token, page_token, max_results)


@router.get("/playlists")
async def playlists(
    response: Response, token: Annotated[str, Depends(access_token)],
    page_token: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
    max_results: Annotated[int, Query(ge=1, le=50)] = 50,
) -> dict[str, Any]:
    no_store(response)
    return await get_user_playlists(token, page_token, max_results)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "youtube"}


@router.post("/create_playlist", status_code=201)
async def create(request: CreatePlaylist, response: Response,
                 token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Create an empty playlist in the authorized YouTube channel."""
    no_store(response)
    return await create_playlist(request, token)


@router.put("/update_playlist/{playlist_id}")
async def update(playlist_id: ResourceId, request: UpdatePlaylist, response: Response,
                 token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Replace name/description; omitted privacy remains unchanged."""
    no_store(response)
    return await update_playlist(playlist_id, request, token)


@router.delete("/delete_playlist/{playlist_id}", status_code=204)
async def delete(playlist_id: ResourceId,
                 token: Annotated[str, Depends(access_token)]) -> Response:
    """Permanently delete the playlist; callers must obtain user confirmation."""
    await delete_playlist(playlist_id, token)
    response = Response(status_code=204)
    no_store(response)
    return response


@router.post("/add_item/{playlist_id}/items", status_code=201)
async def add_item(playlist_id: ResourceId, request: AddItemRequest, response: Response,
                   token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Insert one video; returns its playlist-item ID."""
    no_store(response)
    return await add_item_to_playlist(playlist_id, request, token)


@router.delete("/remove_item/{playlist_item_id}/items", status_code=204)
async def remove_item(playlist_item_id: ResourceId,
                      token: Annotated[str, Depends(access_token)]) -> Response:
    """Remove one playlist item, identified by playlist-item ID, not video ID."""
    await remove_item_from_playlist(playlist_item_id, token)
    response = Response(status_code=204)
    no_store(response)
    return response