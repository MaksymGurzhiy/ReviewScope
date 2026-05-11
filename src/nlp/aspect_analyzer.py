"""
Aspect-Based Sentiment Analysis (ABSA) — domain-agnostic version.

Why dynamic extraction
======================
A static aspect lexicon cannot work across domains. ``atmosphere = ["loud",
"music"]`` is fine for a hotel but spuriously matches every Echo review
("loud sound", "play music"). Same story for ``cleanliness = ["clean"]``
matching "clean sound" or "clean look". So the lexicon was killing
result quality for any non-hospitality dataset.

Approach
========
1. Tag the entire corpus with spaCy and collect *noun chunks* — short
   noun phrases ("battery life", "sound quality", "front desk", "side
   effects"). These are the natural unit for an aspect.
2. Normalise each chunk to its **head noun** (or 1–2 word phrase) and
   filter out:
   - stopwords / pronouns,
   - generic placeholders ("thing", "stuff", "product", "item", ...),
   - chunks that appear in fewer than ``min_count`` reviews.
3. Per review, for each surviving aspect: locate every mention,
   compute local sentiment from a ±WINDOW word context (lexicon +
   negation handling, exactly as before). If the context is neutral,
   fall back to the review-level BERT sentiment.
4. Aggregate across the corpus and keep the top-K aspects by mention
   count.

Output schema is unchanged, so the API / UI / PDF do not need any
adaptation. The list of aspects now reflects what people actually talk
about in the uploaded dataset.
"""
import logging
import random
import re
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

import spacy

logger = logging.getLogger(__name__)


POSITIVE_WORDS = {
    "great", "excellent", "good", "amazing", "perfect", "love", "best", "awesome",
    "wonderful", "fantastic", "outstanding", "superb", "brilliant", "nice", "happy",
    "satisfied", "friendly", "fast", "clean", "delicious", "fresh", "comfortable",
    "easy", "smooth", "quick", "helpful", "beautiful", "convenient", "quiet",
    "recommend", "loved", "liked", "favorite",
}
NEGATIVE_WORDS = {
    "bad", "poor", "terrible", "horrible", "awful", "worst", "rude", "slow",
    "expensive", "overpriced", "dirty", "broken", "defective", "stale", "cold",
    "disappointing", "disappointed", "useless", "annoying", "buggy", "laggy",
    "uncomfortable", "noisy", "smelly", "wait", "waited", "delayed", "late",
    "hate", "hated", "waste", "worthless", "bug", "crash", "fail", "failed",
    "loud", "boring", "frustrating", "frustrated",
}
NEGATIONS = {"not", "no", "never", "n't", "without", "isn't", "don't", "didn't", "wasn't", "won't", "cannot", "can't"}

WINDOW = 6  # words on each side of the aspect mention

# Generic placeholders that should never become an aspect on their own.
# (They survive POS filtering because they are nouns, but carry no info.)
GENERIC_NOUNS = {
    "thing", "things", "stuff", "way", "ways", "time", "times", "lot", "lots",
    "bit", "bits", "kind", "kinds", "type", "types", "part", "parts", "item",
    "items", "product", "products", "service", "services", "purchase",
    "experience", "review", "reviews", "amount", "side", "fact", "case",
    "issue", "issues", "problem", "problems",  # too generic; kept as fallback only
    "everything", "anything", "nothing", "something",
    "someone", "anyone", "everyone", "nobody",
    "people", "person", "everybody",
    "day", "days", "week", "weeks", "month", "months", "year", "years",
    "hour", "hours", "minute", "minutes",
    "today", "yesterday", "tomorrow",
    "home", "house",  # often generic
    "i", "me", "my", "you", "we", "they", "he", "she", "it",
    # Numerals / quantifiers spaCy mis-tags as nouns (NUM is dropped via POS,
    # but PRON/NOUN slip through for words like "one", "first").
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "first", "second", "third", "next", "last", "few",
    # Short "nan" string from empty CSV cells coerced via str().
    "nan", "none", "null", "n/a", "na",
}

