"""
Configuration constants for the AI-Powered Restaurant Recommendation System.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ──────────────────────────────────────────────
# Groq API Configuration
# ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_PRIMARY = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "mixtral-8x7b-32768"

# ──────────────────────────────────────────────
# Budget Mapping (average cost for two, in ₹)
# ──────────────────────────────────────────────
BUDGET_MAP = {
    "low": (0, 500),
    "medium": (500, 1500),
    "high": (1500, float("inf")),
}

# ──────────────────────────────────────────────
# Recommendation Settings
# ──────────────────────────────────────────────
MAX_CANDIDATES = 20       # Max restaurants sent to LLM
TOP_K_RESULTS = 5         # Number of final recommendations
LLM_TEMPERATURE = 0.3     # Low creativity, high consistency
LLM_MAX_TOKENS = 1024     # Max tokens for LLM response
LLM_MAX_RETRIES = 3       # Max retry attempts on API failure

# ──────────────────────────────────────────────
# Data Paths
# ──────────────────────────────────────────────
DATA_DIR_RAW = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
DATA_DIR_PROCESSED = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")
PROCESSED_CSV = os.path.join(DATA_DIR_PROCESSED, "zomato_cleaned.csv")

# ──────────────────────────────────────────────
# Dataset Source
# ──────────────────────────────────────────────
HF_DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"

# ──────────────────────────────────────────────
# Input Constraints
# ──────────────────────────────────────────────
MAX_ADDITIONAL_PREFS_LENGTH = 500   # Max chars for free-text preferences
MIN_RATING = 0.0
MAX_RATING = 5.0
DEFAULT_MIN_RATING = 3.5
DEFAULT_BUDGET = "medium"
