from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from login.service import callback, spotify_login

router = APIRouter(prefix="/login", tags=["Login"])


@router.get("/")
def login() -> RedirectResponse:
    return spotify_login()


@router.get("/callback", response_model=None)
async def spotify_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> JSONResponse:
    return await callback(request, code=code, state=state, error=error)