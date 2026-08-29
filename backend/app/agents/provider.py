"""LLM provider abstraction for Phase 3B.

Implements:
  - LLMProvider (abstract base)
  - GeminiProvider (primary)
  - OpenAIProvider (secondary, requires openai key)
  - get_provider() — factory function that reads config

Provider selection: LLM_PROVIDER=gemini (default) or LLM_PROVIDER=openai

Each provider implements:
  - complete(system: str, user: str) -> str          — JSON-mode completion
  - complete_structured(system, user, schema) -> dict — validated JSON
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return raw text/JSON string from LLM."""
        ...

    def complete_structured(
        self,
        system: str,
        user: str,
        schema: Optional[Type[BaseModel]] = None,
    ) -> dict[str, Any]:
        """Return parsed, validated JSON dict.

        If schema is provided, validates the LLM output against it.
        On parse failure, raises ValueError.
        """
        raw = self.complete(system, user)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}\nRaw: {raw[:400]}") from exc

        if schema is not None:
            validated = schema.model_validate(data)
            return validated.model_dump()

        return data

    def is_available(self) -> bool:
        """Check if the provider is configured and available."""
        try:
            self.complete("Say 'ok' in JSON: {\"status\": \"ok\"}", "ping")
            return True
        except Exception:
            return False


# ── Gemini Provider ───────────────────────────────────────────────────────────

class GeminiProvider(LLMProvider):
    """Google Gemini provider using google-generativeai SDK."""

    def __init__(self, model: Optional[str] = None) -> None:
        settings = get_settings()
        self._api_key = settings.GEMINI_API_KEY
        self._model_name = model or settings.effective_llm_model
        if not self._api_key:
            logger.warning("GEMINI_API_KEY is not set — LLM calls will fail")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    def complete(self, system: str, user: str) -> str:
        try:
            import google.generativeai as genai
        except ImportError:
            raise RuntimeError("google-generativeai is not installed")

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )
        response = model.generate_content(user)
        return response.text


# ── OpenAI Provider ───────────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """OpenAI provider using openai SDK."""

    def __init__(self, model: Optional[str] = None) -> None:
        settings = get_settings()
        self._api_key = settings.OPENAI_API_KEY
        self._model_name = model or settings.effective_llm_model
        if not self._api_key:
            logger.warning("OPENAI_API_KEY is not set — LLM calls will fail")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider_name(self) -> str:
        return "openai"

    def complete(self, system: str, user: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package is not installed")

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model_name,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or "{}"


# ── Mock Provider (for tests) ─────────────────────────────────────────────────

class MockProvider(LLMProvider):
    """Deterministic mock provider for unit tests — no API calls."""

    def __init__(self, responses: Optional[dict[str, str]] = None) -> None:
        self._responses = responses or {}

    @property
    def model_name(self) -> str:
        return "mock-v1"

    @property
    def provider_name(self) -> str:
        return "mock"

    def complete(self, system: str, user: str) -> str:
        """Return a pre-configured response or a safe default."""
        for key, response in self._responses.items():
            if key in system or key in user:
                return response
        # Safe default
        return json.dumps({
            "evidence_needed": ["TRANSACTION", "SETTLEMENT", "FINANCE_RULE"],
            "reason": "Default mock response",
            "findings": ["Mock finding"],
            "observed_facts": ["Payment recorded"],
            "potential_root_causes": ["FEE_VARIANCE"],
            "contradictions": [],
            "root_cause": "FEE_VARIANCE",
            "confidence": 0.82,
            "evidence_ids": [],
            "reasoning": "Mock reasoning",
            "uncertainties": [],
            "requires_human_review": False,
            "conclusion": "Mock conclusion",
            "recommendation": "Mock recommendation",
            "next_steps": ["Review fee"],
            "inferences": ["Mock inference"],
            "status": "ok",
        })


# ── Factory ───────────────────────────────────────────────────────────────────

def get_provider(provider_override: Optional[str] = None) -> LLMProvider:
    """Return configured LLM provider.

    Order of precedence:
      1. provider_override (for testing)
      2. settings.LLM_PROVIDER
    """
    settings = get_settings()
    name = (provider_override or settings.LLM_PROVIDER).lower()

    if name == "gemini":
        return GeminiProvider()
    if name == "openai":
        return OpenAIProvider()
    if name == "mock":
        return MockProvider()

    logger.warning("Unknown LLM_PROVIDER '%s', falling back to Gemini", name)
    return GeminiProvider()
