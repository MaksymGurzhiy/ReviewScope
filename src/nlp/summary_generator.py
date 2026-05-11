"""
Business summary generator.

Produces a human-readable report ("top problems / top strengths") from the
output of the rest of the pipeline. Pure Python, deterministic, no LLM calls.
"""
import re
from typing import Any, Dict, List


def _phrase_signature(phrase: str) -> str:
    """Order-invariant set-of-tokens signature so 'good hotels' /
    'hotels good' / 'hotel good' map to the same signature."""
    tokens = sorted(t for t in re.split(r'\s+', phrase.strip().lower()) if t)
    return ' '.join(tokens)


def _dedupe_phrases(items: List[Any], limit: int) -> List[str]:
    """Return up to `limit` distinct phrases preserving original order."""
    seen: set[str] = set()
    out: List[str] = []
    for entry in items:
        phrase = entry[0] if isinstance(entry, (list, tuple)) else str(entry)
        sig = _phrase_signature(phrase)
        if not sig or sig in seen:
            continue
        seen.add(sig)
        out.append(phrase)
        if len(out) >= limit:
            break
    return out


def _truncate(text: str, limit: int = 160) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


class SummaryGenerator:
    """Generate a structured executive summary."""

    def __init__(self, max_strengths: int = 5, max_problems: int = 5):
        self.max_strengths = max_strengths
        self.max_problems = max_problems

    def generate(
        self,
        *,
        sentiment_summary: Dict[str, Any] | None,
        aspects: Dict[str, Any] | None,
        topics: Dict[str, Any] | None,
        keywords: Dict[str, Any] | None,
        total_reviews: int,
    ) -> str:
        lines: List[str] = []
        lines.append(f"Analyzed {total_reviews} customer reviews.")

        if sentiment_summary:
            pos = sentiment_summary.get("positive_percent", 0)
            neg = sentiment_summary.get("negative_percent", 0)
            neu = sentiment_summary.get("neutral_percent", 0)
            mood = self._mood_label(pos, neg)
            parts = [f"{pos:.1f}% positive"]
            if neu > 0:
                parts.append(f"{neu:.1f}% neutral")
            parts.append(f"{neg:.1f}% negative")
            lines.append(f"Overall sentiment: {mood} ({', '.join(parts)}).")

        # Strengths from aspects
        strengths = self._top_aspects(aspects, polarity=">", limit=self.max_strengths)
        if strengths:
            lines.append("")
            lines.append("Top strengths:")
            for a in strengths:
                lines.append(f"  - {a['aspect']}: {a['positive_pct']:.0f}% positive ({a['total_mentions']} mentions)")

        # Problems from aspects
        problems = self._top_aspects(aspects, polarity="<", limit=self.max_problems)
        if problems:
            lines.append("")
            lines.append("Top problems:")
            for a in problems:
                lines.append(f"  - {a['aspect']}: {a['negative_pct']:.0f}% negative ({a['total_mentions']} mentions)")

        # Top discussed topics
        if topics:
            top = self._top_topics(topics, limit=3)
            if top:
                lines.append("")
                lines.append("Most discussed topics:")
                for t in top:
                    kw = ", ".join(t.get("keywords", [])[:4])
                    lines.append(f"  - {kw} ({t['count']} reviews)")

        # Recommendation
        if sentiment_summary:
            neg = sentiment_summary.get("negative_percent", 0)
            lines.append("")
            if neg > 40:
                lines.append("Recommendation: critical share of negative feedback - immediate corrective action required.")
            elif neg > 20:
                lines.append("Recommendation: monitor negative trends and prioritise fixes for the highlighted problem aspects.")
            else:
                lines.append("Recommendation: maintain current quality and reinforce strengths in marketing.")

        # Detailed conclusion: per-aspect human sentences + sample quotes.
        conclusion = self._conclusion(
            sentiment_summary=sentiment_summary,
            aspects=aspects,
            total_reviews=total_reviews,
            keywords=keywords,
        )
        if conclusion:
            lines.append("")
            lines.append("=" * 60)
            lines.append("CONCLUSION")
            lines.append("=" * 60)
            for block in conclusion:
                lines.append(block)

        return "\n".join(lines)

    # ----------------------------------------------------------------- #
    # Tiering - turn raw % into a human label so the rest of the
    # template can write natural sentences without re-checking ranges.
    # ----------------------------------------------------------------- #
    @staticmethod
    def _tier(pos_pct: float, neg_pct: float, mentions: int) -> str:
        """Return one of: 'star', 'strength', 'split', 'weakness', 'critical'.

        Bucketing is driven by the polarity score (pos% - neg%) rather than
        absolute thresholds on each percentage in isolation. This way a
        67/33 aspect is recognised as a strength (polarity +34), and a
        50/50 aspect is recognised as a split (polarity 0) instead of being
        accidentally labelled a weakness because the negative share hits 50%
        on the nose.
        """
        if mentions <= 0:
            return "split"
        polarity = pos_pct - neg_pct
        if polarity >= 80:        # 90/10 or better
            return "star"
        if polarity >= 30:        # ~65/35 or better
            return "strength"
        if polarity <= -70:       # 15/85 or worse
            return "critical"
        if polarity <= -30:       # ~35/65 or worse
            return "weakness"
        return "split"            # ±30 points around 50/50

    def _aspect_sentence(self, asp: Dict[str, Any]) -> str:
        """One human-readable sentence describing the aspect verdict."""
        name = asp["aspect"]
        mentions = asp.get("total_mentions", 0)
        pos_pct = asp.get("positive_pct", 0)
        neg_pct = asp.get("negative_pct", 0)
        ops_pos = asp.get("opinions_positive") or asp.get("context_positive") or []
        ops_neg = asp.get("opinions_negative") or asp.get("context_negative") or []
        tier = self._tier(pos_pct, neg_pct, mentions)
        praise = ", ".join(ops_pos[:3]) if ops_pos else ""
        complain = ", ".join(ops_neg[:3]) if ops_neg else ""

        if tier == "star":
            base = (f"{name.capitalize()} is a clear winner: "
                    f"{pos_pct:.0f}% of {mentions} mentions are positive")
            if praise:
                base += f" (customers highlight: {praise})"
            return base + ". Use this in marketing."

        if tier == "strength":
            base = (f"{name.capitalize()} is a strength: "
                    f"{pos_pct:.0f}% of {mentions} mentions are positive")
            if praise:
                base += f" (praised for: {praise})"
            tail = ""
            if complain:
                tail = f" A few customers still complained about: {complain}."
            return base + "." + tail

        if tier == "split":
            base = (f"{name.capitalize()} is divisive: opinions are split "
                    f"{pos_pct:.0f}/{neg_pct:.0f} across {mentions} mentions.")
            mid = ""
            if praise and complain:
                mid = (f" Some praise it for {praise}, others criticise it for "
                       f"{complain}.")
            elif praise:
                mid = f" Some praise it for {praise}."
            elif complain:
                mid = f" Several complain about {complain}."
            tail = (" This is a high-priority improvement area - roughly every "
                    "second customer leaves dissatisfied with it.") if mentions >= 4 else ""
            return base + mid + tail

        if tier == "weakness":
            base = (f"{name.capitalize()} is a weakness: "
                    f"{neg_pct:.0f}% of {mentions} mentions are negative")
            if complain:
                base += f" (complaints centre on: {complain})"
            return base + ". Worth investigating."

        # critical
        base = (f"{name.capitalize()} is a critical problem: "
                f"{neg_pct:.0f}% of {mentions} mentions are negative")
        if complain:
            base += f" (recurring issues: {complain})"
        return base + ". Fix this immediately."

    def _action_plan(
        self,
        *,
        aspects: Dict[str, Any] | None,
        keywords: Dict[str, Any] | None,
        sentiment: Dict[str, Any] | None,
    ) -> List[str]:
        """3-5 prioritised actions a non-technical owner can act on today."""
        items = (aspects or {}).get("aspects", []) if isinstance(aspects, dict) else []
        actions: List[str] = []

        # Rank: critical → split with high mentions → weakness → strength
        criticals = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "critical"]
        splits = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "split"]
        weaknesses = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "weakness"]
        stars = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "star"]
        strengths = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "strength"]

        # Sort splits by mentions (most-discussed first), then by neg pct
        splits.sort(key=lambda a: (a.get("total_mentions", 0),
                                   a.get("negative_pct", 0)), reverse=True)
        criticals.sort(key=lambda a: a.get("negative_pct", 0), reverse=True)
        weaknesses.sort(key=lambda a: a.get("negative_pct", 0), reverse=True)
        stars.sort(key=lambda a: a.get("positive_pct", 0), reverse=True)
        strengths.sort(key=lambda a: a.get("positive_pct", 0), reverse=True)

        n = 1
        for a in criticals[:2]:
            ops = a.get("opinions_negative") or []
            extra = f" (specifically: {', '.join(ops[:3])})" if ops else ""
            actions.append(
                f"  {n}. URGENT: fix {a['aspect']} - {a['negative_pct']:.0f}% "
                f"of customers complain about it{extra}.")
            n += 1
        for a in splits[:2]:
            ops = a.get("opinions_negative") or []
            extra = f" Customers say it's {', '.join(ops[:2])}." if ops else ""
            actions.append(
                f"  {n}. Improve {a['aspect']} - every second customer is "
                f"unhappy with it ({a['negative_pct']:.0f}% negative out of "
                f"{a['total_mentions']} mentions).{extra}")
            n += 1
        for a in weaknesses[:1]:
            ops = a.get("opinions_negative") or []
            extra = f" ({', '.join(ops[:3])})" if ops else ""
            actions.append(
                f"  {n}. Investigate {a['aspect']}{extra} - "
                f"{a['negative_pct']:.0f}% of {a['total_mentions']} mentions "
                f"are negative.")
            n += 1

        # Marketing leverage from stars / strengths
        positive_to_market = stars[:2] or strengths[:2]
        if positive_to_market:
            names = [a["aspect"] for a in positive_to_market]
            joined = " and ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + f", and {names[-1]}"
            actions.append(
                f"  {n}. Lean into {joined} in your marketing - "
                f"customers love it ({positive_to_market[0]['positive_pct']:.0f}% positive).")
            n += 1

        # Keyword-only hints (negative phrases that didn't surface as aspects)
        if keywords and isinstance(keywords, dict):
            neg_kws = keywords.get("negative_keywords") or []
            aspect_set = {a["aspect"].lower() for a in items}
            standalone = [
                kw for kw, _ in neg_kws[:8]
                if not any(tok in aspect_set or tok in {a.split()[0]
                           for a in aspect_set} for tok in kw.lower().split())
            ]
            if standalone and not criticals and not splits and not weaknesses:
                actions.append(
                    f"  {n}. Customers also frequently mention these as "
                    f"problems: {', '.join(standalone[:5])}. Worth a closer look.")
                n += 1

        # Fallback if we have nothing actionable
        if not actions:
            neg_total = (sentiment or {}).get("negative_percent", 0)
            if neg_total < 10:
                actions.append(
                    "  No urgent actions - feedback is overwhelmingly positive. "
                    "Keep doing what you do well.")
            else:
                actions.append(
                    "  Monitor the situation - no single recurring problem stands "
                    "out, but keep an eye on negative reviews as they appear.")

        return actions

    def _conclusion(
        self,
        *,
        sentiment_summary: Dict[str, Any] | None,
        aspects: Dict[str, Any] | None,
        total_reviews: int,
        keywords: Dict[str, Any] | None = None,
    ) -> List[str]:
        """Three-block plain-English summary tailored for a lazy reader.

            QUICK VERDICT     -> one sentence answer
            STRENGTHS         -> what to keep / market
            NEEDS WORK        -> what to fix, sorted by priority
            ACTION PLAN       -> 3-5 prioritised steps
        """
        if not aspects and not sentiment_summary:
            return []

        pos_total = (sentiment_summary or {}).get("positive_percent", 0)
        neg_total = (sentiment_summary or {}).get("negative_percent", 0)
        items = (aspects or {}).get("aspects", []) if isinstance(aspects, dict) else []

        blocks: List[str] = []

        # ---------- QUICK VERDICT (1-2 sentences a CEO can skim) ----------
        if pos_total >= 80:
            verdict = (f"Out of {total_reviews:,} reviews, customers are clearly "
                       f"happy: {pos_total:.0f}% positive vs only {neg_total:.0f}% "
                       f"negative. Keep doing what you do well.")
        elif pos_total >= 60 and neg_total < 25:
            verdict = (f"Out of {total_reviews:,} reviews, the result is positive "
                       f"({pos_total:.0f}% positive, {neg_total:.0f}% negative), "
                       f"but there is room to improve.")
        elif neg_total >= 50:
            verdict = (f"Out of {total_reviews:,} reviews, negative feedback "
                       f"dominates ({neg_total:.0f}% negative vs only "
                       f"{pos_total:.0f}% positive). Immediate action is needed.")
        elif 35 <= neg_total < 50:
            verdict = (f"Out of {total_reviews:,} reviews, opinions are split "
                       f"({pos_total:.0f}% positive vs {neg_total:.0f}% negative). "
                       f"You have real strengths and real problems - both are "
                       f"shown below.")
        else:
            verdict = (f"Out of {total_reviews:,} reviews, the result is mixed "
                       f"({pos_total:.0f}% positive, {neg_total:.0f}% negative). "
                       f"The strengths and weaknesses below explain why.")
        blocks.append(verdict)

        # ---------- STRENGTHS ----------
        stars = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "star"]
        strengths = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "strength"]
        positives = sorted(stars + strengths,
                           key=lambda a: (a.get("positive_pct", 0),
                                          a.get("total_mentions", 0)),
                           reverse=True)[:4]
        if positives:
            blocks.append("")
            blocks.append("STRENGTHS - keep doing these:")
            for a in positives:
                blocks.append("  - " + self._aspect_sentence(a))
                ex = a.get("example_positive")
                if ex:
                    blocks.append(f'      Example review: "{_truncate(ex)}"')

        # ---------- NEEDS WORK (split + weakness + critical, prioritised) ----------
        problems_split = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "split"]
        problems_weak = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "weakness"]
        problems_crit = [a for a in items if self._tier(
            a.get("positive_pct", 0), a.get("negative_pct", 0),
            a.get("total_mentions", 0)) == "critical"]
        # Order: critical -> split (by mentions) -> weakness
        problems_split.sort(key=lambda a: a.get("total_mentions", 0), reverse=True)
        problems_crit.sort(key=lambda a: a.get("negative_pct", 0), reverse=True)
        problems_weak.sort(key=lambda a: a.get("negative_pct", 0), reverse=True)
        problems = (problems_crit + problems_split + problems_weak)[:5]

        if problems:
            blocks.append("")
            blocks.append("NEEDS WORK - opinions are split or negative:")
            for a in problems:
                blocks.append("  - " + self._aspect_sentence(a))
                ex_neg = a.get("example_negative")
                ex_pos = a.get("example_positive")
                tier = self._tier(a.get("positive_pct", 0),
                                  a.get("negative_pct", 0),
                                  a.get("total_mentions", 0))
                if tier == "split" and ex_pos and ex_neg:
                    blocks.append(f'      Praise example:    "{_truncate(ex_pos)}"')
                    blocks.append(f'      Complaint example: "{_truncate(ex_neg)}"')
                elif ex_neg:
                    blocks.append(f'      Example complaint: "{_truncate(ex_neg)}"')
        elif neg_total < 10 and not positives:
            blocks.append("")
            blocks.append("No recurring problems found in the feedback.")

        # ---------- ACTION PLAN ----------
        plan = self._action_plan(
            aspects=aspects, keywords=keywords, sentiment=sentiment_summary,
        )
        blocks.append("")
        blocks.append("WHAT TO DO NEXT:")
        blocks.extend(plan)

        return blocks

    @staticmethod
    def _mood_label(pos: float, neg: float) -> str:
        if pos >= 70:
            return "strongly positive"
        if pos >= 50 and neg < 30:
            return "predominantly positive"
        if neg >= 50:
            return "predominantly negative"
        if neg >= 30:
            return "mixed with significant negativity"
        return "mixed"

    @staticmethod
    def _top_aspects(aspects: Dict[str, Any] | None, polarity: str, limit: int) -> List[Dict[str, Any]]:
        if not aspects:
            return []
        items = aspects.get("aspects", []) if isinstance(aspects, dict) else []
        if polarity == ">":
            filtered = [a for a in items if a.get("polarity", 0) > 20 and a.get("total_mentions", 0) >= 2]
            filtered.sort(key=lambda a: a.get("polarity", 0), reverse=True)
        elif polarity == "~":
            # Mixed: aspect with comparable positive/negative shares.
            filtered = [
                a for a in items
                if -20 <= a.get("polarity", 0) <= 20
                and a.get("total_mentions", 0) >= 5
                and a.get("negative_pct", 0) >= 25
            ]
            filtered.sort(key=lambda a: a.get("total_mentions", 0), reverse=True)
        else:
            filtered = [a for a in items if a.get("polarity", 0) < -10 and a.get("total_mentions", 0) >= 2]
            filtered.sort(key=lambda a: a.get("polarity", 0))
        return filtered[:limit]

    @staticmethod
    def _top_topics(topics: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        if not topics:
            return []
        items = topics.get("topics", []) if isinstance(topics, dict) else []
        items_sorted = sorted(items, key=lambda t: t.get("count", 0), reverse=True)
        return items_sorted[:limit]
