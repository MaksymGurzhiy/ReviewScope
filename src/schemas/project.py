"""Project-related schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    language: Optional[str] = Field(default="auto", description="ISO code or 'auto'")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=1000)
    language: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    language: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    analyses_count: int = 0
