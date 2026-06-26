"""
Quick end-to-end runner: filter + prompt + LLM for a specific query.
Usage: python run_query.py
"""

import sys
import os
import io

# Fix Windows console encoding for emoji/unicode
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from src.data.loader import load_zomato_data
from src.services.filter_service import filter_restaurants
from src.services.prompt_builder import build_user_prompt, build_system_prompt
from src.services.recommendation import RecommendationService
from src.models.schemas import UserPreferences

def main():
    # -- 1. User inputs ------------------------------------------------
    prefs = UserPreferences(
        location="Bellandur",
        budget="medium",          # medium = Rs 500-1,500
        min_rating=4.2,
        cuisine=None,             # no cuisine preference
        additional_prefs=None,
    )

    print("=" * 60)
    print("  Restaurant Recommendation Query")
    print("=" * 60)
    print(f"  Location      : {prefs.location}")
    print(f"  Budget        : {prefs.budget} (Rs 500 - Rs 1,500)")
    print(f"  Min Rating    : {prefs.min_rating}")
    print(f"  Cuisine       : Any")
    print()

    # -- 2. Load data --------------------------------------------------
    print("[1/4] Loading dataset...")
    df = load_zomato_data()
    print(f"      Loaded {len(df)} restaurants")
    print()

    # -- 3. Filter -----------------------------------------------------
    print("[2/4] Filtering restaurants...")
    result = filter_restaurants(df, prefs)
    print(f"      Total matches : {result.total_matches}")
    print(f"      Candidates    : {len(result.candidates)}")
    if result.fallback_applied:
        print(f"      ** Fallback   : {result.fallback_message}")
    print()

    if result.candidates.empty:
        print("XX No restaurants found matching your criteria.")
        print(f"   Message: {result.fallback_message}")
        return

    # Show the filtered candidates
    print("  Filtered Candidates:")
    print("-" * 60)
    for i, row in result.candidates.iterrows():
        print(
            f"   {row['restaurant_name']:30s} | "
            f"Rating {row['aggregate_rating']:.1f} | "
            f"Rs {row['average_cost']:,.0f} | "
            f"{row['cuisines'][:40]}"
        )
    print()

    # -- 4. Call LLM ---------------------------------------------------
    print("[3/4] Calling Groq LLM for recommendations...")
    svc = RecommendationService()
    response = svc.get_recommendations(prefs, result.candidates)

    # -- 5. Display results --------------------------------------------
    print()
    print("[4/4] Results received!")
    print()
    print("=" * 60)
    print("  TOP 5 RESTAURANT RECOMMENDATIONS")
    print("=" * 60)
    print()

    if response.summary:
        print(f"  Summary: {response.summary}")
        print()

    for rec in response.recommendations:
        rank_label = f"#{rec.rank}"
        print(f"  {rank_label}  {rec.restaurant_name}")
        print(f"      Cuisine : {rec.cuisine}")
        print(f"      Rating  : {rec.rating}")
        print(f"      Cost    : Rs {rec.estimated_cost:,.0f}")
        print(f"      Why     : {rec.explanation}")
        print()

    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
