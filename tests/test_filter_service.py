"""
Unit tests for the filter service.

Covers:
  - Location filtering (city and neighbourhood)
  - Budget-range mapping and boundary values
  - Cuisine partial / case-insensitive matching
  - Minimum rating filtering
  - MAX_CANDIDATES cap
  - Progressive fallback strategy
  - Edge cases (empty dataset, no matches, single result)
"""

import pandas as pd
import pytest

from src.models.schemas import UserPreferences
from src.services.filter_service import (
    FilterResult,
    filter_restaurants,
    _filter_by_budget,
    _filter_by_cuisine,
    _filter_by_location,
    _filter_by_min_rating,
    _next_budget_tier,
)


# ──────────────────────────────────────────────
# Fixtures — reusable sample data
# ──────────────────────────────────────────────


def _sample_df() -> pd.DataFrame:
    """Return a small cleaned DataFrame with known values."""
    rows = [
        # ── Bangalore / Koramangala ──
        {
            "restaurant_name": "Pizza Palace",
            "city": "Bangalore",
            "location": "Koramangala",
            "cuisines": "Italian, Pizza",
            "average_cost": 800.0,
            "aggregate_rating": 4.5,
            "votes": 300,
            "has_online_delivery": True,
            "has_table_booking": False,
            "rest_type": "Casual Dining",
            "dish_liked": "Margherita",
        },
        {
            "restaurant_name": "Dragon House",
            "city": "Bangalore",
            "location": "BTM Layout",
            "cuisines": "Chinese, Thai",
            "average_cost": 500.0,
            "aggregate_rating": 3.9,
            "votes": 150,
            "has_online_delivery": False,
            "has_table_booking": True,
            "rest_type": "Quick Bites",
            "dish_liked": "Momos",
        },
        {
            "restaurant_name": "Spice Garden",
            "city": "Bangalore",
            "location": "Jayanagar",
            "cuisines": "North Indian, Biryani",
            "average_cost": 1200.0,
            "aggregate_rating": 4.2,
            "votes": 500,
            "has_online_delivery": True,
            "has_table_booking": True,
            "rest_type": "Fine Dining",
            "dish_liked": "Biryani",
        },
        {
            "restaurant_name": "Chai Point",
            "city": "Bangalore",
            "location": "Koramangala",
            "cuisines": "Cafe, Beverages",
            "average_cost": 200.0,
            "aggregate_rating": 3.5,
            "votes": 80,
            "has_online_delivery": True,
            "has_table_booking": False,
            "rest_type": "Cafe",
            "dish_liked": "Chai",
        },
        {
            "restaurant_name": "Luxury Grill",
            "city": "Bangalore",
            "location": "Indiranagar",
            "cuisines": "Continental, Italian",
            "average_cost": 2500.0,
            "aggregate_rating": 4.7,
            "votes": 900,
            "has_online_delivery": False,
            "has_table_booking": True,
            "rest_type": "Fine Dining",
            "dish_liked": "Steak",
        },
        # ── Delhi ──
        {
            "restaurant_name": "Delhi Darbar",
            "city": "Delhi",
            "location": "Connaught Place",
            "cuisines": "Mughlai, North Indian",
            "average_cost": 900.0,
            "aggregate_rating": 4.0,
            "votes": 200,
            "has_online_delivery": True,
            "has_table_booking": False,
            "rest_type": "Casual Dining",
            "dish_liked": "Kebab",
        },
        {
            "restaurant_name": "Street Bites",
            "city": "Delhi",
            "location": "Chandni Chowk",
            "cuisines": "Street Food, North Indian",
            "average_cost": 150.0,
            "aggregate_rating": 4.3,
            "votes": 600,
            "has_online_delivery": False,
            "has_table_booking": False,
            "rest_type": "Quick Bites",
            "dish_liked": "Chaat",
        },
    ]
    return pd.DataFrame(rows)


def _prefs(**kwargs) -> UserPreferences:
    """Shortcut to create UserPreferences with defaults + overrides."""
    defaults = {
        "location": "Bangalore",
        "budget": "medium",
        "cuisine": None,
        "min_rating": 3.5,
        "additional_prefs": None,
    }
    defaults.update(kwargs)
    return UserPreferences(**defaults)


# ──────────────────────────────────────────────
# Individual filter function tests
# ──────────────────────────────────────────────


