# Import APIRouter, HTTPException.
from fastapi import APIRouter, HTTPException
# Import Depends.
from fastapi import Depends
# Import StreamingResponse.
from fastapi.responses import StreamingResponse
# Import httpx.
import httpx
# Import APIError.
from google.genai.errors import APIError
# Import Annotated, Literal.
from typing import Annotated, Literal
# Import ConversationRequest.
from gemini_setup.conversation import ConversationRequest
# Import run_agent.
from gemini_setup.agent import run_agent
# Import access_token.
from spotify.router import access_token

# Import GeminiConfigurationError, GeminiRequestError, classify_request, create_inte....
from gemini_setup.service import (
    GeminiConfigurationError,
    GeminiRequestError,
    classify_request,
    create_interaction,
    create_stream_response,
)

# Set router.
router = APIRouter(prefix="/gemini", tags=["Gemini"])


# Set InteractionRequest.
InteractionRequest = ConversationRequest


@router.post("/agent")
async def run_agent_interaction(
    request: InteractionRequest,
    token: Annotated[str, Depends(access_token)],
    provider: Literal["spotify", "youtube"] = "spotify",
) -> dict[str, str | None]:
    """Route the request and execute playlist preparation before reporting success."""
    # Handle failures from this operation below.
    try:
        # Return await run_agent(request, token, provider).
        return await run_agent(request, token, provider)
    except httpx.TimeoutException as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=504, detail="Gemini did not respond before the request timed out.") from exc
    except APIError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Gemini could not complete the agent request.") from exc
    except HTTPException:
        # Propagate this failure instead of continuing.
        raise
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Could not complete the agent request.") from exc


@router.post("/intent")
def classify_intent(request: InteractionRequest) -> dict[str, str]:
    """Plan a conversational action; never authorize a Spotify write."""
    # Return the assembled result to the caller.
    return {"action": classify_request(request)}


# Define run_stream as an awaited operation.
@router.post("/interactions/stream")
async def run_stream(request: InteractionRequest) -> StreamingResponse:
    # Return create_stream_response(request.prompt, request.history).
    return create_stream_response(request.prompt, request.history)


# Define run_interaction.
@router.post("/interactions")
def run_interaction(request: InteractionRequest) -> dict[str, str]:
    # Handle failures from this operation below.
    try:
        # Return the assembled result to the caller.
        return {"output": create_interaction(request.prompt, request.history)}
    except GeminiConfigurationError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=504,
            detail="Gemini did not respond before the request timed out.",
        ) from exc
    except GeminiRequestError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except APIError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {exc.message}",
        ) from exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(
            status_code=502,
            detail="Could not get a response from Gemini.",
        ) from exc

# File summary
# - Exposes intent, agent, completed-chat, and streaming endpoints.
# - Delegates model operations to agent/service modules.
# - Translates request failures into HTTP responses.
