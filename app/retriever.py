from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import faiss
import numpy as np
import pandas as pd
from app.embedder import E5Embedder
from app.timeparse import time_to_seconds


@dataclass
class RetrieverConfig:
    artifacts_dir: Path
    index_file: str = "faiss.index"
    meta_file: str = "meta.csv"


class SceneRetriever:
    def __init__(self, embedder: E5Embedder, cfg: RetrieverConfig) -> None:
        self.embedder = embedder
        self.cfg = cfg

        index_path = cfg.artifacts_dir / cfg.index_file
        meta_path = cfg.artifacts_dir / cfg.meta_file

        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not meta_path.exists():
            raise FileNotFoundError(f"Meta CSV not found: {meta_path}")

        self.index = faiss.read_index(str(index_path))
        self.meta = pd.read_csv(meta_path).fillna("")

        # sanity check
        if self.index.ntotal != len(self.meta):
            raise ValueError(
                f"Index size ({self.index.ntotal}) != meta rows ({len(self.meta)}). "
                "Rebuild artifacts."
            )

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        q = (query or "").strip()
        if not q:
            return []

        top_k = int(max(1, min(top_k, 50)))

        q_emb = self.embedder.encode_query(q).reshape(1, -1)
        q_emb = np.ascontiguousarray(q_emb, dtype=np.float32)

        scores, indices = self.index.search(q_emb, top_k)

        results: List[Dict] = []
        for rank, idx in enumerate(indices[0]):
            if idx < 0:
                continue
            row = self.meta.iloc[int(idx)]

            start_time = str(row.get("start_time", "")).strip()
            results.append(
                {
                    "rank": rank + 1,
                    "shot_id": str(row.get("shot_id", "")).strip(),
                    "start_time": start_time,
                    "start_sec": float(time_to_seconds(start_time)),
                    "score": float(scores[0][rank]),
                    # 아래는 UI에서 쓰고 싶으면 쓰는 용도(없으면 빈 문자열)
                    "title": str(row.get("title", "")).strip(),
                    "characters": str(row.get("characters", "")).strip(),
                }
            )
        return results
