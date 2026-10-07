"""Reusable helpers for calling the Gemini Interactions API."""

import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

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


def create_interaction(prompt: str) -> str:
    """Try the primary model and fallbacks, allowing 10 seconds per attempt."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise GeminiConfigurationError(
            "Gemini API key is missing; set GEMINI_API_KEY or GOOGLE_API_KEY in .env."
        )

    primary_model = os.getenv("GEMINI_PRIMARY_MODEL", "gemini-3.5-flash-lite" )
    configured_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS")
    if configured_fallbacks:
        fallback_models = tuple(
            model.strip() for model in configured_fallbacks.split(",") if model.strip()
        )
    else:
        fallback_models = DEFAULT_FALLBACK_MODELS

    # Keep compatibility with the old single-fallback environment setting.
    legacy_fallback = os.getenv("GEMINI_FALLBACK_MODEL")
    if legacy_fallback:
        fallback_models += (legacy_fallback.strip(),)

    models = tuple(dict.fromkeys((primary_model, *fallback_models)))
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=10_000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    last_error: Exception | None = None
    for model in models:
        try:
            print(f"Trying Gemini model: {model}", flush=True)
            interaction = client.interactions.create(
                model=model,
                input=prompt,
                timeout=10_000,
            )
            output = interaction.output_text
            if not output:
                raise GeminiRequestError(f"Gemini model {model} returned an empty response.")
            logger.info("Gemini model %s returned a response", model)
            return output
        except Exception as exc:
            last_error = exc
            print(
                f"Gemini model {model} failed ({type(exc).__name__}: {exc}); "
                "trying the next fallback.",
                flush=True,
            )
            logger.warning(
                "Gemini model %s failed (%s): %s; trying the next model",
                model,
                type(exc).__name__,
                exc,
            )

    raise GeminiRequestError(
        f"All configured Gemini models failed: {', '.join(models)}."
    ) from last_error