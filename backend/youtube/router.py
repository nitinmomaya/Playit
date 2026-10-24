"""YouTube HTTP routes: validation/dependencies here, implementation in services."""

# Import Annotated, Any.
from typing import Annotated, Any

# Import APIRouter, Depends, HTTPException, Path, Query, Request, Response.
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
# Import JSONResponse, RedirectResponse.
from fastapi.responses import JSONResponse, RedirectResponse
# Import HTTPAuthorizationCredentials, HTTPBearer.
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Import callback, clear_oauth_cookies, no_store, validate_oauth_state, youtube_login.
from youtube.service import callback, clear_oauth_cookies, no_store, validate_oauth_state, youtube_login
# Import TokenRequest, get_channels, get_tokens, get_user, get_user_playlists.
from youtube.web_api import TokenRequest, get_channels, get_tokens, get_user, get_user_playlists
# Import AddItemRequest, CreatePlaylist, UpdatePlaylist, add_item_to_playlist, creat....
from youtube.web_api import (
    AddItemRequest, CreatePlaylist, UpdatePlaylist, add_item_to_playlist,
    create_playlist, delete_playlist, remove_item_from_playlist, update_playlist,
)

# Set ResourceId.
ResourceId = Annotated[str, Path(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")]

# Set router.
router = APIRouter(prefix="/youtube", tags=["YouTube"])
# Set bearer.
bearer = HTTPBearer(auto_error=False, scheme_name="YouTubeBearer")


# Define access_token.
def access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    # Check not credentials.
    if not credentials:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(401, "A Google bearer access token is required.",
                            headers={"WWW-Authenticate": "Bearer"})
    # Return credentials.credentials.
    return credentials.credentials


# Define login.
@router.get("/login")
def login() -> RedirectResponse:
    # Return youtube_login().
    return youtube_login()


# Define youtube_callback as an awaited operation.
@router.get("/callback")
async def youtube_callback(request: Request, code: str | None = None,
                           state: str | None = None, error: str | None = None) -> RedirectResponse:
    # Return await callback(request, code, state, error).
    return await callback(request, code, state, error)


# Define token as an awaited operation.
@router.post("/token")
async def token(body: TokenRequest, request: Request) -> JSONResponse:
    # Build error responses here too, so failed token requests are also non-cacheable.
    try:
        # Set verifier.
        verifier = validate_oauth_state(request, body.state) if body.grant_type == "authorization_code" else None
        # Set response.
        response = JSONResponse(await get_tokens(body, verifier))
    except HTTPException as exc:
        # Set response.
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    # Call no_store.
    no_store(response)
    # Check body.grant_type == 'authorization_code'.
    if body.grant_type == "authorization_code":
        # Call clear_oauth_cookies.
        clear_oauth_cookies(response)
    # Return response.
    return response


@router.get("/me")
async def me(response: Response, token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Google profile; use /channels for YouTube channel information."""
    # Call no_store.
    no_store(response)
    # Return await get_user(token).
    return await get_user(token)


# Define channels as an awaited operation.
@router.get("/channels")
async def channels(
    response: Response, token: Annotated[str, Depends(access_token)],
    page_token: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
    max_results: Annotated[int, Query(ge=1, le=50)] = 50,
) -> dict[str, Any]:
    # Call no_store.
    no_store(response)
    # Return await get_channels(token, page_token, max_results).
    return await get_channels(token, page_token, max_results)


# Define playlists as an awaited operation.
@router.get("/playlists")
async def playlists(
    response: Response, token: Annotated[str, Depends(access_token)],
    page_token: Annotated[str | None, Query(min_length=1, max_length=2048)] = None,
    max_results: Annotated[int, Query(ge=1, le=50)] = 50,
) -> dict[str, Any]:
    # Call no_store.
    no_store(response)
    # Return await get_user_playlists(token, page_token, max_results).
    return await get_user_playlists(token, page_token, max_results)


# Define health.
@router.get("/health")
def health() -> dict[str, str]:
    # Return the assembled result to the caller.
    return {"status": "ok", "service": "youtube"}


@router.post("/create_playlist", status_code=201)
async def create(request: CreatePlaylist, response: Response,
                 token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Create an empty playlist in the authorized YouTube channel."""
    # Call no_store.
    no_store(response)
    # Return await create_playlist(request, token).
    return await create_playlist(request, token)


@router.put("/update_playlist/{playlist_id}")
async def update(playlist_id: ResourceId, request: UpdatePlaylist, response: Response,
                 token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Replace name/description; omitted privacy remains unchanged."""
    # Call no_store.
    no_store(response)
    # Return await update_playlist(playlist_id, request, token).
    return await update_playlist(playlist_id, request, token)


@router.delete("/delete_playlist/{playlist_id}", status_code=204)
async def delete(playlist_id: ResourceId,
                 token: Annotated[str, Depends(access_token)]) -> Response:
    """Permanently delete the playlist; callers must obtain user confirmation."""
    # Wait for delete_playlist(playlist_id, token).
    await delete_playlist(playlist_id, token)
    # Set response.
    response = Response(status_code=204)
    # Call no_store.
    no_store(response)
    # Return response.
    return response


@router.post("/add_item/{playlist_id}/items", status_code=201)
async def add_item(playlist_id: ResourceId, request: AddItemRequest, response: Response,
                   token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Insert one video; returns its playlist-item ID."""
    # Call no_store.
    no_store(response)
    # Return await add_item_to_playlist(playlist_id, request, token).
    return await add_item_to_playlist(playlist_id, request, token)


@router.delete("/remove_item/{playlist_item_id}/items", status_code=204)
async def remove_item(playlist_item_id: ResourceId,
                      token: Annotated[str, Depends(access_token)]) -> Response:
    """Remove one playlist item, identified by playlist-item ID, not video ID."""
    # Wait for remove_item_from_playlist(playlist_item_id, token).
    await remove_item_from_playlist(playlist_item_id, token)
    # Set response.
    response = Response(status_code=204)
    # Call no_store.
    no_store(response)
    # Return response.
    return response

# File summary
# - Exposes Google OAuth, profile, channel, and playlist routes.
# - Validates resource IDs, pagination, and bearer input.
# - Direct writes require caller-managed confirmation.
