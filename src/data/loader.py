"""
Dataset loader — downloads the Zomato dataset from Hugging Face and caches
the cleaned result as a local CSV for fast subsequent loads.
"""

import logging
import os

import pandas as pd

from src.config import HF_DATASET_NAME, PROCESSED_CSV, DATA_DIR_PROCESSED
from src.data.preprocessor import preprocess

logger = logging.getLogger(__name__)


def load_zomato_data(force_reload: bool = False) -> pd.DataFrame:
    """
    Load the Zomato restaurant dataset.

    1. If a cleaned CSV cache exists (and ``force_reload`` is False), read it.
    2. Otherwise download from Hugging Face, preprocess, cache, and return.

    Parameters
    ----------
    force_reload : bool
        When True the cached CSV is ignored and the dataset is re-downloaded
        and re-processed.

    Returns
    -------
    pd.DataFrame
        Cleaned restaurant DataFrame with standardized column names.

    Raises
    ------
    RuntimeError
        If neither the Hugging Face download nor a local cache is available.
    """

    # ── Try cached CSV first ──────────────────────────────────────────
    if not force_reload and os.path.exists(PROCESSED_CSV):
        logger.info("Loading cached dataset from %s", PROCESSED_CSV)
        try:
            df = pd.read_csv(PROCESSED_CSV)
            logger.info("Cached dataset loaded — %d rows", len(df))
            return df
        except Exception as exc:
            logger.warning("Cache read failed (%s). Will re-download.", exc)

    # ── Download from Hugging Face ────────────────────────────────────
    logger.info("Downloading dataset from Hugging Face: %s", HF_DATASET_NAME)
    try:
        from datasets import load_dataset

        dataset = load_dataset(HF_DATASET_NAME)

        # The dataset may have a single 'train' split
        split_name = list(dataset.keys())[0]
        df = dataset[split_name].to_pandas()
        logger.info("Downloaded %d rows from '%s' split", len(df), split_name)

    except Exception as exc:
        # If download fails, try the cache as last resort
        if os.path.exists(PROCESSED_CSV):
            logger.warning(
                "Download failed (%s). Falling back to cached CSV.", exc
            )
            return pd.read_csv(PROCESSED_CSV)
        raise RuntimeError(
            f"Could not load dataset: download failed ({exc}) "
            f"and no local cache exists at {PROCESSED_CSV}"
        ) from exc

    # ── Preprocess ────────────────────────────────────────────────────
    df = preprocess(df)

    # ── Cache to disk ─────────────────────────────────────────────────
    try:
        os.makedirs(DATA_DIR_PROCESSED, exist_ok=True)
        df.to_csv(PROCESSED_CSV, index=False)
        logger.info("Cached cleaned dataset to %s", PROCESSED_CSV)
    except OSError as exc:
        logger.warning("Could not cache dataset to disk: %s", exc)

    return df


def get_available_cities(df: pd.DataFrame | None = None) -> list[str]:
    """Return a sorted list of unique cities in the dataset."""
    if df is None:
        df = load_zomato_data()
    return sorted(df["city"].dropna().unique().tolist())


def get_available_cuisines(df: pd.DataFrame | None = None) -> list[str]:
    """Return a sorted list of unique individual cuisines in the dataset."""
    if df is None:
        df = load_zomato_data()
    all_cuisines = (
        df["cuisines"]
        .dropna()
        .str.split(", ")
        .explode()
        .str.strip()
        .unique()
    )
    return sorted([c for c in all_cuisines if c and c != "Unknown"])


def get_available_locations(df: pd.DataFrame | None = None) -> list[str]:
    """Return a sorted list of unique neighbourhood locations in the dataset."""
    if df is None:
        df = load_zomato_data()
    return sorted(df["location"].dropna().unique().tolist())
