# -*- coding: utf-8 -*-
"""
Pre-download all NLP models used by the platform.

Run ONCE before starting the backend:
    .venv\\Scripts\\python.exe scripts\\download_models.py

Models will be cached in the standard Hugging Face cache (~/.cache/huggingface/
on Linux/macOS, C:/Users/<USER>/.cache/huggingface on Windows). Subsequent
runs of the backend will load them from disk without network access.

Total download size: ~1.2 GB.
"""
import sys
import time
from pathlib import Path

# allow imports from project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def banner(text: str) -> None:
    print()
    print("=" * 70)
    print(f"  {text}")
    print("=" * 70)


def download_sentiment() -> None:
    banner("1/3  Sentiment model — nlptown/bert-base-multilingual-uncased-sentiment (~672 MB)")
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    name = "nlptown/bert-base-multilingual-uncased-sentiment"
    AutoTokenizer.from_pretrained(name)
    AutoModelForSequenceClassification.from_pretrained(name)
    print(f"  OK: {name}")


def download_embeddings() -> None:
    banner("2/3  Sentence embeddings — paraphrase-multilingual-MiniLM-L12-v2 (~471 MB)")
    from sentence_transformers import SentenceTransformer

    name = "paraphrase-multilingual-MiniLM-L12-v2"
    SentenceTransformer(name)
    print(f"  OK: {name}")


def warmup_pipelines() -> None:
    banner("3/3  Warmup — loading wrappers and running tiny inference")
    from src.models.sentiment_analyzer import SentimentAnalyzer
    from src.models.topic_extractor import TopicExtractor
    from src.models.keyword_extractor import KeywordExtractor

    sa = SentimentAnalyzer()
    out = sa.analyze(["Чудовий сервіс, дуже сподобалось!", "Жахливо, більше ніколи."])
    print(f"  Sentiment sample: {[o['label'] for o in out]}")

    te = TopicExtractor()
    print(f"  TopicExtractor ready: {type(te.embedding_model).__name__}")

    ke = KeywordExtractor()
    print(f"  KeywordExtractor ready: {type(ke.model).__name__}")


def main() -> int:
    t0 = time.perf_counter()
    try:
        download_sentiment()
        download_embeddings()
        warmup_pipelines()
    except Exception as exc:  # noqa: BLE001
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1
    dt = time.perf_counter() - t0
    banner(f"All models downloaded and verified in {dt:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
