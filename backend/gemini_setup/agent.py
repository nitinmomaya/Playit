"""Route Gemini's intent to an executed playlist workflow or a chat reply."""

# Import os.
import os
# Import Literal.
from typing import Literal

# Import HTTPException.
from fastapi import HTTPException
# Import run_in_threadpool.
from fastapi.concurrency import run_in_threadpool
# Import genai.
from google import genai
# Import types.
from google.genai import types

# Import ConversationRequest.
from gemini_setup.conversation import ConversationRequest
# Import classify_request.
from gemini_setup.service import classify_request
# Import prepare_recommendations, recommendation_context.
from recommendations.langgraph_workflow import prepare_recommendations, recommendation_context

# Set _SYSTEM_INSTRUCTION.
_SYSTEM_INSTRUCTION = (
    "You are Playit, a music assistant. Respond naturally to ordinary music questions. "
    "This call is for conversation only and has not prepared or created any playlist. "
    "Never claim a draft is ready or that a review panel exists based on conversation text. "
    "Actual playlist drafts appear below the response that prepared them, with an approval button. "
    "If that preview is missing, ask the user to resend their playlist request to generate a new draft. "
    "Approval happens only through the visible preview button, not chat confirmation. "
    "Do not ask for or expose credentials."
)


# Define _conversation_contents.
def _conversation_contents(request: ConversationRequest) -> list[types.Content]:
    # Set contents.
    contents = [
        types.Content(
            role="model" if turn.role == "assistant" else "user",
            parts=[types.Part.from_text(text=turn.text)],
        )
        for turn in request.history
    ]
    # Call contents.append.
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=request.prompt)]))
    # Return contents.
    return contents


async def _prepare_playlist(request: ConversationRequest, spotify_token: str,
                            provider: Literal["spotify", "youtube"] = "spotify") -> tuple[str, str]:
    """Use existing recommendation and draft services; this does not write to Spotify."""
    # Wait for the operation and keep (preview, recommendations).
    preview, recommendations = await prepare_recommendations(request, spotify_token, provider)
    # Return the assembled result to the caller.
    return preview.draft_id, recommendation_context(recommendations)


async def run_agent(request: ConversationRequest, spotify_token: str,
                    provider: Literal["spotify", "youtube"] = "spotify") -> dict[str, str | None]:
    """Report a draft only after successful preparation; propagate workflow errors."""
    # Read api_key from server configuration.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    # Check not api_key.
    if not api_key:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=503, detail="Gemini API key is missing.")

    # Wait for the operation and keep action.
    action = await run_in_threadpool(classify_request, request)
    # Check action == 'playlist'.
    if action == "playlist":
        # Wait for the operation and keep (draft_id, context_text).
        draft_id, context_text = await _prepare_playlist(request, spotify_token, provider)
        # Return the assembled result to the caller.
        return {
            "text": "Review the matched songs below, then use the approval button to create your playlist.",
            "draft_id": draft_id,
            "context_text": context_text,
        }

    # Read model from server configuration.
    model = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite")
    # Set client.
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
    # Set config.
    config = types.GenerateContentConfig(
        system_instruction=_SYSTEM_INSTRUCTION + f" The selected destination is {provider}. Do not change it.",
        max_output_tokens=1024,
    )
    # Manage client.aio with automatic cleanup.
    async with client.aio as async_client:
        # Wait for the operation and keep response.
        response = await async_client.models.generate_content(
            model=model, contents=_conversation_contents(request), config=config,
        )
    # Return the assembled result to the caller.
    return {
        "text": (response.text or "").strip() or "I couldn't produce a response. Please try again.",
        "draft_id": None,
        "context_text": None,
    }

# File summary
# - Classifies intent before choosing chat or playlist preparation.
# - Returns a real draft ID only after successful graph execution.
# - Keeps approval and provider creation outside model replies.
