

# Import Annotated, Any.
from typing import Annotated, Any

# Import APIRouter, Depends, HTTPException, Request, Response.
from fastapi import APIRouter, Depends, HTTPException, Request, Response
# Import HTTPAuthorizationCredentials, HTTPBearer.
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Import STATE_COOKIE, validate_oauth_state.
from login.service import STATE_COOKIE, validate_oauth_state
# Import TokenRequest, get_tokens, get_user, get_user_playlists, spotify_create_play....
from spotify.web_api import TokenRequest, get_tokens, get_user, get_user_playlists, create_playlist as spotify_create_playlist

# Set router.
router = APIRouter(prefix="/spotify", tags=["Spotify"])

# Import SongRecommendations.
from models.song_details_model.songsdetails import  SongRecommendations

# Import recommend_songs, RecommendationRequest.
from spotify.service import recommend_songs, RecommendationRequest

# Import CreatePlaylist, AddItemRequest, RemoveItemRequest, UpdateItemRequest, add_i....
from spotify.web_api import CreatePlaylist,AddItemRequest, RemoveItemRequest, UpdateItemRequest, add_item_to_playlist, remove_item_from_playlist, update_item_from_playlist

# Set bearer.
bearer = HTTPBearer(auto_error=False)


# Define access_token.
def access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    # Check not credentials.
    if not credentials:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=401, detail="A bearer access token is required.",
                            headers={"WWW-Authenticate": "Bearer"})
    # Return credentials.credentials.
    return credentials.credentials


# Define token as an awaited operation.
@router.post("/token")
async def token(body: TokenRequest, request: Request, response: Response) -> dict[str, Any]:
    # Check body.grant_type == 'authorization_code'.
    if body.grant_type == "authorization_code":
        # Call validate_oauth_state.
        validate_oauth_state(request, body.state)
    # Wait for the operation and keep tokens.
    tokens = await get_tokens(body)
    # Set response.headers['Cache-Control'].
    response.headers["Cache-Control"] = "no-store"
    # Set response.headers['Pragma'].
    response.headers["Pragma"] = "no-cache"
    # Check body.grant_type == 'authorization_code'.
    if body.grant_type == "authorization_code":
        # Call response.delete_cookie.
        response.delete_cookie(STATE_COOKIE, path="/")
    # Return tokens.
    return tokens


# Define me as an awaited operation.
@router.get("/me")
async def me(token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    # Return await get_user(token).
    return await get_user(token)


@router.get("/users/{user_id}/playlists")

async def playlists(user_id: str, token: Annotated[str, Depends(access_token)]) -> dict[str, Any]:
    """Get a user's playlists."""
    # Return await get_user_playlists(user_id, token).
    return await get_user_playlists(user_id, token)


# Define health.
@router.get("/health")
def health() -> dict[str, str]:
    # Return the assembled result to the caller.
    return {"status": "ok", "service": "spotify"}


# Define get_recommendations.
@router.post("/recommendations", response_model=SongRecommendations)
def get_recommendations(request: RecommendationRequest) -> SongRecommendations:
    # Handle failures from this operation below.
    try:
        # Return recommend_songs(request).
        return recommend_songs(request)
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail=f"Could not get recommendations: {exc}",
        ) from exc

@router.post("/users/{user_id}/create_playlist")
async def create_playlist(
    user_id: str, request: CreatePlaylist, token: Annotated[str, Depends(access_token)]
):
    """Create a new playlist based on the recommendation request."""
    # Handle failures from this operation below.
    try:
        #create playlist based on the songs recommeneded in spotify
        return await spotify_create_playlist(user_id, request, token)
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail=f"Could not create playlist: {exc}",
        ) from exc

@router.post("/add_item/{playlist_id}/items")
async def add_item(
    playlist_id: str, request: AddItemRequest, token: Annotated[str, Depends(access_token)]
):
    """Add an item to a playlist."""
    # Handle failures from this operation below.
    try:
        # Return await add_item_to_playlist(playlist_id, request, token).
        return await add_item_to_playlist(playlist_id, request, token)
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail=f"Could not add item to playlist: {exc}",
        ) from exc

@router.post("/remove_item/{playlist_id}/items")
async def remove_item(playlist_id: str, request: RemoveItemRequest):
    """Remove an item from a playlist."""
    # Handle failures from this operation below.
    try:
        # Return await remove_item_from_playlist(playlist_id, request).
        return await remove_item_from_playlist(playlist_id, request)
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail=f"Could not remove item from playlist: {exc}",
        ) from exc

@router.put("/update_item/{playlist_id}/items")
async def update_item(playlist_id: str, request: UpdateItemRequest):
    """Update an item in a playlist."""
    # Handle failures from this operation below.
    try:
        # Return await update_item_from_playlist(playlist_id, request).
        return await update_item_from_playlist(playlist_id, request)
    except HTTPException as exc:
        # Propagate this failure instead of continuing.
        raise exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail=f"Could not update item in playlist: {exc}",
        ) from exc

# File summary
# - Validates Spotify HTTP requests and bearer credentials.
# - Exposes tokens, profiles, playlists, and compatibility endpoints.
# - Legacy remove/update routes are separate from the safe draft workflow.
