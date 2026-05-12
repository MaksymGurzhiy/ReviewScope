"""
NLP package - high-level entry points for review analysis.

The legacy `src.models` package wraps the underlying ML models
(SentimentAnalyzer, TopicExtractor, KeywordExtractor) so the existing
ReviewAnalyzer code keeps working. This package adds:

    - LanguageDetector   - per-text language detection (langdetect)
    - AspectAnalyzer     - aspect-based sentiment (ABSA)
    - SummaryGenerator   - "top problems / top strengths" report
    - NLPPipeline        - orchestrator used by analysis_service

The previous version eagerly imported NLPPipeline here, which caused
circular-import problems once KeywordExtractor started reusing constants
from AspectAnalyzer. Importers should pull NLPPipeline directly:

    from src.nlp.pipeline import NLPPipeline
"""

__all__: list[str] = []
