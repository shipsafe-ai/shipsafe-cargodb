"""Gemini via Vertex AI client — all LLM calls route here (rule 1)."""
from __future__ import annotations
import json
import os
from typing import Any

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationResponse

from agent.config import GEMINI_MODEL, GCP_PROJECT, GCP_REGION


def _init() -> None:
    vertexai.init(project=GCP_PROJECT, location=GCP_REGION)


class GeminiClient:
    def __init__(self) -> None:
        _init()
        self._model = GenerativeModel(GEMINI_MODEL)

    async def generate(self, prompt: str) -> GenerationResponse:
        return await self._model.generate_content_async(prompt)
