"""
Sentiment Analysis using BERT with rating-aware correction
"""
import logging
import time
from typing import Any, Dict, List

import torch
from transformers import pipeline

logger = logging.getLogger(__name__)


def _pick_device() -> int:
    """Return torch device index (-1 = CPU, 0+ = CUDA)."""
    if torch.cuda.is_available():
        return 0
    return -1

POSITIVE_INDICATORS = {
    'excellent', 'amazing', 'fantastic', 'outstanding', 'wonderful', 'perfect',
    'love', 'best', 'great', 'awesome', 'superb', 'brilliant', 'exceptional',
    'highly recommend', 'recommend', 'satisfied', 'happy', 'pleased',
    'friendly', 'helpful', 'beautiful', 'delicious', 'impressive'
}

NEGATIVE_INDICATORS = {
    'terrible', 'horrible', 'awful', 'worst', 'disgusting', 'pathetic',
    'disappointed', 'disappointing', 'rude', 'poor', 'bad', 'slow',
    'cold', 'dirty', 'overpriced', 'waste', 'never again', 'not recommend',
    'not satisfied', 'complained', 'issues', 'problems', 'waited too long'
}


DEFAULT_SENTIMENT_MODEL = "nlptown/bert-base-multilingual-uncased-sentiment"


def _normalize_label(raw_label: str) -> str:
    """Map model-specific labels to POSITIVE/NEUTRAL/NEGATIVE."""
    s = (raw_label or "").lower().strip()
    if "star" in s:
        try:
            stars = int(s.split()[0])
        except (ValueError, IndexError):
            return "NEUTRAL"
        if stars >= 4:
            return "POSITIVE"
        if stars <= 2:
            return "NEGATIVE"
        return "NEUTRAL"
    if s in {"positive", "pos", "label_2"}:
        return "POSITIVE"
    if s in {"negative", "neg", "label_0"}:
        return "NEGATIVE"
    if s in {"neutral", "neu", "label_1"}:
        return "NEUTRAL"
    return raw_label.upper() if raw_label else "NEUTRAL"


class SentimentAnalyzer:
    """Multilingual sentiment analysis (uk/ru/en) with rating correction."""

    def __init__(self, model_name: str = DEFAULT_SENTIMENT_MODEL):
        device = _pick_device()
        device_label = (
            f"cuda:0 ({torch.cuda.get_device_name(0)})"
            if device >= 0
            else "cpu"
        )
        logger.info("Loading sentiment model %s on %s", model_name, device_label)
        t0 = time.perf_counter()
        self.model = pipeline(
            "sentiment-analysis",
            model=model_name,
            truncation=True,
            max_length=512,
            device=device,
        )
        self.device = device
        self.batch_size = 64 if device >= 0 else 16
        logger.info(
            "Sentiment model ready in %.1fs (batch=%d, device=%s)",
            time.perf_counter() - t0, self.batch_size, device_label,
        )

    def _correct_with_rating(self, label: str, score: float,
                             rating: int, text: str) -> tuple:
        """Use rating and lexical cues to correct borderline predictions."""
        text_lower = text.lower()
        has_positive = any(w in text_lower for w in POSITIVE_INDICATORS)
        has_negative = any(w in text_lower for w in NEGATIVE_INDICATORS)

        if rating is not None:
            if rating >= 4 and label == 'NEGATIVE' and score < 0.85:
                if has_positive and not has_negative:
                    return 'POSITIVE', 1.0 - score
                if not has_negative:
                    return 'POSITIVE', 0.6
            if rating <= 2 and label == 'POSITIVE' and score < 0.85:
                if has_negative and not has_positive:
                    return 'NEGATIVE', 1.0 - score
                if not has_positive:
                    return 'NEGATIVE', 0.6

        if score < 0.70:
            if has_positive and not has_negative:
                return 'POSITIVE', 0.65
            if has_negative and not has_positive:
                return 'NEGATIVE', 0.65

        return label, score

    def analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
        n = len(texts)
        batch_size = self.batch_size
        n_batches = (n + batch_size - 1) // batch_size
        logger.info(
            "Sentiment: analyzing %d texts in %d batches of %d (device=%s)",
            n, n_batches, batch_size, "cuda" if self.device >= 0 else "cpu",
        )
        results: List[Dict[str, Any]] = []
        t0 = time.perf_counter()

        for i in range(0, n, batch_size):
            batch = texts[i:i + batch_size]
            batch_idx = i // batch_size + 1
            t_b = time.perf_counter()
            try:
                batch_results = self.model(batch)
                for r in batch_results:
                    r['label'] = _normalize_label(r.get('label', ''))
                results.extend(batch_results)
            except Exception as e:  # noqa: BLE001
                logger.error("Error analyzing batch %d/%d: %s", batch_idx, n_batches, e)
                results.extend([{'label': 'NEUTRAL', 'score': 0.5}] * len(batch))

            done = min(i + batch_size, n)
            elapsed = time.perf_counter() - t0
            rate = done / elapsed if elapsed > 0 else 0
            eta = (n - done) / rate if rate > 0 else 0
            logger.info(
                "Sentiment: batch %d/%d done (%.1fs/batch) | %d/%d (%.0f/s) | ETA %.0fs",
                batch_idx, n_batches, time.perf_counter() - t_b, done, n, rate, eta,
            )

        logger.info("Sentiment: completed %d texts in %.1fs", n, time.perf_counter() - t0)
        return results

    def analyze_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        texts = [r['text'] for r in reviews]
        sentiments = self.analyze(texts)

        for review, sentiment in zip(reviews, sentiments):
            label = sentiment['label']
            score = sentiment['score']

            rating = None
            if review.get('rating'):
                try:
                    rating = int(review['rating'])
                except (ValueError, TypeError):
                    pass

            label, score = self._correct_with_rating(
                label, score, rating, review['text']
            )
            review['sentiment'] = label
            review['sentiment_score'] = score

        return reviews

    def get_summary(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        sentiments = [r.get('sentiment') for r in reviews if r.get('sentiment')]
        if not sentiments:
            return {}

        positive = sum(1 for s in sentiments if s == 'POSITIVE')
        negative = sum(1 for s in sentiments if s == 'NEGATIVE')
        neutral = sum(1 for s in sentiments if s == 'NEUTRAL')
        total = len(sentiments)

        def pct(n: int) -> float:
            return (n / total * 100) if total > 0 else 0.0

        def avg_score(label: str) -> float:
            scores = [r.get('sentiment_score', 0) for r in reviews if r.get('sentiment') == label]
            return sum(scores) / len(scores) if scores else 0.0

        return {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_percent': pct(positive),
            'negative_percent': pct(negative),
            'neutral_percent': pct(neutral),
            'avg_positive_score': avg_score('POSITIVE'),
            'avg_negative_score': avg_score('NEGATIVE'),
            'avg_neutral_score': avg_score('NEUTRAL'),
        }
