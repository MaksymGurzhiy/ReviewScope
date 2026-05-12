"""
Keyword Extraction — opinion-focused log-odds with POS / NER filtering.

Why we abandoned KeyBERT-by-band
================================
KeyBERT ranks candidates by *semantic similarity* to a big "5-star" or
"1-star" document. That is a perfectly fine information-retrieval signal,
but it is **not** what reviewers want. KeyBERT happily returns
``audiobooks``, ``radio``, ``automatically``, ``amazon`` for the AirPods
dataset because they are characteristic of the band — even though none
of them carry an opinion.

What we do instead
==================
1. Tokenise every review with spaCy (already loaded for ABSA — free).
2. Build candidate vocabulary that is **opinion-bearing by construction**:
   * single tokens whose POS is ADJ / ADV / VERB (incl. participles like
     ``disappointed``, ``broken``) — pure NOUN/PROPN are dropped;
   * bigrams of (ADJ|VERB)+NOUN — ``slow service``, ``perfect sound``,
     ``stopped working``;
   * NER ents with type ORG / PERSON / PRODUCT / GPE are blocklisted —
     this kills brand and place names without any hand-curated stoplist.
3. Score every candidate with **log-odds-ratio with informative Dirichlet
   prior** (Monroe, Colaresi & Quinn, "Fightin' Words", 2008). The
   resulting z-score tells you *how much more characteristic* the term is
   for the band, controlling for overall corpus frequency. This is the
   gold standard for "what makes group X talk differently from group Y".
4. Boost candidates that already exist in the opinion lexicon
   (POSITIVE_WORDS / NEGATIVE_WORDS shared with the aspect analyzer) so
   that obvious sentiment words always rise above neutral nouns.

The output schema is unchanged so the API / UI / PDF do not need any
adaptation. Phrases come back sorted by descending z-score, with the raw
score (not similarity) in the second slot.
"""
from __future__ import annotations

import logging
import math
import random
import re
import time
from collections import Counter
from typing import Dict, Iterable, List, Optional, Tuple

import spacy
from spacy.language import Language

from src.nlp.aspect_analyzer import (
    NEGATIVE_WORDS,
    POSITIVE_WORDS,
    VERB_HOMOGRAPH_BLOCKLIST,
)

logger = logging.getLogger(__name__)


GROUP_SAMPLE_CAP = 1500           # docs per band fed to spaCy
MIN_TOKEN_LEN = 3
NER_BLOCKLIST = {"ORG", "PERSON", "PRODUCT", "GPE", "NORP", "FAC", "LOC"}
OPINION_BOOST = 1.6               # multiplied into z-score
MAX_PHRASES_PER_BAND = 10

# Pure stop-words: generic English fillers + conversational junk.
_STOP = frozenset({
    "the", "a", "an", "and", "or", "but", "if", "then", "than", "so",
    "is", "are", "was", "were", "be", "been", "being", "am",
    "have", "has", "had", "having",
    "do", "does", "did", "doing",
    "will", "would", "could", "should", "may", "might", "can", "must",
    "this", "that", "these", "those", "it", "its", "they", "them",
    "we", "us", "our", "i", "me", "my", "you", "your", "he", "him",
    "his", "she", "her", "hers",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "as",
    "out", "up", "down", "off", "over", "under", "into", "onto",
    "again", "also", "only", "even", "still", "now", "ever", "never",
    "always", "well", "just", "too", "very", "really", "quite",
    "no", "not", "yes", "ok", "okay", "oh", "yeah", "yep", "nope",
    "got", "get", "gets", "getting",
    "thing", "things", "stuff", "way", "ways",
    "lot", "lots", "bit", "kind", "kinds", "type", "types",
    "more", "most", "much", "many", "some", "any", "all", "each",
    "one", "two", "three", "first", "second", "next", "last",
    "today", "yesterday", "tomorrow", "now", "later", "soon",
    "would", "should", "could", "won't", "don't", "didn't", "isn't",
    "n't", "'s", "'re", "'ve", "'ll", "'d", "'m",
    # NaN / placeholders
    "nan", "none", "null", "n/a", "na",
})


