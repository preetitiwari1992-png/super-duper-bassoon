"""
Unit and integration tests for ``src.services.recommendation``.

All Groq API calls are **mocked** — no real network requests are made.

Covers
------
- JSON extraction from raw text (clean, fenced, embedded)
- Response validation (valid, missing keys, list-format, malformed)
- RecommendationService retry logic with exponential backoff
- Model fallback (primary → fallback)
- Error propagation when all attempts fail
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.models.schemas import RecommendationResponse, UserPreferences
from src.services.recommendation import (
    RecommendationError,
    RecommendationService,
    _extract_json,
    _validate_response,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

VALID_JSON_RESPONSE = json.dumps(
    {
        "recommendations": [
            {
                "rank": 1,
                "restaurant_name": "Tasty Bites",
                "cuisine": "North Indian",
                "rating": 4.5,
                "estimated_cost": 800.0,
                "explanation": "Great food with authentic flavors.",
            },
            {
                "rank": 2,
                "restaurant_name": "Spice Garden",
                "cuisine": "South Indian",
                "rating": 4.3,
                "estimated_cost": 600.0,
                "explanation": "Affordable and close to your area.",
            },
        ],
        "summary": "Top picks based on your love for Indian cuisine.",
    }
)


@pytest.fixture
def sample_prefs() -> UserPreferences:
    return UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Indian",
        min_rating=4.0,
    )


@pytest.fixture
def sample_candidates() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "restaurant_name": ["Tasty Bites", "Spice Garden"],
            "cuisines": ["North Indian", "South Indian"],
            "aggregate_rating": [4.5, 4.3],
            "average_cost": [800.0, 600.0],
            "votes": [500, 300],
            "has_online_delivery": [True, False],
            "has_table_booking": [True, True],
            "city": ["Bangalore", "Bangalore"],
            "location": ["Koramangala", "BTM"],
        }
    )


def _mock_completion(content: str) -> MagicMock:
    """Build a mock Groq completion object."""
    choice = MagicMock()
    choice.message.content = content
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ──────────────────────────────────────────────
# JSON extraction
# ──────────────────────────────────────────────


class TestExtractJson:
    def test_clean_json(self):
        data = _extract_json(VALID_JSON_RESPONSE)
        assert "recommendations" in data
        assert len(data["recommendations"]) == 2

    def test_json_with_markdown_fences(self):
        wrapped = f"```json\n{VALID_JSON_RESPONSE}\n```"
        data = _extract_json(wrapped)
        assert "recommendations" in data

    def test_json_with_surrounding_text(self):
        messy = f"Here are the results:\n{VALID_JSON_RESPONSE}\nHope this helps!"
        data = _extract_json(messy)
        assert "recommendations" in data

    def test_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("this is not json at all")

    def test_raises_on_empty_string(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("")


# ──────────────────────────────────────────────
# Response validation
# ──────────────────────────────────────────────


class TestValidateResponse:
    def test_valid_response(self):
        data = json.loads(VALID_JSON_RESPONSE)
        result = _validate_response(data)
        assert isinstance(result, RecommendationResponse)
        assert len(result.recommendations) == 2
        assert result.recommendations[0].rank == 1

    def test_list_format_wrapped_automatically(self):
        recs = json.loads(VALID_JSON_RESPONSE)["recommendations"]
        result = _validate_response(recs)
        assert isinstance(result, RecommendationResponse)
        assert len(result.recommendations) == 2

    def test_alternative_key_results(self):
        data = {
            "results": json.loads(VALID_JSON_RESPONSE)["recommendations"],
            "summary": "Test",
        }
        result = _validate_response(data)
        assert len(result.recommendations) == 2

    def test_alternative_key_restaurants(self):
        data = {
            "restaurants": json.loads(VALID_JSON_RESPONSE)["recommendations"],
            "summary": "Test",
        }
        result = _validate_response(data)
        assert len(result.recommendations) == 2

    def test_missing_recommendations_key_raises(self):
        with pytest.raises(ValueError, match="missing"):
            _validate_response({"foo": "bar"})

    def test_summary_defaults_to_empty(self):
        data = {
            "recommendations": json.loads(VALID_JSON_RESPONSE)[
                "recommendations"
            ]
        }
        result = _validate_response(data)
        assert result.summary == ""


# ──────────────────────────────────────────────
# RecommendationService — constructor
# ──────────────────────────────────────────────


class TestServiceInit:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(RecommendationError, match="GROQ_API_KEY"):
            RecommendationService()

    @patch("src.services.recommendation.Groq")
    def test_accepts_explicit_key(self, mock_groq):
        svc = RecommendationService(api_key="test-key-123")
        mock_groq.assert_called_once_with(api_key="test-key-123")
        assert svc.primary_model == "llama-3.3-70b-versatile"


# ──────────────────────────────────────────────
# RecommendationService — get_recommendations
# ──────────────────────────────────────────────


class TestGetRecommendations:
    @patch("src.services.recommendation.Groq")
    def test_success_on_first_try(
        self, mock_groq_cls, sample_prefs, sample_candidates
    ):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = _mock_completion(
            VALID_JSON_RESPONSE
        )

        svc = RecommendationService(api_key="key")
        result = svc.get_recommendations(sample_prefs, sample_candidates)

        assert isinstance(result, RecommendationResponse)
        assert len(result.recommendations) == 2
        assert result.recommendations[0].restaurant_name == "Tasty Bites"

        # Only one API call should have been made
        assert mock_client.chat.completions.create.call_count == 1

    @patch("src.services.recommendation.time.sleep")
    @patch("src.services.recommendation.Groq")
    def test_retry_on_api_error(
        self, mock_groq_cls, mock_sleep, sample_prefs, sample_candidates
    ):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Fail twice, succeed on third attempt
        mock_client.chat.completions.create.side_effect = [
            Exception("rate limited"),
            Exception("server error"),
            _mock_completion(VALID_JSON_RESPONSE),
        ]

        svc = RecommendationService(api_key="key")
        result = svc.get_recommendations(sample_prefs, sample_candidates)

        assert isinstance(result, RecommendationResponse)
        assert mock_client.chat.completions.create.call_count == 3
        # Two backoff sleeps (after attempt 1 and attempt 2)
        assert mock_sleep.call_count == 2

    @patch("src.services.recommendation.time.sleep")
    @patch("src.services.recommendation.Groq")
    def test_fallback_to_second_model(
        self, mock_groq_cls, mock_sleep, sample_prefs, sample_candidates
    ):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Primary model fails all 3 attempts, fallback succeeds on first
        mock_client.chat.completions.create.side_effect = [
            Exception("error 1"),
            Exception("error 2"),
            Exception("error 3"),
            _mock_completion(VALID_JSON_RESPONSE),
        ]

        svc = RecommendationService(api_key="key")
        result = svc.get_recommendations(sample_prefs, sample_candidates)

        assert isinstance(result, RecommendationResponse)
        # 3 failed (primary) + 1 success (fallback) = 4
        assert mock_client.chat.completions.create.call_count == 4

        # Verify the fallback model was used
        last_call_kwargs = (
            mock_client.chat.completions.create.call_args_list[-1]
        )
        assert last_call_kwargs.kwargs["model"] == "mixtral-8x7b-32768"

    @patch("src.services.recommendation.time.sleep")
    @patch("src.services.recommendation.Groq")
    def test_raises_after_all_attempts_exhausted(
        self, mock_groq_cls, mock_sleep, sample_prefs, sample_candidates
    ):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "always fails"
        )

        svc = RecommendationService(api_key="key")
        with pytest.raises(RecommendationError, match="All LLM attempts"):
            svc.get_recommendations(sample_prefs, sample_candidates)

        # 3 retries × 2 models = 6 total calls
        assert mock_client.chat.completions.create.call_count == 6

    @patch("src.services.recommendation.time.sleep")
    @patch("src.services.recommendation.Groq")
    def test_retry_on_json_parse_error(
        self, mock_groq_cls, mock_sleep, sample_prefs, sample_candidates
    ):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # First call returns garbage, second succeeds
        mock_client.chat.completions.create.side_effect = [
            _mock_completion("not valid json"),
            _mock_completion(VALID_JSON_RESPONSE),
        ]

        svc = RecommendationService(api_key="key")
        result = svc.get_recommendations(sample_prefs, sample_candidates)

        assert isinstance(result, RecommendationResponse)
        assert mock_client.chat.completions.create.call_count == 2

    @patch("src.services.recommendation.Groq")
    def test_empty_response_triggers_retry(
        self, mock_groq_cls, sample_prefs, sample_candidates
    ):
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        empty_choice = MagicMock()
        empty_choice.message.content = ""
        empty_completion = MagicMock()
        empty_completion.choices = [empty_choice]

        mock_client.chat.completions.create.side_effect = [
            empty_completion,
            _mock_completion(VALID_JSON_RESPONSE),
        ]

        svc = RecommendationService(api_key="key")
        result = svc.get_recommendations(sample_prefs, sample_candidates)
        assert isinstance(result, RecommendationResponse)


# ──────────────────────────────────────────────
# Exponential backoff timing
# ──────────────────────────────────────────────


class TestBackoffTiming:
    @patch("src.services.recommendation.time.sleep")
    @patch("src.services.recommendation.Groq")
    def test_backoff_durations(
        self, mock_groq_cls, mock_sleep, sample_prefs, sample_candidates
    ):
        """Verify backoff is 1s, 2s for the 3-retry sequence."""
        mock_client = MagicMock()
        mock_groq_cls.return_value = mock_client

        # Fail all 3 attempts on primary, succeed on fallback first try
        mock_client.chat.completions.create.side_effect = [
            Exception("e1"),
            Exception("e2"),
            Exception("e3"),
            _mock_completion(VALID_JSON_RESPONSE),
        ]

        svc = RecommendationService(api_key="key")
        svc.get_recommendations(sample_prefs, sample_candidates)

        # After attempt 1: sleep(1), after attempt 2: sleep(2)
        # Attempt 3 is the last for primary, no sleep after it
        sleep_args = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_args == [1, 2]


# ──────────────────────────────────────────────
# _parse_response static method
# ──────────────────────────────────────────────


class TestParseResponse:
    @patch("src.services.recommendation.Groq")
    def test_parse_valid(self, mock_groq_cls):
        svc = RecommendationService(api_key="key")
        result = svc._parse_response(VALID_JSON_RESPONSE)
        assert isinstance(result, RecommendationResponse)
        assert len(result.recommendations) == 2

    @patch("src.services.recommendation.Groq")
    def test_parse_fenced_json(self, mock_groq_cls):
        svc = RecommendationService(api_key="key")
        fenced = f"```json\n{VALID_JSON_RESPONSE}\n```"
        result = svc._parse_response(fenced)
        assert len(result.recommendations) == 2
