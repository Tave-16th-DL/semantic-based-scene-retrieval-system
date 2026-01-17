from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import faiss
import numpy as np
import pandas as pd
from app.embedder import E5Embedder
from app.timeparse import time_to_seconds

# 임계값: 이 점수 미만은 top-5 안에 들어도 결과에서 제외
SCORE_THRESHOLD = 0.842

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

        # 기본 최대 top-5
        top_k = int(max(1, min(top_k, 5)))

        # query embedding
        q_emb = self.embedder.encode_query(q).reshape(1, -1)
        q_emb = np.ascontiguousarray(q_emb, dtype=np.float32)

        scores, indices = self.index.search(q_emb, top_k)

        results: List[Dict] = []
        for _, idx in enumerate(indices[0]):
            if idx < 0:
                continue

            # 임계값 미만이면 결과 제외
            score = float(scores[0][len(results)])  # 안전하게 아래에서 다시 계산할 수도 있음
            # 위 한 줄은 rank-기반이 아니라 results 길이 기반이라 꼬일 수 있어.
            # 따라서 아래처럼 "원래 rank"를 유지해 score를 읽는 방식이 안전함.

        results = []
        for rank, idx in enumerate(indices[0]):
            if idx < 0:
                continue

            score = float(scores[0][rank])
            if score < SCORE_THRESHOLD:
                continue

            row = self.meta.iloc[int(idx)]
            start_time = str(row.get("start_time", "")).strip()

            results.append(
                {
                    # 필터링 후 rank를 1..N으로 재부여
                    "rank": len(results) + 1,
                    "shot_id": str(row.get("shot_id", "")).strip(),
                    "start_time": start_time,
                    "start_sec": float(time_to_seconds(start_time)),
                    "score": score,
                    "title": str(row.get("title", "")).strip(),
                    "characters": str(row.get("characters", "")).strip(),
                }
            )

        return results
