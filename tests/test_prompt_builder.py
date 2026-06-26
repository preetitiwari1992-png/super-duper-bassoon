"""
Unit tests for ``src.services.prompt_builder``.

Covers
------
- System prompt generation
- User prompt population (all fields)
- Budget range formatting
- Restaurant table formatting (normal, empty, missing columns)
- Convenience ``build_messages`` wrapper
"""

import pandas as pd
import pytest

from src.config import BUDGET_MAP, TOP_K_RESULTS
from src.models.schemas import UserPreferences
from src.services.prompt_builder import (
    OUTPUT_SCHEMA,
    build_messages,
    build_system_prompt,
    build_user_prompt,
    _format_budget_range,
    _format_restaurant_table,
)


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def sample_prefs() -> UserPreferences:
    """Standard user preferences for most tests."""
    return UserPreferences(
        location="Bangalore",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_prefs="family-friendly, outdoor seating",
    )


@pytest.fixture
def sample_prefs_minimal() -> UserPreferences:
    """Minimal preferences — only location, everything else defaults."""
    return UserPreferences(location="Delhi")


@pytest.fixture
def sample_candidates() -> pd.DataFrame:
    """Small DataFrame mimicking filtered restaurant candidates."""
    return pd.DataFrame(
        {
            "restaurant_name": ["Pizza Place", "Pasta House"],
            "cuisines": ["Italian, Pizza", "Italian, Pasta"],
            "aggregate_rating": [4.5, 4.2],
            "average_cost": [800.0, 1200.0],
            "votes": [300, 150],
            "has_online_delivery": [True, False],
            "has_table_booking": [False, True],
            "city": ["Bangalore", "Bangalore"],
            "location": ["Koramangala", "Indiranagar"],
        }
    )


@pytest.fixture
def empty_candidates() -> pd.DataFrame:
    """Empty DataFrame with the expected columns."""
    return pd.DataFrame(
        columns=[
            "restaurant_name",
            "cuisines",
            "aggregate_rating",
            "average_cost",
            "votes",
            "has_online_delivery",
            "has_table_booking",
        ]
    )


# ──────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────


class TestBuildSystemPrompt:
    def test_returns_non_empty_string(self):
        prompt = build_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_contains_key_instructions(self):
        prompt = build_system_prompt()
        assert "restaurant recommendation" in prompt.lower()
        assert "valid JSON" in prompt
        assert str(TOP_K_RESULTS) in prompt

    def test_mentions_ranking(self):
        prompt = build_system_prompt()
        assert "Rank" in prompt or "rank" in prompt


# ──────────────────────────────────────────────
# Budget range formatting
# ──────────────────────────────────────────────


class TestFormatBudgetRange:
    def test_low(self):
        result = _format_budget_range("low")
        assert "0" in result
        assert "500" in result

    def test_medium(self):
        result = _format_budget_range("medium")
        assert "500" in result
        assert "1,500" in result or "1500" in result

    def test_high_shows_plus(self):
        result = _format_budget_range("high")
        assert "+" in result
        assert "1,500" in result or "1500" in result

    def test_unknown_falls_back_to_medium(self):
        result = _format_budget_range("unknown_tier")
        expected = _format_budget_range("medium")
        assert result == expected


# ──────────────────────────────────────────────
# Restaurant table formatting
# ──────────────────────────────────────────────


class TestFormatRestaurantTable:
    def test_empty_df(self, empty_candidates):
        table = _format_restaurant_table(empty_candidates)
        assert "No restaurants" in table

    def test_has_header(self, sample_candidates):
        table = _format_restaurant_table(sample_candidates)
        assert "Name" in table
        assert "Cuisines" in table
        assert "Rating" in table

    def test_contains_restaurant_names(self, sample_candidates):
        table = _format_restaurant_table(sample_candidates)
        assert "Pizza Place" in table
        assert "Pasta House" in table

    def test_row_count_matches(self, sample_candidates):
        table = _format_restaurant_table(sample_candidates)
        # header + separator + 2 data rows = 4 lines
        lines = [l for l in table.split("\n") if l.strip()]
        assert len(lines) == 4

    def test_delivery_and_booking_columns(self, sample_candidates):
        table = _format_restaurant_table(sample_candidates)
        assert "Yes" in table
        assert "No" in table


# ──────────────────────────────────────────────
# User prompt
# ──────────────────────────────────────────────


class TestBuildUserPrompt:
    def test_contains_user_preferences(self, sample_prefs, sample_candidates):
        prompt = build_user_prompt(sample_prefs, sample_candidates)
        assert "Bangalore" in prompt
        assert "medium" in prompt
        assert "Italian" in prompt
        assert "4.0" in prompt
        assert "family-friendly" in prompt

    def test_contains_restaurant_data(self, sample_prefs, sample_candidates):
        prompt = build_user_prompt(sample_prefs, sample_candidates)
        assert "Pizza Place" in prompt
        assert "Pasta House" in prompt

    def test_contains_output_schema(self, sample_prefs, sample_candidates):
        prompt = build_user_prompt(sample_prefs, sample_candidates)
        assert "recommendations" in prompt
        assert "explanation" in prompt

    def test_cuisine_none_shows_any(
        self, sample_prefs_minimal, sample_candidates
    ):
        prompt = build_user_prompt(sample_prefs_minimal, sample_candidates)
        assert "Any" in prompt

    def test_additional_prefs_none_shows_none(
        self, sample_prefs_minimal, sample_candidates
    ):
        prompt = build_user_prompt(sample_prefs_minimal, sample_candidates)
        assert "None" in prompt

    def test_top_k_in_instructions(self, sample_prefs, sample_candidates):
        prompt = build_user_prompt(sample_prefs, sample_candidates)
        assert str(TOP_K_RESULTS) in prompt

    def test_empty_candidates_handled(self, sample_prefs, empty_candidates):
        prompt = build_user_prompt(sample_prefs, empty_candidates)
        assert "No restaurants" in prompt


# ──────────────────────────────────────────────
# build_messages convenience wrapper
# ──────────────────────────────────────────────


class TestBuildMessages:
    def test_returns_two_messages(self, sample_prefs, sample_candidates):
        messages = build_messages(sample_prefs, sample_candidates)
        assert isinstance(messages, list)
        assert len(messages) == 2

    def test_roles_are_correct(self, sample_prefs, sample_candidates):
        messages = build_messages(sample_prefs, sample_candidates)
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_content_matches(self, sample_prefs, sample_candidates):
        messages = build_messages(sample_prefs, sample_candidates)
        assert messages[0]["content"] == build_system_prompt()

    def test_user_content_matches(self, sample_prefs, sample_candidates):
        messages = build_messages(sample_prefs, sample_candidates)
        expected = build_user_prompt(sample_prefs, sample_candidates)
        assert messages[1]["content"] == expected
