"""
Top-level NLP pipeline used by the API.

Orchestrates:
    Sentiment Analysis (BERT/DistilBERT, with rating correction)
    Aspect-Based Sentiment Analysis (lexicon + window scoring)
    Topic Modeling (BERTopic)
    Keyword Extraction (KeyBERT)
    Language Detection (langdetect)
    Insights / Recommendations
    Executive summary text

Models are loaded lazily so the API stays light until first analysis.
"""
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional

from src.models.sentiment_analyzer import SentimentAnalyzer
from src.models.topic_extractor import TopicExtractor
from src.models.keyword_extractor import KeywordExtractor
from src.nlp.aspect_analyzer import AspectAnalyzer
from src.nlp.language_detector import LanguageDetector
from src.nlp.summary_generator import SummaryGenerator
from src.schemas.analysis import AnalysisRequest

logger = logging.getLogger(__name__)


ProgressCallback = Callable[[str, int], None]


# Generic words that show up in file names but tell us nothing about the
# product itself - we strip them so the file-name blocklist only contains
# brand/product tokens.
_FILENAME_STOPWORDS = {
    "review", "reviews", "data", "dataset", "datasets", "sample", "samples",
    "test", "demo", "export", "exports", "csv", "xlsx", "json", "txt",
    "feedback", "feedbacks", "comment", "comments", "the", "and", "of",
    "for", "from", "all", "raw", "final", "v1", "v2", "v3",
}


def _filename_blocklist(file_name: Optional[str]) -> List[str]:
    """Extract candidate product/brand tokens from an uploaded file name.

    'Airpods_Reviews.csv'      -> ['airpods']
    'Amazon Echo 2 Reviews.csv'-> ['amazon', 'echo']
    'reviews.csv'              -> []
    """
    if not file_name:
        return []
    stem = re.sub(r"\.[^.]+$", "", file_name)  # strip extension
    tokens = re.split(r"[\s_\-,()\[\]\.]+", stem.lower())
    return [t for t in tokens if t and len(t) >= 3 and t.isalpha() and t not in _FILENAME_STOPWORDS]


def _noop(_stage: str, _pct: int) -> None:  # default callback
    pass


