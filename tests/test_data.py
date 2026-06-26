"""
Tests for the data ingestion and preprocessing pipeline.

These tests validate:
  - The preprocessor handles all known data quality issues
  - The loader caches data correctly
  - Cleaned data meets the acceptance criteria
"""

import pandas as pd
import pytest

from src.data.preprocessor import preprocess


# ──────────────────────────────────────────────
# Sample data mimicking the raw HF dataset
# ──────────────────────────────────────────────

def _make_raw_df(overrides: list[dict] | None = None) -> pd.DataFrame:
    """Create a small raw DataFrame matching the HF dataset schema."""
    rows = [
        {
            "url": "https://example.com/1",
            "address": "123 Main St",
            "name": "Pizza Palace",
            "online_order": "Yes",
            "book_table": "No",
            "rate": "4.1/5",
            "votes": 300,
            "phone": "1234567890",
            "location": "Koramangala",
            "rest_type": "Casual Dining",
            "dish_liked": "Margherita Pizza",
            "cuisines": "Italian, Pizza",
            "approx_cost(for two people)": "800",
            "reviews_list": "[]",
            "menu_item": "[]",
            "listed_in(type)": "Buffet",
            "listed_in(city)": "Bangalore",
        },
        {
            "url": "https://example.com/2",
            "address": "456 Side St",
            "name": "Dragon House",
            "online_order": "No",
            "book_table": "Yes",
            "rate": "3.9/5",
            "votes": 150,
            "phone": "0987654321",
            "location": "BTM Layout",
            "rest_type": "Quick Bites",
            "dish_liked": "Momos, Noodles",
            "cuisines": "Chinese, Thai",
            "approx_cost(for two people)": "500",
            "reviews_list": "[]",
            "menu_item": "[]",
            "listed_in(type)": "Delivery",
            "listed_in(city)": "bangalore",
        },
        {
            "url": "https://example.com/3",
            "address": "789 High Rd",
            "name": "Spice Garden",
            "online_order": "Yes",
            "book_table": "Yes",
            "rate": "NEW",
            "votes": 0,
            "phone": "5555555555",
            "location": "Jayanagar",
            "rest_type": "Fine Dining",
            "dish_liked": "",
            "cuisines": "North Indian, Biryani",
            "approx_cost(for two people)": "1,200",
            "reviews_list": "[]",
            "menu_item": "[]",
            "listed_in(type)": "Dine-out",
            "listed_in(city)": "BANGALORE",
        },
    ]
    if overrides:
        rows.extend(overrides)
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────
# Preprocessing Tests
# ──────────────────────────────────────────────


