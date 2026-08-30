from __future__ import annotations

import json
import time
from typing import Any

from src.common.config import load_settings


class LLMClient:
    def __init__(self, config_path: str | None = None):
        settings = load_settings(config_path)
        llm = settings["llm"]
        if not llm.get("api_key"):
            raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and fill it before running extraction.")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("openai package is required for LLM extraction.") from exc
        self.client = OpenAI(api_key=llm["api_key"], base_url=llm["base_url"])
        self.model = llm["model"]
        self.embedding_model = llm["embedding_model"]
        self.temperature = float(llm.get("temperature", 0))
        self.max_retries = int(llm.get("max_retries", 3))

    def json_chat(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or "{}"
                return json.loads(content)
            except Exception as exc:
                last_error = exc
                time.sleep(2**attempt)
        raise RuntimeError(f"LLM request failed after {self.max_retries} attempts") from last_error

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]
