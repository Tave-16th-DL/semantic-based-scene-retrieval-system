from __future__ import annotations
from dataclasses import dataclass
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class E5Embedder:
    model_id: str = "intfloat/multilingual-e5-large"

    def __post_init__(self) -> None:
        self.model = SentenceTransformer(self.model_id)
        self.dim = int(self.model.get_sentence_embedding_dimension())

    def encode_query(self, text: str) -> np.ndarray:
        text = (text or "").strip()
        if not text:
            # avoid empty query crash
            text = "(empty query)"
        v = self.model.encode(
            "query: " + text,
            normalize_embeddings=True,
        )
        return np.asarray(v, dtype=np.float32)

    def encode_passages(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        safe = []
        for t in texts:
            t = (t or "").strip()
            if not t:
                # keep empty as a minimal placeholder; will be handled by caller if needed
                safe.append("")
            else:
                safe.append("passage: " + t)

        embs = self.model.encode(
            safe,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=True,
        )
        return np.asarray(embs, dtype=np.float32)