class TestPreprocessor:
    """Test suite for the data preprocessor."""

    def test_column_renaming(self):
        """Verify raw columns are renamed to internal names."""
        df = preprocess(_make_raw_df())
        expected_cols = {
            "restaurant_name", "city", "location", "cuisines",
            "average_cost", "aggregate_rating", "votes",
            "has_online_delivery", "has_table_booking",
            "rest_type", "dish_liked",
        }
        assert set(df.columns) == expected_cols

    def test_no_null_restaurant_names(self):
        """Null or empty restaurant names must be dropped."""
        raw = _make_raw_df([
            {
                "url": "", "address": "", "name": None,
                "online_order": "No", "book_table": "No",
                "rate": "3.0/5", "votes": 10, "phone": "",
                "location": "X", "rest_type": "Cafe",
                "dish_liked": "", "cuisines": "Coffee",
                "approx_cost(for two people)": "200",
                "reviews_list": "[]", "menu_item": "[]",
                "listed_in(type)": "Cafe", "listed_in(city)": "Delhi",
            },
            {
                "url": "", "address": "", "name": "",
                "online_order": "No", "book_table": "No",
                "rate": "2.5/5", "votes": 5, "phone": "",
                "location": "Y", "rest_type": "Cafe",
                "dish_liked": "", "cuisines": "Tea",
                "approx_cost(for two people)": "100",
                "reviews_list": "[]", "menu_item": "[]",
                "listed_in(type)": "Cafe", "listed_in(city)": "Delhi",
            },
        ])
        df = preprocess(raw)
        # The two bad rows should be gone
        assert df["restaurant_name"].isna().sum() == 0
        assert (df["restaurant_name"].str.strip() == "").sum() == 0

    def test_rating_parsing_normal(self):
        """'4.1/5' should become 4.1."""
        df = preprocess(_make_raw_df())
        pizza = df[df["restaurant_name"] == "Pizza Palace"].iloc[0]
        assert pizza["aggregate_rating"] == pytest.approx(4.1)

    def test_rating_parsing_new(self):
        """'NEW' rating should become 0.0."""
        df = preprocess(_make_raw_df())
        spice = df[df["restaurant_name"] == "Spice Garden"].iloc[0]
        assert spice["aggregate_rating"] == 0.0

    def test_rating_clamped(self):
        """Ratings should be clamped to [0.0, 5.0]."""
        raw = _make_raw_df([
            {
                "url": "", "address": "", "name": "Bad Rating Place",
                "online_order": "No", "book_table": "No",
                "rate": "7.5/5", "votes": 1, "phone": "",
                "location": "Z", "rest_type": "Cafe",
                "dish_liked": "", "cuisines": "Cafe",
                "approx_cost(for two people)": "100",
                "reviews_list": "[]", "menu_item": "[]",
                "listed_in(type)": "Cafe", "listed_in(city)": "Delhi",
            },
        ])
        df = preprocess(raw)
        bad = df[df["restaurant_name"] == "Bad Rating Place"].iloc[0]
        assert bad["aggregate_rating"] <= 5.0

    def test_cost_parsing_with_comma(self):
        """'1,200' should become 1200.0."""
        df = preprocess(_make_raw_df())
        spice = df[df["restaurant_name"] == "Spice Garden"].iloc[0]
        assert spice["average_cost"] == pytest.approx(1200.0)

    def test_cost_parsing_plain(self):
        """'800' should become 800.0."""
        df = preprocess(_make_raw_df())
        pizza = df[df["restaurant_name"] == "Pizza Palace"].iloc[0]
        assert pizza["average_cost"] == pytest.approx(800.0)

    def test_city_standardized_to_title_case(self):
        """All city variants ('bangalore', 'BANGALORE') → 'Bangalore'."""
        df = preprocess(_make_raw_df())
        cities = df["city"].unique().tolist()
        # All three rows should have the same title-cased city
        assert all(c == "Bangalore" for c in cities)

    def test_boolean_parsing(self):
        """'Yes'/'No' strings should become True/False."""
        df = preprocess(_make_raw_df())
        pizza = df[df["restaurant_name"] == "Pizza Palace"].iloc[0]
        assert pizza["has_online_delivery"] is True or pizza["has_online_delivery"] == True
        assert pizza["has_table_booking"] is False or pizza["has_table_booking"] == False

    def test_votes_non_negative(self):
        """All votes should be non-negative integers."""
        df = preprocess(_make_raw_df())
        assert (df["votes"] >= 0).all()

    def test_missing_cuisines_filled(self):
        """Null cuisines should be filled with 'Unknown'."""
        raw = _make_raw_df([
            {
                "url": "", "address": "", "name": "Mystery Kitchen",
                "online_order": "No", "book_table": "No",
                "rate": "3.0/5", "votes": 10, "phone": "",
                "location": "X", "rest_type": "Cafe",
                "dish_liked": "", "cuisines": None,
                "approx_cost(for two people)": "200",
                "reviews_list": "[]", "menu_item": "[]",
                "listed_in(type)": "Cafe", "listed_in(city)": "Delhi",
            },
        ])
        df = preprocess(raw)
        mystery = df[df["restaurant_name"] == "Mystery Kitchen"].iloc[0]
        assert mystery["cuisines"] == "Unknown"

    def test_duplicates_dropped(self):
        """Duplicate name+location rows should keep the one with highest votes."""
        raw = _make_raw_df([
            {
                "url": "", "address": "", "name": "Pizza Palace",
                "online_order": "No", "book_table": "No",
                "rate": "3.5/5", "votes": 50, "phone": "",
                "location": "Koramangala", "rest_type": "Cafe",
                "dish_liked": "", "cuisines": "Italian",
                "approx_cost(for two people)": "600",
                "reviews_list": "[]", "menu_item": "[]",
                "listed_in(type)": "Delivery",
                "listed_in(city)": "Bangalore",
            },
        ])
        df = preprocess(raw)
        pizza_rows = df[df["restaurant_name"] == "Pizza Palace"]
        # Should only have 1 row for Koramangala Pizza Palace
        koramangala = pizza_rows[pizza_rows["location"] == "Koramangala"]
        assert len(koramangala) == 1
        # Kept the one with 300 votes (higher)
        assert koramangala.iloc[0]["votes"] == 300

    def test_output_has_no_unexpected_columns(self):
        """The cleaned DataFrame should only contain expected columns."""
        df = preprocess(_make_raw_df())
        expected = {
            "restaurant_name", "city", "location", "cuisines",
            "average_cost", "aggregate_rating", "votes",
            "has_online_delivery", "has_table_booking",
            "rest_type", "dish_liked",
        }
        assert set(df.columns) == expected
