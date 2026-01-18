from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Tuple, List
import faiss
import numpy as np
import pandas as pd
from app.embedder import E5Embedder


COLUMN_WEIGHTS = {"video": 0.6, "dialogue": 0.4}

VIDEO_FIELDS = [
    "detailed_caption",
    "visual_details",
    "location",
    "actions",
    "mood",
    "characters",
]

DIALOGUE_FIELDS = [
    "stt_text",
    "narrative",
]


def join_fields(row: pd.Series, fields: List[str]) -> str:
    vals = []
    for f in fields:
        v = row.get(f, "")
        if pd.isna(v):
            v = ""
        v = str(v).strip()
        if v:
            vals.append(v)
    return " ".join(vals).strip()


def build_semantic_texts(row: pd.Series) -> Tuple[str, str]:
    video_text = join_fields(row, VIDEO_FIELDS)
    dialogue_text = join_fields(row, DIALOGUE_FIELDS)
    return video_text, dialogue_text


def build_embeddings(df: pd.DataFrame, embedder: E5Embedder, batch_size: int = 32) -> np.ndarray:
    """
    Build (N, dim) embeddings:
      emb = normalize( w_v * enc(video) + w_d * enc(dialogue) )
    """
    n = len(df)
    dim = embedder.dim

    video_texts = []
    dialogue_texts = []

    for _, row in df.iterrows():
        v, d = build_semantic_texts(row)
        video_texts.append(v)
        dialogue_texts.append(d)

    # Encode in batches (normalized vectors)
    video_embs = embedder.encode_passages(video_texts, batch_size=batch_size)
    dialogue_embs = embedder.encode_passages(dialogue_texts, batch_size=batch_size)

    # If a row text is empty, encode_passages produced embedding for "" which can be poor.
    # We'll detect empty texts and set that component to 0 vector.
    video_mask = np.array([1.0 if t.strip() else 0.0 for t in video_texts], dtype=np.float32).reshape(-1, 1)
    dialogue_mask = np.array([1.0 if t.strip() else 0.0 for t in dialogue_texts], dtype=np.float32).reshape(-1, 1)

    video_embs = video_embs * video_mask
    dialogue_embs = dialogue_embs * dialogue_mask

    # Weighted sum
    out = (
        COLUMN_WEIGHTS["video"] * video_embs
        + COLUMN_WEIGHTS["dialogue"] * dialogue_embs
    ).astype(np.float32)

    # Handle rows where both parts are empty -> fallback to shot_id embedding (or placeholder)
    zero_rows = np.where(np.linalg.norm(out, axis=1) == 0)[0]
    if len(zero_rows) > 0:
        fallback_texts = []
        for i in zero_rows:
            sid = str(df.iloc[i].get("shot_id", "")).strip()
            fallback_texts.append(sid if sid else "(empty scene)")
        fallback_embs = embedder.encode_passages(fallback_texts, batch_size=batch_size)
        out[zero_rows] = fallback_embs

    # Final L2 normalize
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms).astype(np.float32)
    out = out / norms

    out = np.ascontiguousarray(out, dtype=np.float32)
    assert out.shape == (n, dim)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default="data/exp3_input.csv")
    parser.add_argument("--artifacts", type=str, default="data/artifacts")
    parser.add_argument("--model", type=str, default="intfloat/multilingual-e5-large")
    parser.add_argument("--batch_size", type=int, default=32)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parents[1]  # project root
    csv_path = (base_dir / args.csv).resolve()
    artifacts_dir = (base_dir / args.artifacts).resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path).fillna("")
    print(f"[INFO] Loaded CSV: {csv_path}")
    print(f"[INFO] Rows: {len(df)}")
    print(f"[INFO] Columns: {list(df.columns)}")

    # 최소 필요 컬럼 체크
    required = ["shot_id", "start_time"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    embedder = E5Embedder(model_id=args.model)
    print(f"[INFO] Embedder: {args.model}")
    print(f"[INFO] Embedding dim: {embedder.dim}")

    print("[INFO] Building embeddings...")
    embs = build_embeddings(df, embedder, batch_size=args.batch_size)
    print(f"[INFO] Embeddings shape: {embs.shape}")

    # Build FAISS index (cosine via IP because vectors are normalized)
    index = faiss.IndexFlatIP(embedder.dim)
    index.add(embs)
    print(f"[INFO] FAISS index size: {index.ntotal}")

    # Save index
    index_path = artifacts_dir / "faiss.index"
    faiss.write_index(index, str(index_path))
    print(f"[OK] Saved index: {index_path}")

    # Save meta.csv
    meta_cols = []
    for c in ["shot_id", "start_time", "end_time", "characters"]:
        if c in df.columns:
            meta_cols.append(c)

    # UI에 보여줄 title(detailed_caption 사용)
    title = None
    if "detailed_caption" in df.columns:
        title = df["detailed_caption"].astype(str)
    elif "narrative" in df.columns:
        title = df["narrative"].astype(str)
    else:
        title = df["shot_id"].astype(str)

    meta = df[meta_cols].copy()
    meta["title"] = title.astype(str)

    meta_path = artifacts_dir / "meta.csv"
    meta.to_csv(meta_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Saved meta: {meta_path}")

    build_info = {
        "model_id": args.model,
        "embedding_dim": embedder.dim,
        "weights": COLUMN_WEIGHTS,
        "video_fields": VIDEO_FIELDS,
        "dialogue_fields": DIALOGUE_FIELDS,
        "csv_path": str(csv_path),
        "rows": int(len(df)),
    }
    info_path = artifacts_dir / "build_info.json"
    info_path.write_text(json.dumps(build_info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Saved build_info: {info_path}")


if __name__ == "__main__":
    main()
