"""
Recommendation service — interfaces with the Groq API to generate ranked
restaurant recommendations.

Public API
----------
RecommendationService
    Main service class.  Instantiate once and call ``get_recommendations()``.

RecommendationError
    Raised when all LLM attempts (retries + fallback model) are exhausted.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from groq import Groq

from src.config import (
    GROQ_MODEL_FALLBACK,
    GROQ_MODEL_PRIMARY,
    LLM_MAX_RETRIES,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    TOP_K_RESULTS,
)
from src.models.schemas import Recommendation, RecommendationResponse
from src.services.prompt_builder import build_messages

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Custom exception
# ──────────────────────────────────────────────


class RecommendationError(Exception):
    """Raised when the recommendation service cannot produce results."""


# ──────────────────────────────────────────────
# Response parsing helpers
# ──────────────────────────────────────────────

# Regex to strip markdown fences if the LLM wraps its output in ```json … ```
_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*([\s\S]*?)```",
    re.IGNORECASE,
)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Parse JSON from the LLM's raw text output.

    The model is instructed to return raw JSON, but occasionally wraps it
    in markdown fences.  This helper strips those before parsing.

    Raises
    ------
    json.JSONDecodeError
        If no valid JSON can be extracted.
    """
    # First try: parse the entire string
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second try: extract from markdown fences
    match = _JSON_FENCE_RE.search(text)
    if match:
        return json.loads(match.group(1).strip())

    # Third try: find the first { … } block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise json.JSONDecodeError(
        "No valid JSON found in LLM response", text, 0
    )


def _validate_response(data: dict[str, Any]) -> RecommendationResponse:
    """
    Validate and coerce the parsed JSON into a ``RecommendationResponse``.

    If the top-level dict has a ``recommendations`` key that is a list of
    dicts, Pydantic will handle the rest.  Missing ``summary`` defaults to
    an empty string.
    """
    # Some models return the list at the top level without a wrapper
    if isinstance(data, list):
        data = {"recommendations": data, "summary": ""}

    # Ensure 'recommendations' key exists
    if "recommendations" not in data:
        # Try common alternative keys
        for alt_key in ("results", "restaurants", "ranked"):
            if alt_key in data:
                data["recommendations"] = data.pop(alt_key)
                break
        else:
            raise ValueError(
                "LLM response missing 'recommendations' key"
            )

    return RecommendationResponse(**data)


# ──────────────────────────────────────────────
# Service class
# ──────────────────────────────────────────────


class RecommendationService:
    """
    Groq-powered recommendation engine with retry and model-fallback.

    Parameters
    ----------
    api_key : str | None
        Groq API key.  Falls back to ``GROQ_API_KEY`` env var.
    primary_model : str
        First-choice Groq model name.
    fallback_model : str
        Backup model if the primary repeatedly fails.
    max_retries : int
        Retry count *per model* before switching.
    temperature : float
        LLM sampling temperature.
    max_tokens : int
        Maximum tokens in the LLM response.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        primary_model: str = GROQ_MODEL_PRIMARY,
        fallback_model: str = GROQ_MODEL_FALLBACK,
        max_retries: int = LLM_MAX_RETRIES,
        temperature: float = LLM_TEMPERATURE,
        max_tokens: int = LLM_MAX_TOKENS,
    ) -> None:
        resolved_key = api_key or os.getenv("GROQ_API_KEY")
        if not resolved_key:
            raise RecommendationError(
                "GROQ_API_KEY is not set.  "
                "Add it to your .env file or pass it explicitly."
            )
        self.client = Groq(api_key=resolved_key)
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

    # ── Core recommendation flow ──────────────────────────────────

    def get_recommendations(
        self,
        prefs: "UserPreferences",
        candidates_df: "pd.DataFrame",
    ) -> RecommendationResponse:
        """
        Generate ranked restaurant recommendations.

        Parameters
        ----------
        prefs : UserPreferences
            Validated user preferences.
        candidates_df : pd.DataFrame
            Filtered restaurant candidates.

        Returns
        -------
        RecommendationResponse
            Validated, structured recommendations from the LLM.

        Raises
        ------
        RecommendationError
            If all retry and fallback attempts are exhausted.
        """
        messages = build_messages(prefs, candidates_df)
        last_error: Exception | None = None

        for model in [self.primary_model, self.fallback_model]:
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.info(
                        "Calling Groq API — model=%s, attempt=%d/%d",
                        model, attempt, self.max_retries,
                    )
                    response = self._call_api(model, messages)
                    parsed = self._parse_response(response)
                    logger.info(
                        "Successfully parsed %d recommendations",
                        len(parsed.recommendations),
                    )
                    return parsed

                except json.JSONDecodeError as exc:
                    last_error = exc
                    logger.warning(
                        "JSON parse error (model=%s, attempt=%d): %s",
                        model, attempt, exc,
                    )
                except ValueError as exc:
                    last_error = exc
                    logger.warning(
                        "Validation error (model=%s, attempt=%d): %s",
                        model, attempt, exc,
                    )
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning(
                        "API error (model=%s, attempt=%d): %s",
                        model, attempt, exc,
                    )

                # Exponential backoff: 1s, 2s, 4s …
                if attempt < self.max_retries:
                    backoff = 2 ** (attempt - 1)
                    logger.info("Backing off for %ds", backoff)
                    time.sleep(backoff)

            logger.warning(
                "All %d attempts exhausted for model '%s' — "
                "falling back to next model.",
                self.max_retries, model,
            )

        raise RecommendationError(
            f"All LLM attempts failed. Last error: {last_error}"
        )

    # ── Internal helpers ──────────────────────────────────────────

    def _call_api(
        self,
        model: str,
        messages: list[dict[str, str]],
    ) -> str:
        """Make the actual Groq chat completions call and return raw text."""
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Empty response from Groq API")
        return content

    @staticmethod
    def _parse_response(raw_text: str) -> RecommendationResponse:
        """Extract JSON and validate into a Pydantic model."""
        data = _extract_json(raw_text)
        return _validate_response(data)
