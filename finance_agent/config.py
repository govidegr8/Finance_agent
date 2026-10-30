"""Environment-backed configuration for the finance agent."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Application settings loaded without exposing secret values."""

    llm_provider: str = "groq"
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    fmp_api_key: Optional[str] = None
    groq_model: str = "openai/gpt-oss-120b"
    gemini_model: str = "gemini-2.5-flash"

    def require_llm_key(self) -> str:
        key = self.groq_api_key if self.llm_provider == "groq" else self.gemini_api_key
        variable = "GROQ_API_KEY" if self.llm_provider == "groq" else "GEMINI_API_KEY"
        if not key:
            raise ValueError("Missing required environment variable: %s" % variable)
        return key

    def require_fmp_key(self) -> str:
        if not self.fmp_api_key:
            raise ValueError("Missing required environment variable: FMP_API_KEY")
        return self.fmp_api_key


def get_settings(provider: Optional[str] = None) -> Settings:
    """Load settings from the environment, optionally overriding the LLM provider."""
    dotenv_candidates = (
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    )
    for dotenv_path in dotenv_candidates:
        if dotenv_path.is_file():
            load_dotenv(dotenv_path=dotenv_path)
            break
    selected_provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
    if selected_provider not in {"groq", "gemini"}:
        raise ValueError("LLM_PROVIDER must be either 'groq' or 'gemini'")

    return Settings(
        llm_provider=selected_provider,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        fmp_api_key=os.getenv("FMP_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