class TestLocationFilter:
    """Tests for _filter_by_location."""

    def test_match_by_city(self):
        df = _sample_df()
        result = _filter_by_location(df, "Bangalore")
        assert len(result) == 5  # all Bangalore rows

    def test_match_by_neighbourhood(self):
        df = _sample_df()
        result = _filter_by_location(df, "Koramangala")
        assert len(result) == 2  # Pizza Palace + Chai Point

    def test_case_insensitive(self):
        df = _sample_df()
        result = _filter_by_location(df, "BANGALORE")
        assert len(result) == 5

    def test_no_match(self):
        df = _sample_df()
        result = _filter_by_location(df, "Mumbai")
        assert len(result) == 0

    def test_whitespace_stripped(self):
        df = _sample_df()
        result = _filter_by_location(df, "  Bangalore  ")
        assert len(result) == 5


class TestBudgetFilter:
    """Tests for _filter_by_budget."""

    def test_low_budget(self):
        df = _sample_df()
        result = _filter_by_budget(df, "low")
        # cost 0–500: Dragon House (500), Chai Point (200), Street Bites (150)
        assert len(result) == 3

    def test_medium_budget(self):
        df = _sample_df()
        result = _filter_by_budget(df, "medium")
        # cost 500–1500: Pizza Palace (800), Dragon House (500), Spice Garden (1200), Delhi Darbar (900)
        assert len(result) == 4

    def test_high_budget(self):
        df = _sample_df()
        result = _filter_by_budget(df, "high")
        # cost 1500+: Luxury Grill (2500)
        assert len(result) == 1

    def test_boundary_500_included_in_low(self):
        """₹500 is the upper bound of 'low', should be included."""
        df = _sample_df()
        result = _filter_by_budget(df, "low")
        assert "Dragon House" in result["restaurant_name"].values

    def test_boundary_500_included_in_medium(self):
        """₹500 is the lower bound of 'medium', should be included."""
        df = _sample_df()
        result = _filter_by_budget(df, "medium")
        assert "Dragon House" in result["restaurant_name"].values


class TestCuisineFilter:
    """Tests for _filter_by_cuisine."""

    def test_exact_cuisine(self):
        df = _sample_df()
        result = _filter_by_cuisine(df, "Italian")
        names = result["restaurant_name"].tolist()
        assert "Pizza Palace" in names
        assert "Luxury Grill" in names

    def test_case_insensitive(self):
        df = _sample_df()
        result = _filter_by_cuisine(df, "italian")
        assert len(result) == 2

    def test_partial_match(self):
        """'North Indian' should match restaurants with that substring."""
        df = _sample_df()
        result = _filter_by_cuisine(df, "North Indian")
        names = result["restaurant_name"].tolist()
        assert "Spice Garden" in names
        assert "Delhi Darbar" in names
        assert "Street Bites" in names

    def test_no_match(self):
        df = _sample_df()
        result = _filter_by_cuisine(df, "Japanese")
        assert len(result) == 0


class TestRatingFilter:
    """Tests for _filter_by_min_rating."""

    def test_filters_correctly(self):
        df = _sample_df()
        result = _filter_by_min_rating(df, 4.0)
        assert all(result["aggregate_rating"] >= 4.0)

    def test_zero_rating_includes_all(self):
        df = _sample_df()
        result = _filter_by_min_rating(df, 0.0)
        assert len(result) == len(df)

    def test_high_rating_few_results(self):
        df = _sample_df()
        result = _filter_by_min_rating(df, 4.5)
        names = result["restaurant_name"].tolist()
        assert "Pizza Palace" in names   # 4.5
        assert "Luxury Grill" in names   # 4.7


# ──────────────────────────────────────────────
# Budget tier helper
# ──────────────────────────────────────────────


class TestNextBudgetTier:

    def test_low_to_medium(self):
        assert _next_budget_tier("low") == "medium"

    def test_medium_to_high(self):
        assert _next_budget_tier("medium") == "high"

    def test_high_returns_none(self):
        assert _next_budget_tier("high") is None

    def test_invalid_returns_none(self):
        assert _next_budget_tier("ultra") is None


# ──────────────────────────────────────────────
# Full pipeline tests
# ──────────────────────────────────────────────