# Words that spaCy regularly mis-tags as nouns but are really verbs/adjectives
# in review English ("love this thing", "works great", "fun for kids").
# Treating them as aspects produces nonsense like 'love: 100% positive'.
VERB_HOMOGRAPH_BLOCKLIST = {
    "love", "loves", "loved", "loving",
    "like", "likes", "liked", "liking",
    "hate", "hates", "hated", "hating",
    "want", "wants", "wanted",
    "need", "needs", "needed",
    "use", "uses", "used", "using",
    "work", "works", "worked", "working",
    "buy", "buys", "bought", "buying",
    "try", "tries", "tried", "trying",
    "fun", "joy", "blast",
    "wish", "wishes",
    "thanks", "thank",
    "feel", "feels", "felt",
    "look", "looks", "looked",
    "go", "goes", "went",
    "get", "gets", "got",
    "make", "makes", "made",
    "do", "does", "did", "done",
    "say", "says", "said",
}

# Cap on number of aspects we report so the UI stays readable.
MAX_ASPECTS = 15

# spaCy POS-tagging is slow on big corpora, but we don't actually need to
# look at every review to *discover* what people talk about - a 3k-row
# sample picks up all aspects with mention rate >= 0.5%. After discovery,
# the full dataset is scored via regex which is essentially free.
DISCOVERY_SAMPLE_SIZE = 3000

# Domain-name filter (analogue of max_df in TF-IDF).
#
# Words that show up in >MAX_DOC_FREQ_DOMINANT of the reviews are almost
# always the product/category name itself ("airpod" in an AirPods dataset,
# "echo" in an Echo dataset, "hotel" in hotel reviews, "park" in Disneyland
# reviews). They are not aspects of *quality* - they're just the subject
# everyone is talking about, so polarity stats on them are misleading.
#
# Three-tier check makes this safe across domains:
#   - Tier 1 (unconditional): word in >UNCONDITIONAL_DOC_FREQ of the corpus
#     is the domain name no matter what.
#   - Tier 2 (relative): word in >MAX_DOC_FREQ AND >= DOMINANCE_FACTOR
#     times more frequent than the 3rd-place candidate. Protects legitimate
#     frequent aspects ("room" in hotels - frequent but not dominant
#     relative to "staff", "breakfast", ...).
#   - Tier 3 (compound head): the same 1-gram is the leading token of >=2
#     different 2-grams in the candidate list (e.g. "airpods battery",
#     "airpods volume" -> "airpods" is the product name).
UNCONDITIONAL_DOC_FREQ = 0.85
MAX_DOC_FREQ = 0.5
DOMINANCE_FACTOR = 2.0


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _score_window(tokens: List[str], pos: int, span: int = 1) -> Optional[str]:
    """Return 'positive', 'negative' or None for the window around tokens[pos:pos+span]."""
    left = max(0, pos - WINDOW)
    right = min(len(tokens), pos + span + WINDOW)
    window = tokens[left:right]

    pos_score = 0
    neg_score = 0
    negate = False
    for w in window:
        if w in NEGATIONS:
            negate = True
            continue
        if w in POSITIVE_WORDS:
            if negate:
                neg_score += 1
            else:
                pos_score += 1
            negate = False
        elif w in NEGATIVE_WORDS:
            if negate:
                pos_score += 1
            else:
                neg_score += 1
            negate = False
        else:
            negate = False

    if pos_score == 0 and neg_score == 0:
        return None
    return "positive" if pos_score >= neg_score else "negative"


# Singleton spaCy pipeline. Loaded lazily so importing this module is cheap.
_NLP: Optional[spacy.Language] = None


def _get_nlp() -> spacy.Language:
    global _NLP
    if _NLP is None:
        logger.info("Loading spaCy en_core_web_sm for ABSA + opinion mining...")
        # Keep all components: parser (for dep-parsed opinion words) and
        # NER (so the keyword extractor can drop ORG / PERSON / PRODUCT
        # entities without a hand-curated brand list). Lemmatizer makes
        # "airpods"/"airpod", "ears"/"ear" merge into the same aspect.
        _NLP = spacy.load("en_core_web_sm")
    return _NLP


