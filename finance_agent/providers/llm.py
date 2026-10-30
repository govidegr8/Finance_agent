"""LLM provider adapters used by the research workflow."""

from typing import Protocol

import httpx

from ..config import Settings


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate text for a prompt."""


class GroqProvider:
    """Use Groq's OpenAI-compatible chat-completions endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.require_llm_key()
        self.model = settings.groq_model
        self.base_url = "https://api.groq.com/openai/v1"

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            "%s/chat/completions" % self.base_url,
            headers={"Authorization": "Bearer %s" % self.api_key},
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a careful financial research analyst.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            },
            timeout=60.0,
        )
        if response.status_code == 401:
            raise ValueError(
                "Groq rejected GROQ_API_KEY (HTTP 401). Create or copy a valid key "
                "from https://console.groq.com/keys."
            )
        response.raise_for_status()
        payload = response.json()
        return str(payload["choices"][0]["message"]["content"])


class GeminiProvider:
    """Use Google's Gemini SDK without importing it unless selected."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.require_llm_key()
        self.model = settings.gemini_model

    def generate(self, prompt: str) -> str:
        from google import genai

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(model=self.model, contents=prompt)
        if not response.text:
            raise ValueError("Gemini returned an empty response")
        return response.text


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "groq":
        return GroqProvider(settings)
    if settings.llm_provider == "gemini":
        return GeminiProvider(settings)
    raise ValueError("Unsupported LLM provider: %s" % settings.llm_provider)
