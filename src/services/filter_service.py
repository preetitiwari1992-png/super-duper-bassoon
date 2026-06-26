"""
Filter service — applies deterministic filters to narrow the restaurant
dataset based on user preferences before passing candidates to the LLM.

The filter pipeline runs in order:
  1. Location (city OR neighbourhood)
  2. Budget range
  3. Cuisine (partial, case-insensitive)
  4. Minimum rating

When the intersection of all filters is empty a **progressive fallback**
strategy broadens the criteria until results are found or all options are
exhausted.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.config import BUDGET_MAP, MAX_CANDIDATES
from src.models.schemas import UserPreferences

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Budget helpers
# ──────────────────────────────────────────────

# Ordered tiers so we can "expand" to the next one
_BUDGET_ORDER = ["low", "medium", "high"]


def _next_budget_tier(current: str) -> Optional[str]:
    """Return the next broader budget tier, or None if already at 'high'."""
    try:
        idx = _BUDGET_ORDER.index(current)
    except ValueError:
        return None
    if idx + 1 < len(_BUDGET_ORDER):
        return _BUDGET_ORDER[idx + 1]
    return None


def _budget_range(tier: str) -> tuple[float, float]:
    """Look up the (low, high) cost range for a budget tier."""
    return BUDGET_MAP.get(tier, BUDGET_MAP["medium"])


# ──────────────────────────────────────────────
# Individual filter functions
# ──────────────────────────────────────────────


def _filter_by_location(df: pd.DataFrame, location: str) -> pd.DataFrame:
    """
    Match against both ``city`` and ``location`` (neighbourhood) columns.

    The user might type a city name like "Bangalore" or a neighbourhood
    like "Koramangala". We try both, case-insensitively.
    """
    loc_lower = location.strip().lower()
    mask = (
        df["city"].str.lower().str.strip().eq(loc_lower)
        | df["location"].str.lower().str.strip().eq(loc_lower)
    )
    return df[mask]


def _filter_by_budget(
    df: pd.DataFrame, tier: str
) -> pd.DataFrame:
    """Filter restaurants whose average_cost falls within the budget range."""
    low, high = _budget_range(tier)
    return df[(df["average_cost"] >= low) & (df["average_cost"] <= high)]


def _filter_by_cuisine(df: pd.DataFrame, cuisine: str) -> pd.DataFrame:
    """Case-insensitive partial match against the cuisines string."""
    return df[
        df["cuisines"].str.contains(cuisine, case=False, na=False)
    ]


def _filter_by_min_rating(df: pd.DataFrame, min_rating: float) -> pd.DataFrame:
    """Keep only restaurants at or above the minimum rating."""
    return df[df["aggregate_rating"] >= min_rating]


# ──────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────


@dataclass
class FilterResult:
    """Wraps filtered candidates and metadata about the filter run."""

    candidates: pd.DataFrame
    total_matches: int
    fallback_applied: bool = False
    fallback_message: str = ""


# ──────────────────────────────────────────────
# Main public API
# ──────────────────────────────────────────────


def filter_restaurants(
    df: pd.DataFrame,
    prefs: UserPreferences,
) -> FilterResult:
    """
    Apply chained filters with progressive fallback.

    Parameters
    ----------
    df : pd.DataFrame
        The full cleaned restaurant dataset.
    prefs : UserPreferences
        User-provided preferences.

    Returns
    -------
    FilterResult
        Filtered candidates (capped at ``MAX_CANDIDATES``), plus metadata.
    """

    # ── Step 0: location filter (mandatory, no fallback) ──────────
    location_df = _filter_by_location(df, prefs.location)

    if location_df.empty:
        logger.warning("No restaurants found for location '%s'", prefs.location)
        return FilterResult(
            candidates=pd.DataFrame(columns=df.columns),
            total_matches=0,
            fallback_applied=False,
            fallback_message=(
                f"No restaurants found in '{prefs.location}'. "
                "Try a different city or neighbourhood."
            ),
        )

    # ── Step 1: try strict filters ────────────────────────────────
    result = _apply_strict_filters(location_df, prefs)

    if not result.empty:
        return _finalize(result)

    # ── Step 2: progressive fallback ──────────────────────────────
    logger.info("Strict filters returned 0 results — starting fallback")
    return _fallback(location_df, prefs)


def _apply_strict_filters(
    df: pd.DataFrame,
    prefs: UserPreferences,
    *,
    cuisine: Optional[str] = ...,    # sentinel — use prefs value
    min_rating: Optional[float] = ...,
    budget: Optional[str] = ...,
) -> pd.DataFrame:
    """Apply budget + cuisine + rating filters without fallback."""
    # Resolve sentinels to actual preference values
    if cuisine is ...:
        cuisine = prefs.cuisine
    if min_rating is ...:
        min_rating = prefs.min_rating
    if budget is ...:
        budget = prefs.budget

    result = df.copy()

    # Budget
    result = _filter_by_budget(result, budget)

    # Cuisine (optional)
    if cuisine:
        result = _filter_by_cuisine(result, cuisine)

    # Rating
    result = _filter_by_min_rating(result, min_rating)

    return result


def _fallback(
    location_df: pd.DataFrame,
    prefs: UserPreferences,
) -> FilterResult:
    """
    Progressive fallback strategy.

    Order:
      1. Drop the cuisine filter
      2. Lower min_rating by 0.5 (repeatedly, down to 0.0)
      3. Expand budget to the next tier
      4. Give up
    """
    messages: list[str] = []

    # ── Fallback 1: remove cuisine ────────────────────────────────
    if prefs.cuisine:
        result = _apply_strict_filters(
            location_df, prefs, cuisine=None
        )
        if not result.empty:
            messages.append(
                f"No exact match for '{prefs.cuisine}' cuisine. "
                "Showing results across all cuisines."
            )
            return _finalize(result, fallback=True, message=" ".join(messages))

    # ── Fallback 2: lower min_rating progressively ────────────────
    rating = prefs.min_rating
    while rating > 0.0:
        rating = max(0.0, rating - 0.5)
        result = _apply_strict_filters(
            location_df, prefs, cuisine=None, min_rating=rating
        )
        if not result.empty:
            messages.append(
                f"Lowered minimum rating from {prefs.min_rating} to {rating}."
            )
            return _finalize(result, fallback=True, message=" ".join(messages))

    # ── Fallback 3: expand budget ─────────────────────────────────
    next_tier = _next_budget_tier(prefs.budget)
    if next_tier:
        result = _apply_strict_filters(
            location_df,
            prefs,
            cuisine=None,
            min_rating=0.0,
            budget=next_tier,
        )
        if not result.empty:
            messages.append(
                f"Expanded budget from '{prefs.budget}' to '{next_tier}'."
            )
            return _finalize(result, fallback=True, message=" ".join(messages))

        # Try the widest tier if we haven't already
        if next_tier != "high":
            result = _apply_strict_filters(
                location_df,
                prefs,
                cuisine=None,
                min_rating=0.0,
                budget="high",
            )
            if not result.empty:
                messages.append("Expanded budget to 'high'.")
                return _finalize(result, fallback=True, message=" ".join(messages))

    # ── Fallback 4: return everything in this location ────────────
    if not location_df.empty:
        messages.append(
            "No filtered matches. Showing all restaurants in your location."
        )
        return _finalize(location_df, fallback=True, message=" ".join(messages))

    # ── Nothing at all ────────────────────────────────────────────
    return FilterResult(
        candidates=pd.DataFrame(columns=location_df.columns),
        total_matches=0,
        fallback_applied=True,
        fallback_message="No restaurants match your criteria. Try different preferences.",
    )


def _finalize(
    df: pd.DataFrame,
    *,
    fallback: bool = False,
    message: str = "",
) -> FilterResult:
    """Sort by rating descending and cap at MAX_CANDIDATES."""
    total = len(df)
    capped = (
        df.sort_values(
            ["aggregate_rating", "votes"],
            ascending=[False, False],
        )
        .head(MAX_CANDIDATES)
        .reset_index(drop=True)
    )
    logger.info(
        "Filter result: %d total matches → %d candidates (fallback=%s)",
        total, len(capped), fallback,
    )
    return FilterResult(
        candidates=capped,
        total_matches=total,
        fallback_applied=fallback,
        fallback_message=message,
    )
