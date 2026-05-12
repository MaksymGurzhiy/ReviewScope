"""BERTopic-based topic modeling.

Falls back to a simpler TF-IDF clustering if BERTopic refuses to fit (which
happens on tiny / very homogeneous datasets). Output schema:

    {
        "total_topics": int,
        "topics": [
            {"topic_id": int, "label": str, "name": str,
             "keywords": [str, ...], "count": int}
        ],
    }
"""
from __future__ import annotations

import logging
import os
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_GENERIC_BLOCKLIST = {
    "the", "and", "this", "that", "with", "for", "you", "your", "have",
    "but", "not", "are", "was", "were", "they", "them", "their", "from",
    "very", "just", "really", "ive", "i've", "im", "i'm", "would", "could",
    "should", "than", "then", "thing", "things", "stuff",
}


def _clean_token(tok: str) -> str:
    return re.sub(r"[^a-zA-Z\-]", "", (tok or "").lower())


class TopicExtractor:
    """Lazy BERTopic wrapper. Skips if there are too few reviews."""

    def __init__(
        self,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        extra_blocklist: Optional[Iterable[str]] = None,
        min_topic_size: int = 5,
    ) -> None:
        self.embedding_model = embedding_model
        self.min_topic_size = max(2, min_topic_size)
        self._blocklist = _GENERIC_BLOCKLIST | {
            _clean_token(t) for t in (extra_blocklist or []) if t
        }
        self._model = None
        self._summary: Dict[str, Any] = {"total_topics": 0, "topics": []}

    # ---- public ----------------------------------------------------------
    def analyze_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        texts = [str(r.get("text") or "").strip() for r in reviews]
        valid_idx = [i for i, t in enumerate(texts) if len(t) > 5]
        if len(valid_idx) < max(self.min_topic_size, 5):
            logger.info("TopicExtractor: not enough reviews (%d), skipping.", len(valid_idx))
            return reviews

        valid_texts = [texts[i] for i in valid_idx]
        try:
            topic_ids = self._fit_bertopic(valid_texts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("BERTopic failed (%s); using TF-IDF fallback.", exc)
            topic_ids = self._fallback_tfidf(valid_texts)

        for idx, topic_id in zip(valid_idx, topic_ids):
            reviews[idx]["topic_id"] = int(topic_id)

        self._build_summary(valid_texts, topic_ids)
        return reviews

    def get_summary(self) -> Dict[str, Any]:
        return self._summary

    # ---- internals -------------------------------------------------------
    def _fit_bertopic(self, texts: List[str]) -> List[int]:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
        from sklearn.feature_extraction.text import CountVectorizer

        if self._model is None:
            embedder = SentenceTransformer(self.embedding_model)
            vectorizer = CountVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                min_df=2,
            )
            self._model = BERTopic(
                embedding_model=embedder,
                vectorizer_model=vectorizer,
                min_topic_size=self.min_topic_size,
                calculate_probabilities=False,
                verbose=False,
            )
        topic_ids, _ = self._model.fit_transform(texts)
        return list(topic_ids)

    def _fallback_tfidf(self, texts: List[str]) -> List[int]:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer

        n_clusters = max(2, min(8, len(texts) // self.min_topic_size))
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, max_features=2048)
        try:
            X = vec.fit_transform(texts)
        except ValueError:
            return [0] * len(texts)
        if X.shape[0] < n_clusters:
            return [0] * len(texts)
        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = km.fit_predict(X)
        return [int(x) for x in labels]

    def _build_summary(self, texts: List[str], topic_ids: List[int]) -> None:
        if not texts:
            self._summary = {"total_topics": 0, "topics": []}
            return

        # Use BERTopic's own labels when available; otherwise fall back to
        # the most frequent non-stopwords per cluster.
        bert_topic_labels: Dict[int, List[str]] = {}
        if self._model is not None and hasattr(self._model, "get_topic"):
            try:
                topics_seen = set(int(t) for t in topic_ids if int(t) != -1)
                for tid in topics_seen:
                    words = self._model.get_topic(tid) or []
                    bert_topic_labels[tid] = [
                        w for w, _score in words if w and _clean_token(w) not in self._blocklist
                    ][:8]
            except Exception:  # noqa: BLE001
                bert_topic_labels = {}

        topics: List[Dict[str, Any]] = []
        counts = Counter(topic_ids)
        for topic_id, count in counts.most_common():
            if topic_id == -1:
                continue
            keywords = bert_topic_labels.get(topic_id) or self._top_words(
                [t for t, tid in zip(texts, topic_ids) if tid == topic_id]
            )
            if not keywords:
                continue
            label = " · ".join(keywords[:3])
            topics.append({
                "topic_id": int(topic_id),
                "name": label,
                "label": label,
                "keywords": keywords,
                "count": int(count),
            })

        self._summary = {"total_topics": len(topics), "topics": topics}

    def _top_words(self, cluster_texts: List[str], k: int = 8) -> List[str]:
        words: Counter = Counter()
        for txt in cluster_texts:
            for tok in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", txt.lower()):
                if tok in self._blocklist or len(tok) < 3:
                    continue
                words[tok] += 1
        return [w for w, _ in words.most_common(k)]