def _normalise_chunk(chunk) -> str:
    """
    Reduce a spaCy noun chunk to its informative core.

    - Drop determiners, pronouns, adjectives — anything that isn't a noun.
    - Drop tokens that carry sentiment ("great product" -> "product").
    - Lemmatise so plural/singular variants merge ("ears" -> "ear").
    - Keep at most the last 2 noun tokens to allow compound nouns
      ("battery life", "echo dot") while avoiding long phrases.
    - If after filtering only sentiment/verb-homograph tokens survive,
      return "" so the caller skips this chunk.
    """
    keep = []
    for tok in chunk:
        if tok.pos_ not in {"NOUN", "PROPN"}:
            continue
        lemma = (tok.lemma_ or tok.text).lower().strip()
        if not lemma:
            continue
        if lemma in POSITIVE_WORDS or lemma in NEGATIVE_WORDS:
            continue
        if lemma in VERB_HOMOGRAPH_BLOCKLIST:
            continue
        if len(lemma) < 3 or not lemma.isalpha():
            continue
        keep.append(lemma)
    if not keep:
        return ""
    if len(keep) > 2:
        keep = keep[-2:]
    return " ".join(keep)


class AspectAnalyzer:
    """
    Domain-agnostic ABSA.

    Two-step usage:
        analyzer = AspectAnalyzer()
        analyzer.fit(reviews)          # learns aspects from the corpus
        analyzer.analyze_reviews(reviews)
        analyzer.aggregate(reviews)
    """

    def __init__(
        self,
        min_count: int = 10,
        min_pct: float = 0.005,
        max_aspects: int = MAX_ASPECTS,
        extra_blocklist: Optional[List[str]] = None,
    ):
        # Minimum absolute count of reviews mentioning the aspect.
        self.min_count = min_count
        # Minimum fraction of reviews mentioning the aspect (0.5%).
        self.min_pct = min_pct
        self.max_aspects = max_aspects
        # Domain-specific words to never accept as aspects (e.g. tokens from
        # the uploaded file name like "airpods" or "amazon"). These are
        # lemmatised below so both "airpods" and "airpod" get blocked.
        self.extra_blocklist: set[str] = {
            w.strip().lower() for w in (extra_blocklist or []) if w and w.strip()
        }
        self.aspects: List[str] = []
        self._patterns: Dict[str, re.Pattern] = {}

    # ---------------- aspect discovery ----------------
    def fit(self, reviews: List[Dict[str, Any]]) -> List[str]:
        """Discover aspects from the supplied reviews."""
        nlp = _get_nlp()
        # Drop blank / NaN texts so they don't count as a "nan" aspect.
        all_texts = [
            t for t in (str(r.get("text") or "").strip() for r in reviews)
            if t and t.lower() not in {"nan", "none", "null", "n/a", "na"}
        ]
        n_total = len(all_texts)
        if n_total == 0:
            self.aspects = []
            return self.aspects

        # Lemmatise + canonicalise the user-provided blocklist so that
        # blocking "airpods" also blocks "airpod" (lemma) and "air pod"
        # (split tokenisation by spaCy on rare brand names).
        lemmatised_blocklist: set[str] = set(self.extra_blocklist)
        if self.extra_blocklist:
            for tok in nlp(" ".join(self.extra_blocklist)):
                if tok.lemma_:
                    lemmatised_blocklist.add(tok.lemma_.lower())
                lemmatised_blocklist.add(tok.text.lower())
        # Canonical form = no spaces, trailing 's' stripped. Catches cases
        # where spaCy tokenises "AirPod" as 2 tokens "air"+"pod" so the
        # noun-chunk normaliser produces "air pod" (a 2-gram).
        canonical_blocklist: set[str] = {
            re.sub(r"\s+", "", w).rstrip("s") for w in lemmatised_blocklist if len(w) >= 4
        }

        # Sample for discovery to keep tagging fast on big corpora.
        if n_total > DISCOVERY_SAMPLE_SIZE:
            rng = random.Random(42)
            texts = rng.sample(all_texts, DISCOVERY_SAMPLE_SIZE)
            logger.info(
                "Sampled %d of %d reviews for aspect discovery",
                len(texts), n_total,
            )
        else:
            texts = all_texts
        n_docs = len(texts)

        # Per-document set of aspect candidates so we count *documents*, not raw mentions.
        doc_freq: Counter = Counter()
        logger.info("Extracting aspect candidates from %d reviews via spaCy...", n_docs)

        for doc in nlp.pipe(texts, batch_size=64, n_process=1):
            seen_in_doc = set()
            for chunk in doc.noun_chunks:
                if chunk.root.pos_ not in {"NOUN", "PROPN"}:
                    continue
                if chunk.root.lemma_.lower() in VERB_HOMOGRAPH_BLOCKLIST:
                    continue
                norm = _normalise_chunk(chunk)
                if not norm:
                    continue
                if norm in GENERIC_NOUNS:
                    continue
                if all(w in GENERIC_NOUNS for w in norm.split()):
                    continue
                # Domain-specific blocklist (e.g. product name from filename).
                if norm in lemmatised_blocklist:
                    continue
                if any(w in lemmatised_blocklist for w in norm.split()):
                    continue
                # Canonical match catches "air pod" when blocklist has "airpods".
                norm_canon = re.sub(r"\s+", "", norm).rstrip("s")
                if norm_canon in canonical_blocklist:
                    continue
                seen_in_doc.add(norm)
            doc_freq.update(seen_in_doc)

        # Threshold is computed on the FULL corpus size, not just the sample,
        # otherwise we'd accept too many noisy candidates from small samples.
        threshold_pct = int(n_total * self.min_pct)
        # ...but if we sampled, scale the threshold down proportionally so it
        # actually applies to the sample we tagged.
        if n_docs < n_total:
            threshold_pct = int(threshold_pct * (n_docs / n_total))
        # Adaptive absolute floor: tiny corpora need a low bar (otherwise the
        # ABSA section is empty for any sample/demo), large corpora keep the
        # strict 10-mention bar so single-mention noise never surfaces.
        if n_total <= 30:
            adaptive_floor = 2
        elif n_total <= 100:
            adaptive_floor = 3
        elif n_total <= 500:
            adaptive_floor = 4
        elif n_total <= 2000:
            adaptive_floor = 6
        else:
            adaptive_floor = self.min_count  # 10 by default
        threshold = max(adaptive_floor, threshold_pct)
        survivors = [(a, c) for a, c in doc_freq.most_common() if c >= threshold]

        # Deduplicate: prefer longer/more specific phrase if both forms exist.
        # E.g. keep "battery life" over "battery" if both pass the threshold.
        survivors_dict: Dict[str, int] = dict(survivors)
        deduped: List[Tuple[str, int]] = []
        for asp, cnt in survivors:
            words = asp.split()
            if len(words) == 1:
                # Drop the single noun if a 2-gram containing it exists with >=70% of its count.
                bigger = [(o, oc) for o, oc in survivors_dict.items()
                          if o != asp and asp in o.split() and oc >= cnt * 0.7]
                if bigger:
                    continue
            deduped.append((asp, cnt))

        # Strip product-name candidates (max_df-style filter).
        # See module-level docstring of _strip_domain_names.
        deduped = self._strip_domain_names(deduped, n_docs=n_docs)

        self.aspects = [a for a, _ in deduped[: self.max_aspects]]
        self._patterns = {
            a: re.compile(r"\b" + re.escape(a) + r"\b", re.IGNORECASE) for a in self.aspects
        }
        logger.info(
            "Discovered %d aspects (threshold=%d): %s",
            len(self.aspects), threshold, self.aspects,
        )
        return self.aspects

    @staticmethod
    def _strip_domain_names(
        candidates: List[Tuple[str, int]],
        *,
        n_docs: int,
    ) -> List[Tuple[str, int]]:
        """Drop words that look like the product/category name.

        Order:
          1. Tier 3 first (compound-head detection) - cleanest signal.
             Reduces "<head> <word>" 2-grams to "<word>" and removes the
             head itself if it also appears as a 1-gram.
          2. Then Tier 1 / Tier 2 on what's left, single iteration only
             so we never accidentally strip legitimate top aspects.
        """
        if not candidates:
            return candidates

        result = list(candidates)
        dropped: set[str] = set()

        # ----- Tier 3: compound head detection (data-driven) -----
        head_counts: Counter = Counter()
        for word, _ in result:
            parts = word.split()
            if len(parts) == 2:
                head_counts[parts[0]] += 1
        compound_heads = {h for h, c in head_counts.items() if c >= 2}

        if compound_heads:
            cleaned: List[Tuple[str, int]] = []
            seen: dict[str, int] = {}
            for word, count in result:
                parts = word.split()
                if len(parts) == 2 and parts[0] in compound_heads:
                    word = parts[1]
                if word in compound_heads:
                    # the bare head ("airpods", "echo") - drop entirely
                    continue
                if word in seen:
                    seen[word] = max(seen[word], count)
                else:
                    seen[word] = count
                    cleaned.append((word, count))
            # rebuild (preserve order, but use max count after merge)
            result = [(w, seen[w]) for w, _ in cleaned]
            dropped.update(compound_heads)

        # ----- Tier 1 + Tier 2: single-pass on remaining top word -----
        if result:
            unconditional = int(n_docs * UNCONDITIONAL_DOC_FREQ)
            max_count = int(n_docs * MAX_DOC_FREQ)
            top_word, top_count = result[0]
            should_drop = False
            if top_count > unconditional:
                should_drop = True
            elif top_count > max_count and len(result) >= 3:
                ref_count = result[2][1]
                if ref_count > 0 and top_count >= ref_count * DOMINANCE_FACTOR:
                    should_drop = True
            if should_drop:
                dropped.add(top_word)
                result = result[1:]

        if dropped:
            logger.info("Filtered out domain-name aspects: %s", sorted(dropped))
        return result

    # ---------------- per-review tagging ----------------
    def analyze_review(self, text: str, doc_sentiment: Optional[str] = None) -> Dict[str, str]:
        if not self.aspects:
            return {}
        tokens = _tokenize(text)
        aspects_found: Dict[str, str] = {}

        for aspect, pattern in self._patterns.items():
            match = pattern.search(text)
            if not match:
                continue
            first_word = aspect.split()[0]
            try:
                pos = tokens.index(first_word)
            except ValueError:
                pos = -1

            span = len(aspect.split())
            local = _score_window(tokens, pos, span=span) if pos >= 0 else None
            if local is None and doc_sentiment:
                ds = doc_sentiment.upper()
                if ds == "POSITIVE":
                    local = "positive"
                elif ds == "NEGATIVE":
                    local = "negative"
                else:
                    local = "neutral"
            aspects_found[aspect] = local or "neutral"

        return aspects_found

    def analyze_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.aspects:
            self.fit(reviews)
        for r in reviews:
            r["aspects"] = self.analyze_review(
                r.get("text", ""),
                doc_sentiment=r.get("sentiment"),
            )
        return reviews

    # ---------------- aggregation ----------------
    # English stopwords used to filter context words around aspects so we
    # only surface meaningful collocations.
    _CONTEXT_STOP = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "must", "shall",
        "this", "that", "these", "those", "it", "its", "they", "them",
        "we", "us", "our", "i", "me", "my", "you", "your", "he", "him",
        "his", "she", "her", "of", "in", "on", "at", "to", "for", "with",
        "by", "from", "as", "and", "or", "but", "if", "then", "than", "so",
        "too", "very", "really", "just", "more", "most", "much", "some",
        "any", "all", "no", "not", "out", "up", "down", "off", "over",
        "under", "again", "also", "only", "even", "still", "now", "ever",
        "never", "always", "well", "good", "bad", "great", "nice",
    })

    def aggregate(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        per_aspect: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
        )
        # For each aspect, collect: review texts (+ their sentiment) and
        # context word frequencies for richer "Conclusion" output.
        per_aspect_reviews: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)
        per_aspect_ctx_pos: Dict[str, Counter] = defaultdict(Counter)
        per_aspect_ctx_neg: Dict[str, Counter] = defaultdict(Counter)

        for r in reviews:
            text = str(r.get("text") or "")
            doc_sent = str(r.get("sentiment") or "").upper()
            for aspect, sent in (r.get("aspects") or {}).items():
                per_aspect[aspect][sent] += 1
                per_aspect[aspect]["total"] += 1
                per_aspect_reviews[aspect].append((text, sent, doc_sent))

        # Dependency-parsed opinion-word mining. ONE extra spaCy pass over
        # a capped sample of texts that mention any aspect: for each aspect
        # we extract the syntactic OPINION token (adj/verb/adv connected to
        # the aspect noun via amod/nsubj/acomp/dobj/conj relations).
        # Way more interpretable than raw word-window context.
        per_aspect_opinions_pos, per_aspect_opinions_neg = self._mine_opinions(
            per_aspect_reviews
        )

        # Fallback: also keep cheap word-window collocations so we still
        # have *something* if dep-parsing yields nothing for an aspect.
        for aspect, samples in per_aspect_reviews.items():
            for text, sent, _doc_sent in samples:
                tokens = _tokenize(text)
                first = aspect.split()[0]
                try:
                    pos = tokens.index(first)
                except ValueError:
                    continue
                span = len(aspect.split())
                left = max(0, pos - 5)
                right = min(len(tokens), pos + span + 5)
                for w in tokens[left:right]:
                    if w in self._CONTEXT_STOP or w in aspect.split():
                        continue
                    if len(w) < 3 or w in POSITIVE_WORDS or w in NEGATIVE_WORDS:
                        continue
                    if not w.isalpha():
                        continue
                    if sent == "positive":
                        per_aspect_ctx_pos[aspect][w] += 1
                    elif sent == "negative":
                        per_aspect_ctx_neg[aspect][w] += 1

        result = []
        for aspect, counts in per_aspect.items():
            total = counts["total"]
            pos_pct = (counts["positive"] / total * 100) if total else 0
            neg_pct = (counts["negative"] / total * 100) if total else 0

            # Pick 1 short representative review per polarity. For an
            # example to count as positive we require BOTH the local
            # aspect sentiment AND the review-level (BERT) sentiment to
            # agree; same for negative. This eliminates contradictions
            # like a negative review being shown as positive evidence
            # because of an ambiguous word in the window.
            pos_examples = [
                t for t, s, ds in per_aspect_reviews[aspect]
                if s == "positive" and ds == "POSITIVE" and 40 <= len(t) <= 200
            ]
            neg_examples = [
                t for t, s, ds in per_aspect_reviews[aspect]
                if s == "negative" and ds == "NEGATIVE" and 40 <= len(t) <= 200
            ]
            pos_examples.sort(key=len)
            neg_examples.sort(key=len)

            # Prefer dep-parsed opinion words; if empty, fall back to the
            # cheap word-window context (already collected above).
            ops_pos = per_aspect_opinions_pos.get(aspect)
            ops_neg = per_aspect_opinions_neg.get(aspect)
            opinions_pos_list = (
                [w for w, _ in ops_pos.most_common(5)] if ops_pos
                else [w for w, _ in per_aspect_ctx_pos[aspect].most_common(4)]
            )
            opinions_neg_list = (
                [w for w, _ in ops_neg.most_common(5)] if ops_neg
                else [w for w, _ in per_aspect_ctx_neg[aspect].most_common(4)]
            )

            result.append({
                "aspect": aspect,
                "total_mentions": total,
                "positive": counts["positive"],
                "negative": counts["negative"],
                "neutral": counts["neutral"],
                "positive_pct": round(pos_pct, 1),
                "negative_pct": round(neg_pct, 1),
                "polarity": round(pos_pct - neg_pct, 1),
                # New: dep-parsed opinion words (with fallback to context).
                "opinions_positive": opinions_pos_list,
                "opinions_negative": opinions_neg_list,
                # Legacy fields kept for backward-compat with PDF / older UIs.
                "context_positive": opinions_pos_list,
                "context_negative": opinions_neg_list,
                "example_positive": pos_examples[0] if pos_examples else None,
                "example_negative": neg_examples[0] if neg_examples else None,
            })
        result.sort(key=lambda x: x["total_mentions"], reverse=True)
        return {"aspects": result, "total_aspects": len(result)}

    # ----------------------------------------------------------------- #
    # Dependency-parsed opinion-word mining
    # ----------------------------------------------------------------- #
    # Cap how many texts we re-tag for opinion mining. Each spaCy doc costs
    # ~1ms even on CPU; 3000 texts is plenty of signal across all aspects.
    _OPINION_SAMPLE_CAP = 3000

    # Sentiment-bearing dependency relations between an aspect noun and its
    # opinion modifier:
    #   amod      -> "great service" (adjective directly modifies aspect)
    #   acomp     -> "service is great" (adj complement of copula)
    #   nsubj     -> "service sucks" (verb's subject)
    #   dobj/pobj -> "love the service" (verb takes aspect as object)
    #   conj      -> coordinated "service was slow and rude"
    #   advmod    -> adverb modifier of an opinion verb
    _OPINION_DEPS = {"amod", "acomp", "attr", "nsubj", "dobj", "pobj",
                     "conj", "advmod", "xcomp", "ccomp"}

    @staticmethod
    def _is_opinion_token(tok) -> bool:
        if not tok or not tok.text:
            return False
        lemma = (tok.lemma_ or tok.text).lower().strip()
        if not lemma or not lemma.isalpha() or len(lemma) < 3:
            return False
        if lemma in {"be", "have", "do", "get", "go", "say", "make", "take",
                     "come", "see", "look", "feel", "think", "know", "want"}:
            return False
        if tok.pos_ not in {"ADJ", "ADV", "VERB"}:
            return False
        return True

    def _opinion_for_aspect_in_doc(self, doc, aspect_first_word: str
                                   ) -> List[str]:
        """Return opinion lemmas dep-linked to any token whose lemma == aspect."""
        opinions: List[str] = []
        for tok in doc:
            tok_lemma = (tok.lemma_ or tok.text).lower()
            if tok_lemma != aspect_first_word:
                continue
            # Walk parent and children for opinion-bearing modifiers.
            for cand in (tok.head, *tok.children, *tok.head.children):
                if cand is tok:
                    continue
                if cand.dep_ not in self._OPINION_DEPS \
                        and tok.dep_ not in self._OPINION_DEPS:
                    continue
                if not self._is_opinion_token(cand):
                    continue
                opinions.append((cand.lemma_ or cand.text).lower())
                # Adverb modifiers of the opinion ("really slow") — pick up too.
                for child in cand.children:
                    if child.dep_ == "advmod" and self._is_opinion_token(child):
                        lem = (child.lemma_ or child.text).lower()
                        if lem not in {"so", "very", "too", "really", "just"}:
                            opinions.append(lem)
        return opinions

    def _mine_opinions(
        self,
        per_aspect_reviews: Dict[str, List[Tuple[str, str, str]]],
    ) -> Tuple[Dict[str, Counter], Dict[str, Counter]]:
        """Re-tag a sample of aspect-mentioning reviews and pull dep-linked
        opinion words per aspect, separated by aggregated sentiment band."""
        if not per_aspect_reviews:
            return {}, {}

        # Pool unique texts with their dominant sentiment per aspect, but
        # because the same text may mention multiple aspects we re-tag each
        # text once and rely on _opinion_for_aspect_in_doc to filter.
        text_meta: Dict[str, Tuple[str, Dict[str, str]]] = {}
        for aspect, samples in per_aspect_reviews.items():
            first = aspect.split()[0]
            for text, sent, _doc_sent in samples:
                if not text:
                    continue
                key = text
                if key not in text_meta:
                    text_meta[key] = (text, {})
                text_meta[key][1][first] = sent

        all_texts = list(text_meta.values())
        if len(all_texts) > self._OPINION_SAMPLE_CAP:
            all_texts = random.sample(all_texts, self._OPINION_SAMPLE_CAP)

        nlp = _get_nlp()
        per_aspect_pos: Dict[str, Counter] = defaultdict(Counter)
        per_aspect_neg: Dict[str, Counter] = defaultdict(Counter)

        t0 = time.perf_counter()
        for doc, (_, aspects_in_text) in zip(
            nlp.pipe([t for t, _ in all_texts], batch_size=64, n_process=1),
            all_texts,
        ):
            for first_word, sent in aspects_in_text.items():
                ops = self._opinion_for_aspect_in_doc(doc, first_word)
                if not ops:
                    continue
                bucket = (per_aspect_pos[first_word]
                          if sent == "positive"
                          else per_aspect_neg[first_word]
                          if sent == "negative"
                          else None)
                if bucket is None:
                    continue
                for op in ops:
                    bucket[op] += 1

        # The keys above are aspect-first-word; we need them keyed by FULL
        # aspect string. Rebuild by mapping each aspect's first word back.
        out_pos: Dict[str, Counter] = {}
        out_neg: Dict[str, Counter] = {}
        for aspect in per_aspect_reviews.keys():
            first = aspect.split()[0]
            if first in per_aspect_pos:
                out_pos[aspect] = per_aspect_pos[first]
            if first in per_aspect_neg:
                out_neg[aspect] = per_aspect_neg[first]

        logger.info(
            "ABSA opinion mining: %d texts re-tagged in %.1fs (aspects=%d)",
            len(all_texts), time.perf_counter() - t0, len(per_aspect_reviews),
        )
        return out_pos, out_neg