def _bucket(review: dict) -> str:
    """'pos' / 'neu' / 'neg' from rating, falling back to BERT label."""
    r = review.get("rating")
    try:
        rating = int(r) if r is not None else 0
    except (ValueError, TypeError):
        rating = 0
    if rating >= 4:
        return "pos"
    if rating == 3:
        return "neu"
    if 1 <= rating <= 2:
        return "neg"
    sent = (review.get("sentiment") or "").upper()
    if sent == "POSITIVE":
        return "pos"
    if sent == "NEGATIVE":
        return "neg"
    return "neu"


# Singleton spaCy. Re-use whatever the aspect analyzer loaded.
_NLP: Optional[Language] = None


def _get_nlp() -> Language:
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load(
                "en_core_web_sm",
                disable=["textcat"],  # keep tagger, parser, NER, lemmatizer
            )
        except OSError:
            logger.warning(
                "en_core_web_sm not installed; falling back to blank en. "
                "POS / NER filtering will be disabled."
            )
            _NLP = spacy.blank("en")
    return _NLP


# --------------------------------------------------------------------- #
# Candidate extraction
# --------------------------------------------------------------------- #
def _is_blocklisted_ner(token) -> bool:
    return token.ent_type_ in NER_BLOCKLIST


def _good_token(token) -> bool:
    """True if the token is a content word we want to keep."""
    if token.is_space or token.is_punct or token.is_digit:
        return False
    if token.like_url or token.like_email or token.like_num:
        return False
    text = token.lemma_.lower() or token.text.lower()
    if not text.isalpha():
        return False
    if len(text) < MIN_TOKEN_LEN:
        return False
    if text in _STOP:
        return False
    if text in VERB_HOMOGRAPH_BLOCKLIST:
        return False
    if _is_blocklisted_ner(token):
        return False
    return True


def _candidates_from_doc(doc) -> List[str]:
    """Return opinion-bearing 1- and 2-grams from a single spaCy doc."""
    out: List[str] = []
    tokens = [t for t in doc if not (t.is_space or t.is_punct)]

    # Unigrams: only ADJ / ADV / VERB participles (sentiment-bearing POS).
    for t in tokens:
        if not _good_token(t):
            continue
        pos = t.pos_
        if pos == "ADJ" or pos == "ADV":
            out.append(t.lemma_.lower())
        elif pos == "VERB":
            # past participles like "disappointed", "broken", "stopped"
            tag = t.tag_
            if tag in {"VBN", "VBD", "VBG"} or t.lemma_ != t.text.lower():
                out.append(t.lemma_.lower())

    # Bigrams: (ADJ|VERB) + NOUN (e.g. "slow service", "stopped working").
    # We walk the linear sequence and emit any adjacent pair that matches.
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i + 1]
        if not _good_token(a) or not _good_token(b):
            continue
        if _is_blocklisted_ner(a) or _is_blocklisted_ner(b):
            continue
        if a.pos_ in {"ADJ", "VERB"} and b.pos_ in {"NOUN", "PROPN"}:
            phrase = f"{a.lemma_.lower()} {b.lemma_.lower()}"
            out.append(phrase)
        elif a.pos_ in {"NOUN", "PROPN"} and b.pos_ in {"VERB"}:
            # "battery died", "service sucks"
            phrase = f"{a.lemma_.lower()} {b.lemma_.lower()}"
            out.append(phrase)
    return out


# --------------------------------------------------------------------- #
# Log-odds with informative Dirichlet prior (Monroe, Colaresi, Quinn 2008)
# --------------------------------------------------------------------- #
def _log_odds(
    target: Counter,
    background: Counter,
    *,
    alpha: float = 0.01,
) -> Dict[str, float]:
    """Return z-scored log-odds ratio for every term in `target`.

    target     : Counter of term -> count in the focal band
    background : Counter of term -> count in EVERYTHING ELSE
    alpha      : Dirichlet smoothing pseudo-count
    """
    n_t = sum(target.values())
    n_b = sum(background.values())
    if n_t == 0 or n_b == 0:
        return {}

    # Combined background prior: (target ∪ background) acts as the
    # informative prior alpha_w. Monroe's eq. (16).
    prior = Counter()
    prior.update(target)
    prior.update(background)
    n_p = sum(prior.values())

    a0 = alpha * n_p  # total pseudo-count

    out: Dict[str, float] = {}
    for w, y_t in target.items():
        y_b = background.get(w, 0)
        a_w = alpha * prior[w]
        # log-odds of word w in target vs background, with prior
        num_t = y_t + a_w
        den_t = (n_t + a0) - num_t
        num_b = y_b + a_w
        den_b = (n_b + a0) - num_b
        if num_t <= 0 or den_t <= 0 or num_b <= 0 or den_b <= 0:
            continue
        log_odds = math.log(num_t / den_t) - math.log(num_b / den_b)
        # Approximate variance per Monroe eq. (20)
        var = 1.0 / num_t + 1.0 / num_b
        z = log_odds / math.sqrt(var)
        out[w] = z
    return out


