# Import APIRouter, Request.
from fastapi import APIRouter, Request
# Import RedirectResponse.
from fastapi.responses import RedirectResponse

# Import callback, spotify_login.
from login.service import callback, spotify_login

# Set router.
router = APIRouter(tags=["Login"])


# Define login.
@router.get("/spotify/login")
def login() -> RedirectResponse:
    # Return spotify_login().
    return spotify_login()


# Define spotify_callback as an awaited operation.
@router.get("/callback", response_model=None)
async def spotify_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    # Return await callback(request, code=code, state=state, error=error).
    return await callback(request, code=code, state=state, error=error)

# File summary
# - Exposes Spotify login and authorization callback routes.
# - Delegates OAuth behavior to login.service.
