"""
CSV and Excel file parser.

Two-stage column detection
==========================
1. **Name-based mapping** via `CSV_FIELD_MAPPING` (config.config). Covers
   the typical TripAdvisor / Booking / Yelp / sample exports plus a few
   Ukrainian/Russian header variants. Substring match, case-insensitive.

2. **Content-based fallback**. If `text` cannot be located by name, the
   parser inspects each remaining column and picks the one with the
   highest *average string length* — that's empirically the review body.
   Numeric columns whose values mostly fall in 1..5 / 0..10 / 0..100 are
   tagged as `rating`; columns parseable as dates → `date`. This makes
   the parser dataset-agnostic: any CSV exported from any review platform
   works without users having to rename columns.

Rating-scale normalisation
==========================
If the rating column lives outside the canonical 1–5 range we rescale:
* 0–10  → round((v / 10) * 5)
* 0–100 → round((v / 100) * 5)
* 1–10  → round((v / 10) * 5)
Anything else is dropped (set to None) so downstream models never see noise.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .base_parser import BaseParser
from config.config import CSV_FIELD_MAPPING

logger = logging.getLogger(__name__)


# Minimum average characters in a cell for a column to be plausibly the
# review text (filters out short codes / IDs / single-word fields).
MIN_AVG_TEXT_LEN = 25

# How many rows we sample for content-based heuristics. We don't need to
# scan the whole 20k-row dataset to pick column roles.
HEURISTIC_SAMPLE_SIZE = 200


def _norm_rating(value: Any, scale_max: float) -> Optional[int]:
    """Rescale a rating value to the canonical 1..5 integer scale."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if scale_max == 5:
        return int(round(v)) if 1 <= v <= 5 else None
    if scale_max == 10:
        return int(round((v / 10) * 5)) if 0 <= v <= 10 else None
    if scale_max == 100:
        return int(round((v / 100) * 5)) if 0 <= v <= 100 else None
    # Unknown scale - reject defensively.
    return None


