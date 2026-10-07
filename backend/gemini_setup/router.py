from fastapi import APIRouter, HTTPException
import httpx
from google.genai.errors import APIError
from pydantic import BaseModel

from gemini_setup.service import (
    GeminiConfigurationError,
    GeminiRequestError,
    create_interaction,
)

router = APIRouter(prefix="/gemini", tags=["Gemini"])


class InteractionRequest(BaseModel):
    prompt: str


@router.post("/interactions")
def run_interaction(request: InteractionRequest) -> dict[str, str]:
    try:
        return {"output": create_interaction(request.prompt)}
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Gemini did not respond before the request timed out.",
        ) from exc
    except GeminiRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {exc.message}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not get a response from Gemini.",
        ) from exc