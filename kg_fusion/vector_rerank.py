from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.llm_extraction.client import LLMClient


def cosine(left: list[float], right: list[float]) -> float:
    denom = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(y * y for y in right))
    if denom == 0:
        return 0.0
    return sum(x * y for x, y in zip(left, right)) / denom


class EmbeddingReranker:
    def __init__(
        self,
        config_path: str | None = None,
        cache_path: str | Path | None = None,
        enabled: bool = True,
        string_weight: float = 0.4,
        vector_weight: float = 0.6,
    ) -> None:
        self.enabled = enabled
        self.string_weight = string_weight
        self.vector_weight = vector_weight
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache: dict[str, list[float]] = {}
        if self.cache_path and self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.client: LLMClient | None = None
        if enabled:
            try:
                self.client = LLMClient(config_path)
            except Exception:
                self.enabled = False

    def save_cache(self) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    def embed_texts(self, texts: list[str]) -> dict[str, list[float]]:
        missing = [text for text in texts if text and text not in self.cache]
        if self.enabled and self.client and missing:
            embeddings = self.client.embed(missing)
            for text, embedding in zip(missing, embeddings):
                self.cache[text] = embedding
        return {text: self.cache[text] for text in texts if text in self.cache}

    def rerank(self, mention_name: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        if not self.enabled:
            for candidate in candidates:
                candidate["vector_score"] = candidate["string_score"]
                candidate["combined_score"] = candidate["string_score"]
            return sorted(candidates, key=lambda item: item["combined_score"], reverse=True)
        candidate_names = [item["canonical"].get("normalized_name") or item["canonical"].get("name", "") for item in candidates]
        vectors = self.embed_texts([mention_name, *candidate_names])
        mention_vec = vectors.get(mention_name)
        for candidate, candidate_name in zip(candidates, candidate_names):
            candidate_vec = vectors.get(candidate_name)
            vector_score = cosine(mention_vec, candidate_vec) if mention_vec and candidate_vec else candidate["string_score"]
            candidate["vector_score"] = vector_score
            candidate["combined_score"] = self.string_weight * candidate["string_score"] + self.vector_weight * vector_score
        return sorted(candidates, key=lambda item: item["combined_score"], reverse=True)

