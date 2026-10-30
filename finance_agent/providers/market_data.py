"""Yahoo Finance market-data adapter."""

from datetime import date

import yfinance as yf

from ..models import PriceSnapshot, SourceMetadata


def get_latest_price(ticker: str) -> PriceSnapshot:
    """Return the latest available daily close for a ticker."""
    normalized_ticker = ticker.strip().upper()
    if not normalized_ticker:
        raise ValueError("Ticker must not be empty")

    history = yf.Ticker(normalized_ticker).history(period="5d", auto_adjust=False)
    if history.empty or "Close" not in history:
        raise ValueError("No market data found for ticker: %s" % normalized_ticker)

    close_series = history["Close"].dropna()
    if close_series.empty:
        raise ValueError("No closing price found for ticker: %s" % normalized_ticker)

    latest_date = close_series.index[-1]
    return PriceSnapshot(
        ticker=normalized_ticker,
        price=float(close_series.iloc[-1]),
        source=SourceMetadata(
            provider="yahoo_finance",
            as_of=latest_date.date() if hasattr(latest_date, "date") else date.today(),
        ),
    )
