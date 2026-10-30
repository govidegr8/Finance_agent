"""End-to-end finance research orchestration."""

from datetime import date

from ..agents.research import build_research_prompt, parse_analysis_response
from ..config import Settings, get_settings
from ..models import FinanceEvidence
from ..providers.fundamentals import FMPClient
from ..providers.llm import build_llm_provider
from ..providers.market_data import get_latest_price


def analyze_ticker(
    ticker: str,
    question: str,
    settings: Settings = None,
) -> object:
    """Collect evidence and return a validated LLM research report."""
    active_settings = settings or get_settings()
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("Ticker must not be empty")

    price = get_latest_price(normalized_ticker)
    fundamentals = FMPClient(active_settings.require_fmp_key()).get_fundamentals(
        normalized_ticker
    )
    evidence = FinanceEvidence(
        ticker=normalized_ticker,
        price=price,
        fundamentals=fundamentals,
        collected_at=date.today(),
    )
    provider = build_llm_provider(active_settings)
    raw_response = provider.generate(build_research_prompt(question, evidence))
    return parse_analysis_response(raw_response, evidence)