class TestFilterRestaurants:
    """Tests for the main filter_restaurants function."""

    def test_happy_path(self):
        """Standard query with matches."""
        df = _sample_df()
        result = filter_restaurants(df, _prefs(location="Bangalore", budget="medium", min_rating=3.5))
        assert isinstance(result, FilterResult)
        assert len(result.candidates) > 0
        assert result.total_matches > 0
        assert not result.fallback_applied

    def test_location_not_found(self):
        """Unknown location returns empty with helpful message."""
        df = _sample_df()
        result = filter_restaurants(df, _prefs(location="Mumbai"))
        assert len(result.candidates) == 0
        assert "Mumbai" in result.fallback_message

    def test_cuisine_filter_applied(self):
        """When cuisine is provided, results should match it."""
        df = _sample_df()
        result = filter_restaurants(
            df, _prefs(location="Bangalore", cuisine="Italian", budget="medium")
        )
        assert not result.candidates.empty
        for _, row in result.candidates.iterrows():
            assert "italian" in row["cuisines"].lower()

    def test_results_sorted_by_rating_desc(self):
        """Candidates should be sorted by rating, highest first."""
        df = _sample_df()
        result = filter_restaurants(df, _prefs(location="Bangalore", min_rating=0.0))
        ratings = result.candidates["aggregate_rating"].tolist()
        assert ratings == sorted(ratings, reverse=True)

    def test_max_candidates_cap(self):
        """Even with many matches, cap at MAX_CANDIDATES (20)."""
        # Create a large dataset
        rows = []
        for i in range(50):
            rows.append({
                "restaurant_name": f"Restaurant {i}",
                "city": "Bangalore",
                "location": "Koramangala",
                "cuisines": "Indian",
                "average_cost": 800.0,
                "aggregate_rating": 4.0,
                "votes": i,
                "has_online_delivery": True,
                "has_table_booking": False,
                "rest_type": "Cafe",
                "dish_liked": "",
            })
        df = pd.DataFrame(rows)
        result = filter_restaurants(df, _prefs(location="Bangalore", min_rating=0.0))
        assert len(result.candidates) == 20
        assert result.total_matches == 50

    def test_single_result(self):
        """A single match is still returned correctly."""
        df = _sample_df()
        result = filter_restaurants(
            df, _prefs(location="Bangalore", budget="high", min_rating=4.0)
        )
        assert len(result.candidates) == 1
        assert result.candidates.iloc[0]["restaurant_name"] == "Luxury Grill"


# ──────────────────────────────────────────────
# Fallback tests
# ──────────────────────────────────────────────


class TestFallback:
    """Tests for progressive fallback behaviour."""

    def test_fallback_drops_cuisine(self):
        """When cuisine has no matches, fallback should drop it."""
        df = _sample_df()
        result = filter_restaurants(
            df, _prefs(
                location="Bangalore",
                cuisine="Japanese",      # no Japanese in sample data
                budget="medium",
                min_rating=3.5,
            )
        )
        assert result.fallback_applied
        assert len(result.candidates) > 0
        assert "cuisine" in result.fallback_message.lower()

    def test_fallback_lowers_rating(self):
        """When rating is too high, fallback should lower it."""
        df = _sample_df()
        result = filter_restaurants(
            df, _prefs(
                location="Delhi",
                budget="low",
                min_rating=5.0,          # nobody has 5.0
            )
        )
        assert result.fallback_applied
        assert len(result.candidates) > 0
        assert "rating" in result.fallback_message.lower()

    def test_fallback_expands_budget(self):
        """When budget is too restrictive, fallback should expand it."""
        df = _sample_df()
        # All Delhi restaurants: Darbar (900, medium), Street Bites (150, low)
        # With high budget (1500+) and no cuisine and rating 0 → 0 results
        # Fallback should expand or show all
        result = filter_restaurants(
            df, _prefs(
                location="Delhi",
                budget="high",
                min_rating=0.0,
            )
        )
        # Should fall back and find something
        assert result.fallback_applied
        assert len(result.candidates) > 0

    def test_empty_dataset(self):
        """Empty DataFrame → empty result, no crash."""
        df = pd.DataFrame(columns=_sample_df().columns)
        result = filter_restaurants(df, _prefs(location="Bangalore"))
        assert len(result.candidates) == 0

    def test_neighbourhood_search(self):
        """Searching by neighbourhood should work as well as city."""
        df = _sample_df()
        result = filter_restaurants(
            df, _prefs(location="Koramangala", budget="medium", min_rating=0.0)
        )
        assert len(result.candidates) > 0
        locations = result.candidates["location"].str.lower().tolist()
        assert all(loc == "koramangala" for loc in locations)
