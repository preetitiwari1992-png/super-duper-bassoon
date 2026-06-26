"""
Pydantic models for request / response validation.

Models
------
Restaurant
    Represents a single restaurant record from the cleaned dataset.
UserPreferences
    Captures user input for the recommendation request.
Recommendation
    A single ranked recommendation returned by the LLM.
RecommendationResponse
    The full response envelope returned to the client.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from src.config import (
    DEFAULT_BUDGET,
    DEFAULT_MIN_RATING,
    MAX_ADDITIONAL_PREFS_LENGTH,
    MAX_RATING,
    MIN_RATING,
)


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────


class Restaurant(BaseModel):
    """A single restaurant from the cleaned Zomato dataset."""

    restaurant_name: str
    city: str
    location: str = ""
    cuisines: str = "Unknown"
    average_cost: float = 0.0
    aggregate_rating: float = 0.0
    votes: int = 0
    has_online_delivery: bool = False
    has_table_booking: bool = False
    rest_type: str = "Unknown"
    dish_liked: str = ""


# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────


class UserPreferences(BaseModel):
    """User input for the recommendation endpoint."""

    location: str = Field(
        ...,
        min_length=1,
        description="City or neighbourhood, e.g. 'Banashankari', 'BTM'",
    )
    budget: str = Field(
        default=DEFAULT_BUDGET,
        description="Budget tier: 'low', 'medium', or 'high'",
    )
    cuisine: Optional[str] = Field(
        default=None,
        description="Preferred cuisine, e.g. 'Italian', 'Chinese'",
    )
    min_rating: float = Field(
        default=DEFAULT_MIN_RATING,
        ge=MIN_RATING,
        le=MAX_RATING,
        description="Minimum acceptable rating (0.0–5.0)",
    )
    additional_prefs: Optional[str] = Field(
        default=None,
        description="Free-text additional preferences, e.g. 'family-friendly'",
    )

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("low", "medium", "high"):
            raise ValueError("budget must be 'low', 'medium', or 'high'")
        return v

    @field_validator("additional_prefs")
    @classmethod
    def truncate_additional_prefs(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > MAX_ADDITIONAL_PREFS_LENGTH:
            return v[:MAX_ADDITIONAL_PREFS_LENGTH]
        return v


# ──────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────


class Recommendation(BaseModel):
    """A single ranked restaurant recommendation from the LLM."""

    rank: int
    restaurant_name: str
    cuisine: str
    rating: float
    estimated_cost: float
    explanation: str


class RecommendationResponse(BaseModel):
    """Full response envelope for the /recommend endpoint."""

    recommendations: List[Recommendation]
    summary: str = ""
    total_matches: int = 0