# --------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------- #
class KeywordExtractor:
    """Opinion-focused keyword extraction with POS / NER / log-odds.

    Public surface kept compatible with the previous KeyBERT version:
        extractor = KeywordExtractor(extra_blocklist=blocklist)
        extractor.analyze_reviews(reviews)        # no-op (kept for pipeline)
        extractor.get_summary(reviews, top_n=10)  # main entry point
    """

    def __init__(
        self,
        model_name: str = "en_core_web_sm",  # noqa: ARG002 — kept for API compat
        top_n: int = 10,
        keyphrase_ngram_range: tuple = (1, 2),  # noqa: ARG002 — informational only
        extra_blocklist: List[str] | None = None,
    ):
        self.top_n = top_n
        self._blocklist_canon: set[str] = {
            re.sub(r"\s+", "", w.lower()).rstrip("s")
            for w in (extra_blocklist or [])
            if w and len(w) >= 4
        }
        # Keep raw tokens too so multi-word filename tokens get blocked.
        self._blocklist_raw: set[str] = {
            w.lower() for w in (extra_blocklist or []) if w
        }
        # Lazy spaCy load.
        _ = _get_nlp()

    # Pipeline-compat shim: no per-review keyword field anymore.
    def analyze_reviews(self, reviews: list, top_n: int = 5) -> list:  # noqa: ARG002
        return reviews

    # ----------------------------------------------------------------- #
    def _blocked(self, phrase: str) -> bool:
        for tok in phrase.lower().split():
            canon = tok.rstrip("s")
            if canon in self._blocklist_canon or tok in self._blocklist_raw:
                return True
        return False

    def _band_counters(
        self, reviews: list,
    ) -> Tuple[Counter, Counter, Counter]:
        """Return (pos, neu, neg) Counters of phrase-frequency."""
        groups: Dict[str, List[str]] = {"pos": [], "neu": [], "neg": []}
        for r in reviews:
            text = (r.get("text") or "").strip()
            if not text:
                continue
            groups[_bucket(r)].append(text)

        for k, v in groups.items():
            if len(v) > GROUP_SAMPLE_CAP:
                groups[k] = random.sample(v, GROUP_SAMPLE_CAP)

        nlp = _get_nlp()
        counters: Dict[str, Counter] = {"pos": Counter(), "neu": Counter(), "neg": Counter()}
        for band, docs in groups.items():
            if not docs:
                continue
            t0 = time.perf_counter()
            for doc in nlp.pipe(docs, batch_size=64, n_process=1):
                seen_in_doc = set()  # count document-frequency, not raw
                for cand in _candidates_from_doc(doc):
                    if self._blocked(cand):
                        continue
                    seen_in_doc.add(cand)
                counters[band].update(seen_in_doc)
            logger.info(
                "Keywords: %s band — %d docs tagged in %.1fs (vocab=%d)",
                band, len(docs), time.perf_counter() - t0, len(counters[band]),
            )

        return counters["pos"], counters["neu"], counters["neg"]

    @staticmethod
    def _opinion_boost(phrase: str) -> float:
        """Multiplier for terms that already look like opinions."""
        toks = phrase.lower().split()
        for t in toks:
            if t in POSITIVE_WORDS or t in NEGATIVE_WORDS:
                return OPINION_BOOST
        return 1.0

    def _rank(
        self,
        target: Counter,
        background: Counter,
        *,
        min_count: int,
        top_n: int,
        polarity: str = "",
    ) -> List[Tuple[str, float]]:
        """polarity = 'pos' | 'neg' | '' — filters cross-polarity opinion words
        (e.g. drops 'satisfied' from the negative band when it appears via
        'not satisfied'). Pure log-odds is unaware of negation; this filter
        is the cheapest possible mitigation that doesn't hurt big datasets."""
        if not target:
            return []
        scored = _log_odds(target, background)
        out: List[Tuple[str, str]] = []
        for w, z in scored.items():
            if target[w] < min_count:
                continue
            if z <= 0:  # we only want terms over-represented in target
                continue
            tokens = w.lower().split()
            if polarity == "pos" and any(t in NEGATIVE_WORDS for t in tokens):
                continue
            if polarity == "neg" and any(t in POSITIVE_WORDS for t in tokens):
                continue
            boosted = z * self._opinion_boost(w)
            out.append((w, boosted))
        out.sort(key=lambda x: x[1], reverse=True)
        # Drop near-duplicates: prefer longer phrase if its tokens cover a
        # shorter already-kept one.  ("perfect sound" hides "sound" only if
        # both came out as keywords for the same band.)
        deduped: List[Tuple[str, float]] = []
        kept_tokens: List[set[str]] = []
        for phrase, score in out:
            toks = set(phrase.split())
            # Drop if a kept phrase is a strict subset of this one or vice versa.
            if any(prev <= toks or toks <= prev for prev in kept_tokens):
                # Allow if the longer one is the new candidate — replace.
                if any(prev < toks for prev in kept_tokens):
                    # remove the strict-subset entry
                    deduped = [(p, s) for (p, s), kt in zip(deduped, kept_tokens)
                               if not (kt < toks)]
                    kept_tokens = [kt for kt in kept_tokens if not (kt < toks)]
                else:
                    continue
            deduped.append((phrase, score))
            kept_tokens.append(toks)
            if len(deduped) >= top_n:
                break
        return deduped

    # ----------------------------------------------------------------- #
    def get_summary(self, reviews: list, top_n: int = 10) -> dict:
        n = len(reviews)
        if n == 0:
            return {
                "total_unique_keywords": 0,
                "top_keywords": [],
                "positive_keywords": [],
                "negative_keywords": [],
                "neutral_keywords": [],
            }

        logger.info("Keywords: building summary from %d reviews (log-odds)", n)
        t0 = time.perf_counter()
        pos_c, neu_c, neg_c = self._band_counters(reviews)

        # Adaptive minimum document frequency: tiny corpora need a low bar.
        if n <= 30:
            min_count = 1
        elif n <= 100:
            min_count = 2
        elif n <= 1000:
            min_count = 3
        else:
            min_count = 4

        # For each band, the "background" is the union of the OTHER two
        # bands. This is what makes terms truly distinguishing.
        pos = self._rank(pos_c, neu_c + neg_c,
                         min_count=min_count, top_n=top_n, polarity="pos")
        neg = self._rank(neg_c, pos_c + neu_c,
                         min_count=min_count, top_n=top_n, polarity="neg")
        # Neutral is rarely informative; we still compute it but the UI
        # treats an empty list as "hide this column".
        neu = self._rank(neu_c, pos_c + neg_c,
                         min_count=max(2, min_count), top_n=min(top_n, 6))

        merged: Dict[str, float] = {}
        for kw, sc in pos + neu + neg:
            merged[kw] = max(merged.get(kw, 0.0), sc)
        top = sorted(merged.items(), key=lambda x: x[1], reverse=True)[:20]

        logger.info(
            "Keywords: summary done in %.1fs (pos=%d neu=%d neg=%d, total=%d)",
            time.perf_counter() - t0, len(pos), len(neu), len(neg), len(merged),
        )

        # Round to 2 decimals — z-scores are typically in [0, 8] range so
        # this is enough resolution for the UI bar widths.
        def _fmt(items: Iterable[Tuple[str, float]]) -> List[List]:
            return [[kw, round(float(sc), 2)] for kw, sc in items]

        return {
            "total_unique_keywords": len(merged),
            "top_keywords": _fmt(top),
            "positive_keywords": _fmt(pos),
            "negative_keywords": _fmt(neg),
            "neutral_keywords": _fmt(neu),
        }


# Public re-exports kept for backward-compat with old import statements.
__all__ = ["KeywordExtractor"]
