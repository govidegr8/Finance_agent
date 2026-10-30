"""Financial Modeling Prep fundamentals adapter."""

from datetime import date
from typing import Any, Dict, List, Optional

import httpx

from ..models import FundamentalSnapshot, SourceMetadata


class FMPClient:
    """Small client for the FMP stable profile and ratios endpoints."""

    def __init__(self, api_key: str, timeout: float = 15.0) -> None:
        if not api_key:
            raise ValueError("FMP API key must not be empty")
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://financialmodelingprep.com/stable"

    def _get(self, path: str, ticker: str) -> List[Dict[str, Any]]:
        response = httpx.get(
            "%s/%s" % (self.base_url, path),
            params={"symbol": ticker, "apikey": self.api_key},
            timeout=self.timeout,
        )
        if response.status_code == 401:
            raise ValueError(
                "FMP rejected FMP_API_KEY (HTTP 401). Copy or regenerate the key "
                "from https://site.financialmodelingprep.com/developer/docs/dashboard."
            )
        if response.status_code == 403:
            raise ValueError(
                "FMP denied the request (HTTP 403). This account may not support "
                "the requested stable endpoint. Check the FMP plan and API docs."
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Unexpected FMP response for %s" % ticker)
        return payload

    def get_fundamentals(self, ticker: str) -> FundamentalSnapshot:
        """Return normalized profile and latest available ratio values."""
        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            raise ValueError("Ticker must not be empty")

        profile = self._get("profile", normalized_ticker)
        ratios = self._get("ratios-ttm", normalized_ticker)
        profile_row: Dict[str, Any] = profile[0] if profile else {}
        ratio_row: Dict[str, Any] = ratios[0] if ratios else {}
        selected_ratios: Dict[str, float] = {}
        ratio_keys = {
            "gross_margin": "grossProfitMarginTTM",
            "operating_margin": "operatingProfitMarginTTM",
            "net_profit_margin": "netProfitMarginTTM",
            "return_on_assets": "returnOnAssetsTTM",
            "return_on_equity": "returnOnEquityTTM",
            "price_to_earnings": "priceToEarningsRatioTTM",
            "price_to_book": "priceToBookRatioTTM",
            "current_ratio": "currentRatioTTM",
        }
        for output_name, response_key in ratio_keys.items():
            value = ratio_row.get(response_key)
            if isinstance(value, (int, float)):
                selected_ratios[output_name] = float(value)

        return FundamentalSnapshot(
            ticker=normalized_ticker,
            company_name=_optional_string(profile_row.get("companyName")),
            ratios=selected_ratios,
            source=SourceMetadata(
                provider="financial_modeling_prep", as_of=date.today()
            ),
        )


def _optional_string(value: Optional[Any]) -> Optional[str]:
    return str(value) if value is not None else None
