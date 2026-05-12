"""DistilBERT sentiment analyzer with star-rating correction.

Outputs three labels (POSITIVE / NEGATIVE / NEUTRAL) even though DistilBERT-SST2
itself is binary — we treat low-confidence predictions and 3-star ratings as
neutral so the downstream UI / ABSA / summary modules see the full spectrum.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Tuneable thresholds. Confidence below NEUTRAL_BAND collapses to NEUTRAL,
# which prevents BERT's binary head from forcing a polarity on lukewarm text.
NEUTRAL_BAND = 0.65
DEFAULT_MODEL = os.getenv(
    "SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"
)


def _normalise_label(raw: str) -> str:
    raw = (raw or "").strip().upper()
    if raw.startswith("POS") or raw in {"LABEL_1", "1"}:
        return "POSITIVE"
    if raw.startswith("NEG") or raw in {"LABEL_0", "0"}:
        return "NEGATIVE"
    return "NEUTRAL"


def _rating_label(rating: Any) -> Optional[str]:
    """Map a numeric review rating to a polarity label, when available."""
    if rating is None:
        return None
    try:
        v = float(rating)
    except (TypeError, ValueError):
        return None
    if v <= 2:
        return "NEGATIVE"
    if v >= 4:
        return "POSITIVE"
    if v == 3:
        return "NEUTRAL"
    return None


class SentimentAnalyzer:
    """Lazy DistilBERT sentiment classifier with rating-aware correction."""

    def __init__(self, model_name: str = DEFAULT_MODEL, batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self._pipe = None  # transformers pipeline, loaded on first call

    def _ensure_loaded(self) -> None:
        if self._pipe is not None:
            return
        from transformers import pipeline

        logger.info("Loading sentiment model: %s", self.model_name)
        self._pipe = pipeline(
            task="sentiment-analysis",
            model=self.model_name,
            tokenizer=self.model_name,
            truncation=True,
            top_k=None,
        )

    def analyze_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not reviews:
            return reviews
        self._ensure_loaded()
        texts = [str(r.get("text") or "")[:512] for r in reviews]
        try:
            preds = self._pipe(texts, batch_size=self.batch_size)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Sentiment inference failed: %s", exc)
            for r in reviews:
                r.setdefault("sentiment", "NEUTRAL")
                r.setdefault("sentiment_score", 0.5)
            return reviews

        for review, pred in zip(reviews, preds):
            top = pred[0] if isinstance(pred, list) and pred else pred
            label = _normalise_label(top.get("label", "NEUTRAL"))
            score = float(top.get("score", 0.0))

            if score < NEUTRAL_BAND:
                label = "NEUTRAL"

            override = _rating_label(review.get("rating"))
            if override is not None:
                if override == "NEUTRAL":
                    label = "NEUTRAL"
                elif override != label and score < 0.85:
                    label = override

            review["sentiment"] = label
            review["sentiment_score"] = round(score, 4)
        return reviews

    @staticmethod
    def get_summary(reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(reviews) or 1
        pos = sum(1 for r in reviews if r.get("sentiment") == "POSITIVE")
        neg = sum(1 for r in reviews if r.get("sentiment") == "NEGATIVE")
        neu = total - pos - neg

        def pct(n: int) -> float:
            return round((n / total) * 100, 1)

        avg_score = (
            round(sum(float(r.get("sentiment_score", 0.0)) for r in reviews) / total, 3)
            if reviews
            else 0.0
        )

        return {
            "total": len(reviews),
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "positive_percent": pct(pos),
            "negative_percent": pct(neg),
            "neutral_percent": pct(neu),
            "avg_score": avg_score,
        }
