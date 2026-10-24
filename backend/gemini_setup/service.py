"""Reusable helpers for calling the Gemini Interactions API."""

# Import json.
import json
# Import logging.
import logging
# Import os.
import os
# Import AsyncIterator.
from collections.abc import AsyncIterator

# Import load_dotenv.
from dotenv import load_dotenv
# Import HTTPException.
from fastapi import HTTPException
# Import StreamingResponse.
from fastapi.responses import StreamingResponse
# Import genai.
from google import genai
# Import types.
from google.genai import types
# Import Literal.
from typing import Literal
# Import ConversationRequest, ConversationTurn, contextual_prompt.
from gemini_setup.conversation import ConversationRequest, ConversationTurn, contextual_prompt

# Call load_dotenv.
load_dotenv()

# Set logger.
logger = logging.getLogger(__name__)

# Set DEFAULT_FALLBACK_MODELS.
DEFAULT_FALLBACK_MODELS = (
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-3.8-flash"
)


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini credentials are not configured."""


class GeminiRequestError(RuntimeError):
    """Raised when all configured Gemini models fail to return output."""


def classify_request(request: ConversationRequest) -> Literal["playlist", "chat"]:
    """Choose a workflow, never authorize a provider write."""
    # Set instruction.
    instruction = (
        "Classify the current music conversation request. Return ONLY JSON "
        '{"action":"playlist"} or {"action":"chat"}. '
        "Use playlist for requests to recommend/find songs, make/build a playlist or mix, "
        "or refine an earlier recommendation (such as 'more upbeat', 'only Hindi', "
        "'make that a playlist', 'add more songs like those', 'I asked for 10', "
        "'make it 2 hours', 'you only gave me 3 songs'). Use chat for greetings, "
        "music questions/explanations, questions about a playlist, cancellations, or unrelated conversation. "
        "A mention of Spotify or the word playlist alone is not enough. "
        "Do not interpret approval/confirmation as permission to write; approval happens in the UI. "
        f"Current user message: {request.prompt}"
    )
    # Handle failures from this operation below.
    try:
        # Set result.
        result = json.loads(create_interaction(instruction, request.history))
        # Check not isinstance(result, dict) or result.get('action') not in ('playlist', 'c....
        if not isinstance(result, dict) or result.get("action") not in ("playlist", "chat"):
            # Propagate this failure instead of continuing.
            raise ValueError("Invalid intent response")
        # Return 'playlist' if result['action'] == 'playlist' else 'chat'.
        return "playlist" if result["action"] == "playlist" else "chat"
    except GeminiConfigurationError as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=502, detail="Could not understand the request. Please try again.") from exc


def create_stream_response(prompt: str, history: list[ConversationTurn] | None = None) -> StreamingResponse:
    """Validate input and build the streamed HTTP response."""
    # Check not prompt.strip().
    if not prompt.strip():
        # Stop this request with an explicit HTTP error.
        raise HTTPException(status_code=422, detail="A valid prompt is required.")

    # Return StreamingResponse(stream_events(prompt, history), media_type='application/x....
    return StreamingResponse(
        stream_events(prompt, history),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def stream_events(prompt: str, history: list[ConversationTurn] | None = None) -> AsyncIterator[str]:
    """Encode model chunks, completion, and failures as NDJSON events."""
    # Define encode.
    def encode(event_type: str, text: str = "") -> str:
        # Return json.dumps({'type': event_type, 'text': text}) + '\n'.
        return json.dumps({"type": event_type, "text": text}) + "\n"

    yield encode("status", "Waiting for Gemini…")
    # Set received_text.
    received_text = False
    # Set stream.
    stream = stream_interaction(prompt, history)
    # Handle failures from this operation below.
    try:
        # Process each text in stream.
        async for text in stream:
            # Set received_text.
            received_text = True
            yield encode("delta", text)
        # Check not received_text.
        if not received_text:
            # Propagate this failure instead of continuing.
            raise GeminiRequestError("Gemini returned no answer text.")
        yield encode("done")
    except Exception as exc:
        # Call logger.warning.
        logger.warning("Gemini stream failed (%s)", type(exc).__name__)
        yield encode("error", "Could not complete the response. Please try again.")
    finally:
        # Wait for stream.aclose().
        await stream.aclose()


async def stream_interaction(prompt: str, history: list[ConversationTurn] | None = None) -> AsyncIterator[str]:
    """Yield real Gemini answer chunks as they are generated."""
    # Read api_key from server configuration.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    # Check not api_key.
    if not api_key:
        # Propagate this failure instead of continuing.
        raise GeminiConfigurationError("Gemini API key is missing.")
    # Set client.
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))
    # Manage client.aio with automatic cleanup.
    async with client.aio as async_client:
        # Read stream from server configuration.
        stream = await async_client.models.generate_content_stream(
            model=os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite"),
            contents=[types.Content(
                role="model" if turn.role == "assistant" else "user",
                parts=[types.Part.from_text(text=turn.text)],
            ) for turn in history or []] + [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])],
        )
        
        # Handle failures from this operation below.
        try:
            # Process each chunk in stream.
            async for chunk in stream:
                # Process each candidate in chunk.candidates or [].
                for candidate in chunk.candidates or []:
                    # Check candidate.content.
                    if candidate.content:
                        # Process each part in candidate.content.parts or [].
                        for part in candidate.content.parts or []:
                            # Check part.text and (not part.thought).
                            if part.text and not part.thought:
                                yield part.text
                        break
        finally:
            # Wait for stream.aclose().
            await stream.aclose()


def create_interaction(prompt: str, history: list[ConversationTurn] | None = None) -> str:
    """Try the primary model and fallbacks, allowing 10 seconds per attempt."""
    # Read api_key from server configuration.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    # Check not api_key.
    if not api_key:
        # Propagate this failure instead of continuing.
        raise GeminiConfigurationError(
            "Gemini API key is missing; set GEMINI_API_KEY or GOOGLE_API_KEY in .env."
        )

    # Read primary_model from server configuration.
    primary_model = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite" )
    # Read configured_fallbacks from server configuration.
    configured_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS")
    # Check configured_fallbacks.
    if configured_fallbacks:
        # Set fallback_models.
        fallback_models = tuple(
            model.strip() for model in configured_fallbacks.split(",") if model.strip()
        )
    else:
        # Set fallback_models.
        fallback_models = DEFAULT_FALLBACK_MODELS

    # Keep compatibility with the old single-fallback environment setting.
    legacy_fallback = os.getenv("GEMINI_FALLBACK_MODEL")
    # Check legacy_fallback.
    if legacy_fallback:
        # Update fallback_models.
        fallback_models += (legacy_fallback.strip(),)

    # Set models.
    models = tuple(dict.fromkeys((primary_model, *fallback_models)))
    # Set client.
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=10_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    # Declare last_error.
    last_error: Exception | None = None
    # Process each model in models.
    for model in models:
        # Handle failures from this operation below.
        try:
            # Call print.
            print(f"Trying Gemini model: {model}", flush=True)
            # Set interaction.
            interaction = client.interactions.create(
                model=model,
                input=contextual_prompt(prompt, history),
                timeout=10_000,
            )
            # Set output.
            output = interaction.output_text
            # Check not output.
            if not output:
                # Propagate this failure instead of continuing.
                raise GeminiRequestError(f"Gemini model {model} returned an empty response.")
            # Call logger.info.
            logger.info("Gemini model %s returned a response", model)
            # Return output.
            return output
        except Exception as exc:
            # Set last_error.
            last_error = exc
            # Call print.
            print(
                f"Gemini model {model} failed ({type(exc).__name__}: {exc}); "
                "trying the next fallback.",
                flush=True,
            )
            # Call logger.warning.
            logger.warning(
                "Gemini model %s failed (%s): %s; trying the next model",
                model,
                type(exc).__name__,
                exc,
            )

    # Propagate this failure instead of continuing.
    raise GeminiRequestError(
        f"All configured Gemini models failed: {', '.join(models)}."
    ) from last_error

# File summary
# - Centralizes Gemini intent classification and SDK requests.
# - Encodes public status/text/error events as NDJSON.
# - Applies legacy SDK fallbacks separately from LangChain generation.