class NLPPipeline:
    """Single-responsibility orchestrator. Models are cached at instance level."""

    def __init__(self):
        self.sentiment: Optional[SentimentAnalyzer] = None
        self.topics: Optional[TopicExtractor] = None
        self.keywords: Optional[KeywordExtractor] = None
        self.aspects: Optional[AspectAnalyzer] = None
        self.summary = SummaryGenerator()
        # Cache the per-run blocklist so lazy model factories can pick it up.
        self._blocklist: List[str] = []

    # ------------------------------------------------------------- public
    def run(
        self,
        reviews: List[Dict[str, Any]],
        options: AnalysisRequest,
        on_progress: ProgressCallback = _noop,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()

        # Drop blank / NaN reviews up-front so they don't pollute any of
        # the downstream models (sentiment, topics, keywords, aspects).
        reviews = [
            r for r in reviews
            if str(r.get("text") or "").strip()
            and str(r.get("text") or "").strip().lower() not in {"nan", "none", "null", "n/a", "na"}
        ]
        if not reviews:
            raise ValueError("All reviews are empty after cleaning.")

        # Build the per-dataset blocklist from the uploaded file name once
        # and reuse it across ABSA, BERTopic and KeyBERT.
        self._blocklist = _filename_blocklist(file_name)
        if self._blocklist:
            logger.info("Filename blocklist: %s", self._blocklist)
        self.aspects = AspectAnalyzer(extra_blocklist=self._blocklist)

        def report(stage: str, pct: int) -> None:
            try:
                on_progress(stage, pct)
            except Exception:  # noqa: BLE001
                logger.debug("progress callback failed", exc_info=True)

        report("language_detection", 5)
        LanguageDetector.annotate(reviews)
        primary_language = LanguageDetector.primary(reviews)
        language_distribution = LanguageDetector.distribution(reviews)

        analyses_performed: List[str] = []
        sentiment_summary: Dict[str, Any] | None = None
        aspects_summary: Dict[str, Any] | None = None
        topic_summary: Dict[str, Any] | None = None
        keyword_summary: Dict[str, Any] | None = None

        if options.analyze_sentiment:
            report("sentiment", 15)
            self._sentiment(reviews)
            sentiment_summary = self.sentiment.get_summary(reviews) if self.sentiment else None
            analyses_performed.append("sentiment")

        if options.analyze_aspects:
            report("aspects", 45)
            self.aspects.analyze_reviews(reviews)
            aspects_summary = self.aspects.aggregate(reviews)
            analyses_performed.append("aspects")

        if options.analyze_topics:
            report("topics", 60)
            try:
                self._topics(reviews)
                topic_summary = self.topics.get_summary()  # type: ignore[union-attr]
                analyses_performed.append("topics")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Topic extraction failed: %s", exc)

        if options.extract_keywords:
            report("keywords", 78)
            try:
                self._keywords(reviews)
                keyword_summary = self.keywords.get_summary(reviews)  # type: ignore[union-attr]
                analyses_performed.append("keywords")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Keyword extraction failed: %s", exc)

        report("insights", 90)
        insights = self._build_insights(sentiment_summary, aspects_summary, keyword_summary)
        recommendations = self._build_recommendations(sentiment_summary, aspects_summary)

        summary_text: Optional[str] = None
        if options.generate_summary:
            report("summary", 95)
            summary_text = self.summary.generate(
                sentiment_summary=sentiment_summary,
                aspects=aspects_summary,
                topics=topic_summary,
                keywords=keyword_summary,
                total_reviews=len(reviews),
            )

        duration_ms = int((time.perf_counter() - t0) * 1000)

        metrics = {
            "total_reviews": len(reviews),
            "analyses_performed": analyses_performed,
            "primary_language": primary_language,
            "language_distribution": language_distribution,
            "duration_ms": duration_ms,
        }

        return {
            "sentiment_summary": sentiment_summary,
            "aspects": aspects_summary,
            "topics": topic_summary,
            "keywords": keyword_summary,
            "summary_text": summary_text,
            "insights": insights,
            "recommendations": recommendations,
            "metrics": metrics,
            "sample_reviews": reviews,
        }

    # ----------------------------------------------------------- helpers
    def _sentiment(self, reviews: List[Dict[str, Any]]) -> None:
        if self.sentiment is None:
            self.sentiment = SentimentAnalyzer()
        self.sentiment.analyze_reviews(reviews)

    def _topics(self, reviews: List[Dict[str, Any]]) -> None:
        if self.topics is None:
            self.topics = TopicExtractor(extra_blocklist=self._blocklist)
        self.topics.analyze_reviews(reviews)

    def _keywords(self, reviews: List[Dict[str, Any]]) -> None:
        if self.keywords is None:
            self.keywords = KeywordExtractor(extra_blocklist=self._blocklist)
        self.keywords.analyze_reviews(reviews, top_n=5)

    @staticmethod
    def _build_insights(sent_sum, aspects_sum, kw_sum) -> List[str]:
        out: List[str] = []
        if sent_sum:
            pos = sent_sum.get("positive_percent", 0)
            neg = sent_sum.get("negative_percent", 0)
            if pos > 70:
                out.append(f"Strongly positive sentiment ({pos:.1f}%) - customers are very satisfied.")
            elif pos > 50:
                out.append(f"Mostly positive feedback ({pos:.1f}%) with room for improvement.")
            elif neg > 50:
                out.append(f"Concerning negative feedback ({neg:.1f}%) - immediate action needed.")
            if neg > 30:
                out.append(f"High negative sentiment ({neg:.1f}%) requires attention.")

        if aspects_sum:
            items = aspects_sum.get("aspects", [])
            top = sorted(items, key=lambda a: a.get("total_mentions", 0), reverse=True)[:1]
            for a in top:
                out.append(
                    f"Most discussed aspect: {a['aspect']} ({a['total_mentions']} mentions, polarity {a['polarity']:+.0f})."
                )

        if kw_sum:
            pos_kw = kw_sum.get("positive_keywords", [])[:3]
            neg_kw = kw_sum.get("negative_keywords", [])[:3]
            if pos_kw:
                out.append("Key strengths: " + ", ".join(k for k, _ in pos_kw) + ".")
            if neg_kw:
                out.append("Main concerns: " + ", ".join(k for k, _ in neg_kw) + ".")

        if not out:
            out.append("Analysis completed - check detailed results.")
        return out

    @staticmethod
    def _build_recommendations(sent_sum, aspects_sum) -> List[str]:
        out: List[str] = []
        if sent_sum:
            neg = sent_sum.get("negative_percent", 0)
            if neg > 40:
                out.append("Priority: contact dissatisfied customers and address top complaints immediately.")
            elif neg > 20:
                out.append("Monitor: keep tracking negative trends and investigate root causes.")
        if aspects_sum:
            negs = [a for a in aspects_sum.get("aspects", []) if a.get("polarity", 0) < -10]
            negs.sort(key=lambda a: a.get("polarity", 0))
            if negs:
                top = ", ".join(a["aspect"] for a in negs[:3])
                out.append(f"Focus on improving these aspects: {top}.")
            poss = [a for a in aspects_sum.get("aspects", []) if a.get("polarity", 0) > 30]
            poss.sort(key=lambda a: a.get("polarity", 0), reverse=True)
            if poss:
                top = ", ".join(a["aspect"] for a in poss[:2])
                out.append(f"Leverage strengths in marketing: {top}.")
        if not out:
            out.append("Continue monitoring customer feedback and maintain current quality standards.")
        return out
