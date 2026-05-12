"""KeyBERT-based keyword extraction with sentiment bucketing.

Per-review keywords are pulled with KeyBERT (or a TF-IDF fallback) and then
aggregated across the corpus, bucketed by review sentiment so the UI can show
"why customers love/hate it" lists.

Output of ``get_summary``:

    {
        "positive_keywords": [(phrase, score), ...],
        "neutral_keywords":  [(phrase, score), ...],
        "negative_keywords": [(phrase, score), ...],
        "all_keywords":      [(phrase, count), ...],
    }
"""
from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_GENERIC_BLOCKLIST = {
    "the", "and", "this", "that", "with", "for", "you", "your", "have",
    "but", "not", "are", "was", "were", "they", "them", "their", "from",
    "really", "just", "very", "review", "reviews", "product", "products",
    "thing", "things", "stuff", "amazon",
}


def _clean(tok: str) -> str:
    return re.sub(r"[^a-zA-Z\-\s]", "", (tok or "").lower()).strip()


class KeywordExtractor:
    """Lazy KeyBERT wrapper with a deterministic TF-IDF fallback."""

    def __init__(
        self,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        extra_blocklist: Optional[Iterable[str]] = None,
        keyphrase_ngram_range: Tuple[int, int] = (1, 2),
    ) -> None:
        self.embedding_model = embedding_model
        self.keyphrase_ngram_range = keyphrase_ngram_range
        self._blocklist = _GENERIC_BLOCKLIST | {
            _clean(t) for t in (extra_blocklist or []) if t
        }
        self._kb = None

    # ---- public ----------------------------------------------------------
    def analyze_reviews(
        self,
        reviews: List[Dict[str, Any]],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        texts = [str(r.get("text") or "").strip() for r in reviews]
        if not any(texts):
            return reviews

        try:
            per_review = self._keybert_extract(texts, top_n=top_n)
        except Exception as exc:  # noqa: BLE001
            logger.warning("KeyBERT failed (%s); using TF-IDF fallback.", exc)
            per_review = self._fallback_extract(texts, top_n=top_n)

        for review, kws in zip(reviews, per_review):
            cleaned = [
                (phrase, float(score))
                for phrase, score in kws
                if phrase and _clean(phrase) and _clean(phrase) not in self._blocklist
            ][:top_n]
            review["keywords"] = cleaned
        return reviews

    def get_summary(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        buckets: Dict[str, Dict[str, float]] = {
            "POSITIVE": defaultdict(float),
            "NEGATIVE": defaultdict(float),
            "NEUTRAL": defaultdict(float),
        }
        all_counts: Dict[str, int] = defaultdict(int)

        for review in reviews:
            sentiment = (review.get("sentiment") or "NEUTRAL").upper()
            bucket = buckets.get(sentiment, buckets["NEUTRAL"])
            for phrase, score in review.get("keywords") or []:
                key = _clean(phrase)
                if not key or key in self._blocklist:
                    continue
                bucket[key] += float(score) or 0.01
                all_counts[key] += 1

        def top(d: Dict[str, float], k: int = 12) -> List[Tuple[str, float]]:
            return sorted(
                [(p, round(s, 3)) for p, s in d.items()],
                key=lambda kv: kv[1],
                reverse=True,
            )[:k]

        return {
            "positive_keywords": top(buckets["POSITIVE"]),
            "negative_keywords": top(buckets["NEGATIVE"]),
            "neutral_keywords":  top(buckets["NEUTRAL"]),
            "all_keywords": sorted(
                all_counts.items(), key=lambda kv: kv[1], reverse=True
            )[:30],
        }

    # ---- internals -------------------------------------------------------
    def _keybert_extract(
        self, texts: List[str], top_n: int
    ) -> List[List[Tuple[str, float]]]:
        if self._kb is None:
            from keybert import KeyBERT
            from sentence_transformers import SentenceTransformer

            self._kb = KeyBERT(model=SentenceTransformer(self.embedding_model))

        # KeyBERT supports batch input.
        results = self._kb.extract_keywords(
            texts,
            keyphrase_ngram_range=self.keyphrase_ngram_range,
            stop_words="english",
            top_n=top_n,
            use_mmr=True,
            diversity=0.5,
        )
        # KeyBERT returns either a list-of-lists (batch) or a single list
        # (single doc). Normalise.
        if results and isinstance(results[0], tuple):
            return [results]
        return results  # type: ignore[return-value]

    def _fallback_extract(
        self, texts: List[str], top_n: int
    ) -> List[List[Tuple[str, float]]]:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vec = TfidfVectorizer(
            stop_words="english",
            ngram_range=self.keyphrase_ngram_range,
            min_df=1,
            max_features=4096,
        )
        try:
            X = vec.fit_transform(texts)
        except ValueError:
            return [[] for _ in texts]
        terms = vec.get_feature_names_out()
        out: List[List[Tuple[str, float]]] = []
        for i in range(X.shape[0]):
            row = X.getrow(i).toarray().ravel()
            if not row.any():
                out.append([])
                continue
            idx = row.argsort()[::-1][:top_n]
            out.append([(str(terms[j]), float(row[j])) for j in idx])
        return out
