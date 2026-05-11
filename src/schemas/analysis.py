"""Analysis & results schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Settings for the analysis pipeline."""

    analyze_sentiment: bool = True
    analyze_aspects: bool = True
    analyze_topics: bool = True
    extract_keywords: bool = True
    generate_summary: bool = True


class AnalysisOut(BaseModel):
    id: str
    project_id: str
    user_id: str
    file_name: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    total_reviews: int = 0
    status: str
    error_message: Optional[str] = None
    progress_stage: Optional[str] = None
    progress_pct: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


class ResultOut(BaseModel):
    id: str
    analysis_id: str
    sentiment_summary: Optional[Dict[str, Any]] = None
    aspects: Optional[Dict[str, Any]] = None
    topics: Optional[Dict[str, Any]] = None
    keywords: Optional[Dict[str, Any]] = None
    summary_text: Optional[str] = None
    insights: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    metrics: Optional[Dict[str, Any]] = None
    sample_reviews: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class AnalysisResponse(BaseModel):
    analysis: AnalysisOut
    result: Optional[ResultOut] = None
