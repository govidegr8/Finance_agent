"""Typed contracts shared by finance data providers and agents."""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    provider: str
    as_of: date
    currency: Optional[str] = None


class PriceSnapshot(BaseModel):
    ticker: str
    price: float = Field(ge=0)
    source: SourceMetadata


class FundamentalSnapshot(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    ratios: Dict[str, float] = Field(default_factory=dict)
    source: SourceMetadata


class FinanceEvidence(BaseModel):
    ticker: str
    price: Optional[PriceSnapshot] = None
    fundamentals: Optional[FundamentalSnapshot] = None
    collected_at: date


class AnalysisReport(BaseModel):
    ticker: str
    summary: str
    positive_signals: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    sources: List[SourceMetadata] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
