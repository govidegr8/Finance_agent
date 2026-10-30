from datetime import date

import pytest

from finance_agent.agents.research import parse_analysis_response
from finance_agent.agents.research import normalize_findings
from finance_agent.config import get_settings
from finance_agent.models import FinanceEvidence, PriceSnapshot, SourceMetadata
from finance_agent.providers.fundamentals import FMPClient


def test_settings_do_not_require_keys_until_used(monkeypatch):
    monkeypatch.setattr("finance_agent.config.load_dotenv", lambda **kwargs: None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    settings = get_settings()

    assert settings.llm_provider == "groq"
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        settings.require_llm_key()


def test_analysis_response_is_validated_against_evidence():
    evidence = FinanceEvidence(
        ticker="AAPL",
        price=PriceSnapshot(
            ticker="AAPL",
            price=123.45,
            source=SourceMetadata(provider="yahoo_finance", as_of=date(2026, 10, 28)),
        ),
        collected_at=date(2026, 10, 29),
    )

    report = parse_analysis_response(
        '{"summary":"Evidence-backed summary.","positive_signals":[],'
        '"risks":[],"limitations":[],"sources":[{"provider":"fake"}],'
        '"evidence":{"wrong":true}}',
        evidence,
    )

    assert report.ticker == "AAPL"
    assert report.summary == "Evidence-backed summary."
    assert report.evidence["price"]["price"] == 123.45
    assert report.sources[0].provider == "yahoo_finance"


def test_invalid_analysis_json_is_rejected():
    evidence = FinanceEvidence(ticker="AAPL", collected_at=date(2026, 10, 29))

    with pytest.raises(ValueError, match="invalid JSON"):
        parse_analysis_response("not json", evidence)


def test_structured_findings_are_normalized():
    findings = normalize_findings(
        [{"description": "High margin", "evidence": "gross_margin: 0.48"}]
    )

    assert findings == ["High margin (evidence: gross_margin: 0.48)"]


def test_fmp_authentication_error_is_actionable(monkeypatch):
    class Response:
        status_code = 401

        def raise_for_status(self):
            raise AssertionError("401 should be handled before raise_for_status")

    monkeypatch.setattr(
        "finance_agent.providers.fundamentals.httpx.get",
        lambda *args, **kwargs: Response(),
    )

    with pytest.raises(ValueError, match="FMP rejected FMP_API_KEY"):
        FMPClient("invalid-key")._get("profile", "AAPL")


def test_fmp_uses_stable_symbol_query_parameter(monkeypatch):
    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return [{"symbol": "AAPL"}]

    request = {}

    def fake_get(url, params, timeout):
        request.update(url=url, params=params, timeout=timeout)
        return Response()

    monkeypatch.setattr("finance_agent.providers.fundamentals.httpx.get", fake_get)

    result = FMPClient("test-key")._get("profile", "AAPL")

    assert result == [{"symbol": "AAPL"}]
    assert request["url"] == "https://financialmodelingprep.com/stable/profile"
    assert request["params"] == {"symbol": "AAPL", "apikey": "test-key"}
