from fastapi import APIRouter

router = APIRouter(prefix="/login", tags=["Login"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "login"}