class CSVParser(BaseParser):
    """Parser for CSV and Excel files."""

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path)

        df = self._read_dataframe(path)
        logger.info("Loaded %d rows from %s", len(df), path.name)
        logger.info("Columns found: %s", df.columns.tolist())

        column_mapping = self._detect_columns(df)
        logger.info("Detected column mapping: %s", column_mapping)

        if not column_mapping.get('text'):
            raise ValueError(
                "Could not locate a review-text column. Expected one of: "
                "'review', 'text', 'comment', 'feedback', 'opinion', "
                "'description' (any language). Got: "
                f"{df.columns.tolist()}"
            )

        rating_scale = self._guess_rating_scale(df, column_mapping.get('rating'))
        if column_mapping.get('rating') and rating_scale != 5:
            logger.info(
                "Rating column '%s' uses 0..%s scale - rescaling to 1..5",
                column_mapping['rating'], int(rating_scale),
            )

        reviews: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            review: Dict[str, Any] = {'text': row[column_mapping['text']]}
            if column_mapping.get('date'):
                review['date'] = row[column_mapping['date']]
            if column_mapping.get('rating'):
                normalised = _norm_rating(row[column_mapping['rating']], rating_scale)
                if normalised is not None:
                    review['rating'] = normalised
            if column_mapping.get('author'):
                review['author'] = row[column_mapping['author']]
            reviews.append(review)

        self.parsed_reviews = self.validate_reviews(reviews)
        logger.info("Successfully parsed %d valid reviews", len(self.parsed_reviews))
        return self.parsed_reviews

    # ------------------------------------------------------------------
    # IO helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _read_dataframe(path: Path) -> pd.DataFrame:
        if path.suffix.lower() in ('.xlsx', '.xls'):
            return pd.read_excel(path)
        for enc in ('utf-8', 'utf-8-sig', 'latin-1', 'cp1252'):
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode {path.name} with common encodings.")

    # ------------------------------------------------------------------
    # Column detection
    # ------------------------------------------------------------------
    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Detect text/rating/date/author columns.

        Step 1: try `CSV_FIELD_MAPPING` (name-based).
        Step 2: for any field still missing, fall back to content-based
        heuristics on a small sample of rows.
        """
        columns = list(df.columns)
        mapping = self._detect_columns_by_name(columns)

        missing = [k for k in ('text', 'rating', 'date') if k not in mapping]
        if missing:
            content_mapping = self._detect_columns_by_content(df, exclude=set(mapping.values()))
            for k in missing:
                if content_mapping.get(k):
                    mapping[k] = content_mapping[k]
                    logger.info(
                        "Column '%s' inferred from CONTENT for field '%s'",
                        content_mapping[k], k,
                    )

        return mapping

    @staticmethod
    def _detect_columns_by_name(columns: List[str]) -> Dict[str, str]:
        """First pass: substring match against CSV_FIELD_MAPPING."""
        mapping: Dict[str, str] = {}
        lowered = [str(c).lower().strip() for c in columns]
        for field, patterns in CSV_FIELD_MAPPING.items():
            for pat in patterns:
                pat_l = pat.lower()
                for i, col in enumerate(lowered):
                    if pat_l in col:
                        mapping[field] = columns[i]
                        break
                if field in mapping:
                    break
        return mapping

    @staticmethod
    def _detect_columns_by_content(
        df: pd.DataFrame,
        exclude: set,
    ) -> Dict[str, str]:
        """Second pass: pick columns by what's *inside* them.

        - `text`   = unmapped column with the largest average string length
                     (must clear MIN_AVG_TEXT_LEN to qualify).
        - `rating` = unmapped numeric column whose values mostly fit 1..5,
                     0..10 or 0..100.
        - `date`   = unmapped column whose values mostly parse as dates.
        """
        mapping: Dict[str, str] = {}
        sample = df.head(HEURISTIC_SAMPLE_SIZE)

        candidates = [c for c in df.columns if c not in exclude]
        if not candidates:
            return mapping

        # ---- text: longest average string length
        avg_lens = {}
        for c in candidates:
            try:
                series = sample[c].dropna().astype(str)
            except Exception:  # noqa: BLE001
                continue
            if len(series) == 0:
                continue
            avg_lens[c] = series.str.len().mean()
        if avg_lens:
            best_text, best_len = max(avg_lens.items(), key=lambda kv: kv[1])
            if best_len >= MIN_AVG_TEXT_LEN:
                mapping['text'] = best_text

        # Min number of rows we need to declare a column numeric/date.
        # Scales with the sample so it works on tiny test files too.
        min_rows = max(2, min(5, int(len(sample) * 0.3)))

        # ---- rating: numeric column with values in 1..5 / 0..10 / 0..100
        for c in candidates:
            if c in mapping.values():
                continue
            series = pd.to_numeric(sample[c], errors='coerce').dropna()
            if len(series) < min_rows:
                continue
            mn, mx = series.min(), series.max()
            if mn >= 1 and mx <= 5:
                mapping['rating'] = c
                break
            if mn >= 0 and mx <= 10 and mx > 5:
                mapping['rating'] = c
                break
            if mn >= 0 and mx <= 100 and mx > 10:
                mapping['rating'] = c
                break

        # ---- date: column whose values mostly parse as dates.
        # Skip purely-numeric columns first - pandas would otherwise interpret
        # plain integers like 85 as nanosecond timestamps from 1970-01-01.
        for c in candidates:
            if c in mapping.values():
                continue
            raw = sample[c].dropna()
            if len(raw) < min_rows:
                continue
            numeric_ratio = pd.to_numeric(raw, errors='coerce').notna().mean()
            if numeric_ratio >= 0.8:
                continue
            try:
                parsed = pd.to_datetime(raw, errors='coerce', utc=False)
            except Exception:  # noqa: BLE001
                continue
            ratio = parsed.notna().mean() if len(parsed) else 0
            if ratio >= 0.7:
                mapping['date'] = c
                break

        return mapping

    @staticmethod
    def _guess_rating_scale(df: pd.DataFrame, rating_col: Optional[str]) -> float:
        """Return 5 / 10 / 100 depending on the observed rating range."""
        if not rating_col:
            return 5
        try:
            series = pd.to_numeric(df[rating_col], errors='coerce').dropna()
        except Exception:  # noqa: BLE001
            return 5
        if len(series) == 0:
            return 5
        mx = series.max()
        if mx > 10:
            return 100
        if mx > 5:
            return 10
        return 5
