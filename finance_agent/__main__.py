"""Command-line entry point for the finance agent."""

import argparse
import json
import os
import sys
from typing import Optional, Sequence

from .config import get_settings
from .providers.fundamentals import FMPClient
from .providers.market_data import get_latest_price
from .services.orchestrator import analyze_ticker


class ConsoleStyle:
    """ANSI colors for terminal output with a plain-text fallback."""

    def __init__(self, enabled: bool) -> None:
        prefix = "\033["
        self.title = prefix + "1;36m" if enabled else ""
        self.heading = prefix + "1;34m" if enabled else ""
        self.positive = prefix + "32m" if enabled else ""
        self.risk = prefix + "33m" if enabled else ""
        self.muted = prefix + "2;37m" if enabled else ""
        self.reset = prefix + "0m" if enabled else ""

    def paint(self, text: str, color: str) -> str:
        return "%s%s%s" % (color, text, self.reset)


def get_console_style(no_color: bool = False) -> ConsoleStyle:
    enabled = sys.stdout.isatty() and not no_color and not os.getenv("NO_COLOR")
    return ConsoleStyle(enabled)


def print_section(style: ConsoleStyle, title: str, items: Sequence[str], color: str) -> None:
    if not items:
        return
    print("\n" + style.paint(title, color))
    print("-" * len(title))
    print("\n".join("  * %s" % item for item in items))


def print_report(report, style: ConsoleStyle) -> None:
    print(style.paint("FINANCE RESEARCH REPORT", style.title))
    print(style.paint("Ticker: %s" % report.ticker, style.muted))
    print()
    print(style.paint("SUMMARY", style.heading))
    print(report.summary)
    print_section(style, "POSITIVE SIGNALS", report.positive_signals, style.positive)
    print_section(style, "RISKS", report.risks, style.risk)
    print_section(style, "LIMITATIONS", report.limitations, style.muted)
    print_section(
        style,
        "SOURCES",
        ["%s (as of %s)" % (source.provider, source.as_of) for source in report.sources],
        style.muted,
    )
    disclaimer = "Educational research only; this is not investment advice."
    print("\n" + style.paint(disclaimer, style.muted))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="finance-agent",
        description="Research public companies using live financial data.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze a ticker using market and fundamental data"
    )
    analyze_parser.add_argument("ticker", help="Stock ticker, for example AAPL")
    analyze_parser.add_argument(
        "--question",
        default="Provide a concise fundamental analysis and identify key risks.",
        help="Question for the research agent",
    )
    analyze_parser.add_argument(
        "--provider",
        choices=("groq", "gemini"),
        help="LLM provider; defaults to LLM_PROVIDER",
    )
    analyze_parser.add_argument(
        "--json", action="store_true", help="Print the validated report as JSON"
    )
    analyze_parser.add_argument(
        "--no-color", action="store_true", help="Disable colored human-readable output"
    )

    price_parser = subparsers.add_parser(
        "price", help="Fetch the latest available close"
    )
    price_parser.add_argument("ticker", help="Stock ticker, for example AAPL")

    fundamentals_parser = subparsers.add_parser(
        "fundamentals", help="Fetch the latest available FMP fundamentals"
    )
    fundamentals_parser.add_argument("ticker", help="Stock ticker, for example AAPL")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "price":
            print(
                json.dumps(
                    get_latest_price(args.ticker).model_dump(), default=str, indent=2
                )
            )
        elif args.command == "fundamentals":
            settings = get_settings()
            result = FMPClient(settings.require_fmp_key()).get_fundamentals(args.ticker)
            print(json.dumps(result.model_dump(), default=str, indent=2))
        elif args.command == "analyze":
            settings = get_settings(args.provider)
            report = analyze_ticker(args.ticker, args.question, settings)
            if args.json:
                print(json.dumps(report.model_dump(), default=str, indent=2))
            else:
                print_report(report, get_console_style(args.no_color))
    except (ValueError, KeyError) as exc:
        parser.exit(2, "Error: %s\n" % exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
