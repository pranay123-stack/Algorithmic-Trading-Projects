"""Intelligent market matching layer.

Uses sentence embeddings + heuristic filters to identify when markets
on Kalshi and Polymarket represent the same real-world event despite
different wording.

Strategy:
1. Normalize market titles (lowercase, strip filler words, standardize dates/names)
2. Compute sentence embeddings via all-MiniLM-L6-v2 (fast, accurate)
3. Cosine similarity matrix between all Kalshi vs Polymarket titles
4. Apply threshold filter + heuristic cross-checks to avoid false positives
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

import numpy as np

from .config import Config
from .models import Market, MarketMatch, Platform

logger = logging.getLogger(__name__)

# ── Title normalization ─────────────────────────────────────────────

# Common filler patterns to strip
_FILLER = re.compile(
    r"\b(will|the|a|an|be|in|on|at|to|of|for|by|is|it|this|that|do|does)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9\s%$.]")

# Synonyms for common prediction market phrasing
_SYNONYMS = [
    (r"\bwin(?:s|ning)?\b", "win"),
    (r"\bchampion(?:s|ship)?\b", "win"),
    (r"\bvictor(?:y|ious)?\b", "win"),
    (r"\bbecome\b.*\bchampion\b", "win"),
    (r"\btriumph\b", "win"),
    (r"\belect(?:ed|ion)?\b", "election"),
    (r"\bvote(?:d|s|r)?\b", "election"),
    (r"\bapprove(?:d|s|al)?\b", "approve"),
    (r"\bpass(?:ed|es)?\b", "approve"),
    (r"\bexceed\b", "above"),
    (r"\babove\b", "above"),
    (r"\bover\b", "above"),
    (r"\bgreater than\b", "above"),
    (r"\bmore than\b", "above"),
    (r"\bbelow\b", "below"),
    (r"\bunder\b", "below"),
    (r"\bless than\b", "below"),
    (r"\bbefore\b.*\b(\w+ \d{1,2})\b", r"by \1"),
    (r"\bprior to\b", "by"),
    (r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", r"\3-\1-\2"),  # normalize dates
]


def normalize_title(title: str) -> str:
    """Normalize a market title for better matching."""
    text = title.lower().strip()
    # Remove question marks and special chars but keep numbers/percentages
    text = text.rstrip("?").strip()
    # Apply synonym normalization
    for pattern, replacement in _SYNONYMS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Remove filler words
    text = _FILLER.sub(" ", text)
    # Clean up
    text = _NON_ALNUM.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return text


# ── Embedding engine ────────────────────────────────────────────────

_model = None


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", Config.EMBEDDING_MODEL)
        _model = SentenceTransformer(Config.EMBEDDING_MODEL)
        logger.info("Embedding model loaded")
    return _model


def compute_embeddings(texts: list[str]) -> np.ndarray:
    """Compute normalized sentence embeddings for a list of texts."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(embeddings)


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity matrix between two sets of normalized embeddings."""
    # Since embeddings are already normalized, dot product = cosine similarity
    return a @ b.T


# ── Heuristic cross-checks ─────────────────────────────────────────

def _extract_numbers(text: str) -> set[str]:
    """Extract significant numbers from text (prices, thresholds, dates)."""
    return set(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))


def _heuristic_compatible(kalshi_title: str, poly_title: str) -> bool:
    """Additional heuristic checks beyond embedding similarity.

    Catches false positives where the overall topic matches but
    specific thresholds/dates/values differ.
    """
    k_nums = _extract_numbers(kalshi_title)
    p_nums = _extract_numbers(poly_title)

    # If both markets mention specific numbers, at least one must overlap
    if k_nums and p_nums and not k_nums & p_nums:
        return False

    return True


# ── Main matching function ──────────────────────────────────────────

def find_matches(
    kalshi_markets: list[Market],
    poly_markets: list[Market],
    threshold: float | None = None,
) -> list[MarketMatch]:
    """Find matching markets between Kalshi and Polymarket.

    Uses embedding similarity with heuristic cross-checks.
    Returns matches sorted by similarity (highest first).
    """
    if not kalshi_markets or not poly_markets:
        return []

    threshold = threshold or Config.MATCH_THRESHOLD

    # Normalize titles
    k_titles = [normalize_title(m.title) for m in kalshi_markets]
    p_titles = [normalize_title(m.title) for m in poly_markets]

    # Compute embeddings
    logger.info(
        "Computing embeddings: %d Kalshi x %d Polymarket titles",
        len(k_titles), len(p_titles),
    )
    k_embeddings = compute_embeddings(k_titles)
    p_embeddings = compute_embeddings(p_titles)

    # Similarity matrix
    sim_matrix = cosine_similarity_matrix(k_embeddings, p_embeddings)

    # Find matches above threshold
    matches: list[MarketMatch] = []
    for i, k_market in enumerate(kalshi_markets):
        for j, p_market in enumerate(poly_markets):
            sim = float(sim_matrix[i, j])
            if sim < threshold:
                continue

            # Heuristic check
            if not _heuristic_compatible(k_market.title, p_market.title):
                logger.debug(
                    "Heuristic rejected: %.3f | %s | %s",
                    sim, k_market.title, p_market.title,
                )
                continue

            matches.append(MarketMatch(
                kalshi_market=k_market,
                poly_market=p_market,
                similarity=sim,
            ))

    # Sort by similarity descending
    matches.sort(key=lambda m: m.similarity, reverse=True)

    # Deduplicate: each market should only appear in one match (best)
    used_kalshi: set[str] = set()
    used_poly: set[str] = set()
    deduped: list[MarketMatch] = []

    for match in matches:
        k_id = match.kalshi_market.market_id
        p_id = match.poly_market.market_id
        if k_id not in used_kalshi and p_id not in used_poly:
            deduped.append(match)
            used_kalshi.add(k_id)
            used_poly.add(p_id)

    logger.info("Found %d market matches (threshold=%.2f)", len(deduped), threshold)
    return deduped
