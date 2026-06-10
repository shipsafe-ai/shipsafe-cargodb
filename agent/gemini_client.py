"""Gemini via Vertex AI client — all LLM calls route here (rule 1)."""
from __future__ import annotations
import json
import os
from typing import Any

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, GenerationResponse

from agent.config import GEMINI_MODEL, GCP_PROJECT, GCP_REGION

_SUPPORTS_THINKING = "2.5" in GEMINI_MODEL


def _init() -> None:
    vertexai.init(project=GCP_PROJECT, location=GCP_REGION)


def _extract_thinking(response: GenerationResponse) -> str:
    """Extract thought parts from Gemini 2.5 response (include_thoughts=True)."""
    thoughts = []
    for candidate in getattr(response, "candidates", []):
        for part in getattr(candidate.content, "parts", []):
            if getattr(part, "thought", False) and getattr(part, "text", ""):
                thoughts.append(part.text)
    return "\n\n".join(thoughts)


class GeminiClient:
    def __init__(self) -> None:
        _init()
        config_kwargs: dict[str, Any] = {}
        if _SUPPORTS_THINKING:
            try:
                from vertexai.generative_models import ThinkingConfig
                config_kwargs["thinking_config"] = ThinkingConfig(include_thoughts=True)
            except ImportError:
                pass
        gen_config = GenerationConfig(**config_kwargs) if config_kwargs else None
        self._model = GenerativeModel(GEMINI_MODEL, generation_config=gen_config)
        self._gen_config = gen_config

    async def generate(self, prompt: str) -> GenerationResponse:
        return await self._model.generate_content_async(prompt)

    async def generate_with_thinking(self, prompt: str) -> tuple[GenerationResponse, str]:
        """Returns (response, thinking_text). thinking_text empty if model doesn't support it."""
        response = await self._model.generate_content_async(prompt)
        thinking = _extract_thinking(response) if _SUPPORTS_THINKING else ""
        return response, thinking
