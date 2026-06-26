"""
Data preprocessor — cleans and normalizes the raw Zomato dataset.

Handles the real Hugging Face dataset schema where columns are:
  url, address, name, online_order, book_table, rate, votes, phone,
  location, rest_type, dish_liked, cuisines, approx_cost(for two people),
  reviews_list, menu_item, listed_in(type), listed_in(city)

After preprocessing the DataFrame is standardized to:
  restaurant_name, city, location, cuisines, average_cost,
  aggregate_rating, votes, has_online_delivery, has_table_booking,
  rest_type, dish_liked
"""

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Column Mapping: raw HF name → internal name
# ──────────────────────────────────────────────
COLUMN_RENAME_MAP = {
    "name": "restaurant_name",
    "online_order": "has_online_delivery",
    "book_table": "has_table_booking",
    "rate": "aggregate_rating",
    "approx_cost(for two people)": "average_cost",
    "listed_in(city)": "city",
    "listed_in(type)": "listed_in_type",
}

# Columns to keep after renaming
COLUMNS_TO_KEEP = [
    "restaurant_name",
    "city",
    "location",
    "cuisines",
    "average_cost",
    "aggregate_rating",
    "votes",
    "has_online_delivery",
    "has_table_booking",
    "rest_type",
    "dish_liked",
]


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master preprocessing pipeline.

    Applies all cleaning steps in order and returns a tidy DataFrame
    ready for filtering and prompt building.
    """
    logger.info("Starting preprocessing — %d raw rows", len(df))

    df = _rename_columns(df)
    df = _select_columns(df)
    df = _drop_null_names(df)
    df = _clean_cuisines(df)
    df = _parse_rating(df)
    df = _parse_cost(df)
    df = _standardize_city(df)
    df = _standardize_location(df)
    df = _parse_boolean_fields(df)
    df = _parse_votes(df)
    df = _clean_rest_type(df)
    df = _clean_dish_liked(df)
    df = _drop_duplicates(df)
    df = df.reset_index(drop=True)

    logger.info("Preprocessing complete — %d clean rows", len(df))
    return df


# ──────────────────────────────────────────────
# Individual Cleaning Steps
# ──────────────────────────────────────────────


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw HF columns to standardized internal names."""
    return df.rename(columns=COLUMN_RENAME_MAP)


def _select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns we need; ignore extras gracefully."""
    available = [col for col in COLUMNS_TO_KEEP if col in df.columns]
    missing = set(COLUMNS_TO_KEEP) - set(available)
    if missing:
        logger.warning("Missing columns in dataset (will be filled): %s", missing)
        for col in missing:
            df[col] = None
    return df[COLUMNS_TO_KEEP].copy()


def _drop_null_names(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where restaurant_name is null or empty."""
    before = len(df)
    df = df.dropna(subset=["restaurant_name"])
    df = df[df["restaurant_name"].str.strip() != ""]
    logger.info("Dropped %d rows with null/empty restaurant_name", before - len(df))
    return df


def _clean_cuisines(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing cuisines with 'Unknown' and strip whitespace."""
    df["cuisines"] = df["cuisines"].fillna("Unknown")
    df["cuisines"] = df["cuisines"].astype(str).str.strip()
    return df


def _parse_rating(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the 'rate' field which comes as strings like '4.1/5', 'NEW', '-'.
    Convert to float in range [0.0, 5.0].
    """
    def _extract_rating(value):
        if pd.isna(value):
            return 0.0
        value = str(value).strip()
        # Handle special values
        if value.upper() in ("NEW", "-", "", "NONE"):
            return 0.0
        # Handle "X/5" format
        match = re.match(r"^([\d.]+)\s*/\s*5", value)
        if match:
            try:
                rating = float(match.group(1))
                return max(0.0, min(5.0, rating))
            except ValueError:
                return 0.0
        # Try plain numeric
        try:
            rating = float(value)
            return max(0.0, min(5.0, rating))
        except ValueError:
            return 0.0

    df["aggregate_rating"] = df["aggregate_rating"].apply(_extract_rating)
    return df


def _parse_cost(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse 'approx_cost(for two people)' which can be strings like '800',
    '1,200', or contain currency symbols. Convert to float.
    """
    def _extract_cost(value):
        if pd.isna(value):
            return 0.0
        value = str(value).strip()
        # Remove everything except digits, dots, and commas
        cleaned = re.sub(r"[^\d.,]", "", value)
        # Remove commas (thousands separator)
        cleaned = cleaned.replace(",", "")
        try:
            return max(0.0, float(cleaned))
        except ValueError:
            return 0.0

    df["average_cost"] = df["average_cost"].apply(_extract_cost)
    return df


def _standardize_city(df: pd.DataFrame) -> pd.DataFrame:
    """Title-case city names and strip whitespace."""
    df["city"] = (
        df["city"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
    )
    return df


def _standardize_location(df: pd.DataFrame) -> pd.DataFrame:
    """Title-case location (neighbourhood) names and strip whitespace."""
    df["location"] = (
        df["location"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .str.title()
    )
    return df


def _parse_boolean_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Convert 'Yes'/'No' strings to bool for online_order and book_table."""
    for col in ["has_online_delivery", "has_table_booking"]:
        df[col] = (
            df[col]
            .fillna("No")
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lambda x: x == "yes")
        )
    return df


def _parse_votes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure votes is a non-negative integer."""
    def _safe_int(value):
        try:
            return max(0, int(float(value)))
        except (ValueError, TypeError):
            return 0

    df["votes"] = df["votes"].apply(_safe_int)
    return df


def _clean_rest_type(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the restaurant type field."""
    df["rest_type"] = (
        df["rest_type"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )
    return df


def _clean_dish_liked(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the dish_liked field."""
    df["dish_liked"] = (
        df["dish_liked"]
        .fillna("")
        .astype(str)
        .str.strip()
    )
    return df


def _drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop duplicate restaurants by name + location, keeping highest votes."""
    before = len(df)
    df = df.sort_values("votes", ascending=False)
    df = df.drop_duplicates(subset=["restaurant_name", "location"], keep="first")
    logger.info("Dropped %d duplicate rows", before - len(df))
    return df
