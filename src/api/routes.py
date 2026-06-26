"""
FastAPI route handlers for the recommendation API.

Implemented in Phase 4.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from src.data.loader import (
    get_available_cuisines,
    get_available_locations,
    load_zomato_data,
)
from src.models.schemas import RecommendationResponse, UserPreferences
from src.services.filter_service import filter_restaurants
from src.services.recommendation import RecommendationError, RecommendationService

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency to allow easy mocking in tests
def get_rec_service() -> RecommendationService:
    return RecommendationService()

@router.post("/recommend", response_model=RecommendationResponse)
async def recommend(
    prefs: UserPreferences,
    rec_service: RecommendationService = Depends(get_rec_service)
):
    try:
        df = load_zomato_data()
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while loading dataset.")
        
    filter_result = filter_restaurants(df, prefs)
    
    if filter_result.candidates.empty:
        raise HTTPException(
            status_code=404, 
            detail=filter_result.fallback_message or "No restaurants match your criteria."
        )

    try:
        response = rec_service.get_recommendations(prefs, filter_result.candidates)
        # Add metadata from filter step
        response.total_matches = filter_result.total_matches
        
        # Append fallback message to the AI summary if a fallback occurred
        if filter_result.fallback_applied:
            if response.summary:
                response.summary = f"{filter_result.fallback_message}\n\n{response.summary}"
            else:
                response.summary = filter_result.fallback_message
                
        return response
    except RecommendationError as e:
        logger.error(f"Recommendation generation failed: {e}")
        raise HTTPException(status_code=502, detail="Failed to generate recommendations from LLM.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@router.get("/cuisines", response_model=List[str])
async def get_cuisines():
    try:
        return get_available_cuisines()
    except Exception as e:
        logger.error(f"Failed to get cuisines: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

@router.get("/locations", response_model=List[str])
async def get_locations():
    try:
        return get_available_locations()
    except Exception as e:
        logger.error(f"Failed to get locations: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")
