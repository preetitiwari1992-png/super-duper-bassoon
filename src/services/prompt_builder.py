"""
Prompt builder — constructs structured LLM prompts from user preferences
and restaurant data.

Public API
----------
build_system_prompt()
    Returns the static system-role prompt.

build_user_prompt(prefs, candidates_df)
    Returns the user-role prompt populated with preferences and restaurant data.

build_messages(prefs, candidates_df)
    Convenience wrapper that returns a ready-to-send message list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.config import BUDGET_MAP, TOP_K_RESULTS

if TYPE_CHECKING:
    from src.models.schemas import UserPreferences


# ──────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an expert restaurant recommendation assistant. You have deep knowledge \
of dining experiences, cuisines, and what makes a great restaurant choice.

Given a list of candidate restaurants and the user's preferences, you must:
1. Rank the top {top_k} restaurants that best match the user's needs.
2. Provide a clear, personalized explanation for each recommendation.
3. Consider factors like cuisine match, rating, cost, popularity (votes), \
and any special preferences the user mentioned.
4. Return your response as valid JSON — no markdown fences, no extra text.
"""

# ──────────────────────────────────────────────
# JSON output schema (injected into the prompt)
# ──────────────────────────────────────────────

OUTPUT_SCHEMA = """\
{
  "recommendations": [
    {
      "rank": 1,
      "restaurant_name": "...",
      "cuisine": "...",
      "rating": 4.5,
      "estimated_cost": 800,
      "explanation": "A 1–2 sentence personalized reason."
    }
  ],
  "summary": "A short overall summary (1–2 sentences) of why these restaurants were chosen."
}\
"""

# ──────────────────────────────────────────────
# User prompt template
# ──────────────────────────────────────────────

_USER_PROMPT_TEMPLATE = """\
## User Preferences
- Location: {location}
- Budget: {budget} ({budget_range})
- Preferred Cuisine: {cuisine}
- Minimum Rating: {min_rating}
- Additional Preferences: {additional_prefs}

## Available Restaurants
{restaurant_table}

## Instructions
From the restaurant list above, rank the top {top_k} restaurants that best \
match the user's preferences. Return ONLY valid JSON in this exact format:
{output_schema}

Important:
- Use the exact restaurant names from the list.
- The "estimated_cost" should be the average cost for two people.
- Each "explanation" must reference specific qualities of the restaurant \
and how they relate to the user's preferences.
- If fewer than {top_k} restaurants are available, rank all of them.
"""


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _format_budget_range(budget: str) -> str:
    """Human-readable budget range string, e.g. '₹500 – ₹1 500'."""
    low, high = BUDGET_MAP.get(budget, BUDGET_MAP["medium"])
    if high == float("inf"):
        return f"₹{low:,.0f}+"
    return f"₹{low:,.0f} – ₹{high:,.0f}"


def _format_restaurant_table(df: pd.DataFrame) -> str:
    """
    Build a compact Markdown table of candidate restaurants.

    Columns included: Name, Cuisines, Rating, Cost, Votes, Delivery, Booking.
    """
    if df.empty:
        return "(No restaurants available.)"

    header = (
        "| # | Name | Cuisines | Rating | Avg Cost (₹) | Votes "
        "| Online Delivery | Table Booking |"
    )
    separator = (
        "|---|------|----------|--------|--------------|-------"
        "|-----------------|---------------|"
    )
    rows: list[str] = [header, separator]

    for idx, row in enumerate(df.itertuples(index=False), start=1):
        name = getattr(row, "restaurant_name", "N/A")
        cuisines = getattr(row, "cuisines", "N/A")
        rating = getattr(row, "aggregate_rating", 0.0)
        cost = getattr(row, "average_cost", 0.0)
        votes = getattr(row, "votes", 0)
        delivery = "Yes" if getattr(row, "has_online_delivery", False) else "No"
        booking = "Yes" if getattr(row, "has_table_booking", False) else "No"

        rows.append(
            f"| {idx} | {name} | {cuisines} | {rating} | {cost:,.0f} "
            f"| {votes} | {delivery} | {booking} |"
        )

    return "\n".join(rows)


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────


def build_system_prompt() -> str:
    """Return the system-role prompt for the LLM."""
    return SYSTEM_PROMPT.format(top_k=TOP_K_RESULTS)


def build_user_prompt(
    prefs: "UserPreferences",
    candidates_df: pd.DataFrame,
) -> str:
    """
    Populate the user-role prompt with user preferences and candidate data.

    Parameters
    ----------
    prefs : UserPreferences
        Validated user preferences.
    candidates_df : pd.DataFrame
        Filtered restaurant candidates (output of ``filter_restaurants``).

    Returns
    -------
    str
        The fully-formatted user prompt ready for the LLM.
    """
    return _USER_PROMPT_TEMPLATE.format(
        location=prefs.location,
        budget=prefs.budget,
        budget_range=_format_budget_range(prefs.budget),
        cuisine=prefs.cuisine or "Any",
        min_rating=prefs.min_rating,
        additional_prefs=prefs.additional_prefs or "None",
        restaurant_table=_format_restaurant_table(candidates_df),
        top_k=TOP_K_RESULTS,
        output_schema=OUTPUT_SCHEMA,
    )


def build_messages(
    prefs: "UserPreferences",
    candidates_df: pd.DataFrame,
) -> list[dict[str, str]]:
    """
    Convenience method — return the full message list expected by the Groq API.

    Returns
    -------
    list[dict]
        ``[{"role": "system", "content": ...}, {"role": "user", "content": ...}]``
    """
    return [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(prefs, candidates_df)},
    ]
