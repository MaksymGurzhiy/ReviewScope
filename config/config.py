"""
Configuration file for the Review Analysis System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/reviews.db")

# ML Model Settings
MAX_REVIEWS_PER_ANALYSIS = int(os.getenv("MAX_REVIEWS_PER_ANALYSIS", 1000))
MIN_REVIEWS_FOR_TOPICS = int(os.getenv("MIN_REVIEWS_FOR_TOPICS", 10))

# Supported file formats
SUPPORTED_FORMATS = ['.csv', '.xlsx', '.xls', '.json']

# Review field mappings.
# Substrings searched (case-insensitively) inside CSV column names. Covers
# the most common English/Ukrainian/Russian header variants. If none of
# these patterns matches, the parser falls back to content-based detection
# (CSVParser._detect_columns_by_content).
CSV_FIELD_MAPPING = {
    'date': [
        'date', 'created_at', 'created', 'timestamp', 'review_date',
        'posted', 'time', 'when',
        'дата', 'час', 'опубл',
    ],
    'rating': [
        'rating', 'score', 'stars', 'star_rating', 'mark', 'grade',
        'rate', 'overall', 'satisfaction',
        'оценка', 'оцінка', 'рейтинг', 'бал',
    ],
    'text': [
        'review_text', 'text', 'comment', 'review', 'content', 'feedback',
        'opinion', 'body', 'description', 'message', 'headline', 'verdict',
        'отзыв', 'комментарий', 'текст', 'відгук', 'коментар',
    ],
    'author': [
        'author', 'reviewer', 'customer', 'user_name', 'username', 'user',
        'name', 'nickname', 'full_name',
        'автор', 'имя', 'ім\'я',
    ],
}

# Google Takeout JSON structure
GOOGLE_TAKEOUT_STRUCTURE = {
    'reviews_key': 'reviews',
    'text_key': 'comment',
    'rating_key': 'starRating',
    'date_key': 'createTime',
    'rating_mapping': {
        'ONE': 1,
        'TWO': 2,
        'THREE': 3,
        'FOUR': 4,
        'FIVE': 5
    }
}

# Report settings
REPORT_LANGUAGE = os.getenv("REPORT_LANGUAGE", "en")
PDF_FONT = os.getenv("PDF_FONT", "Helvetica")

# Sentiment thresholds
SENTIMENT_THRESHOLDS = {
    'positive': 0.6,
    'negative': 0.4
}

# Topic modeling settings
BERTOPIC_MIN_TOPIC_SIZE = 5
BERTOPIC_NR_TOPICS = 10

# KeyBERT settings
KEYBERT_TOP_N = 10
KEYBERT_KEYPHRASE_NGRAM_RANGE = (1, 2)
