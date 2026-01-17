from __future__ import annotations
import re
from typing import Union


Number = Union[int, float]


def time_to_seconds(t: Union[str, Number, None]) -> float:
    """
    Convert time string to seconds.
    Supports:
      - "0:01:41" (H:MM:SS)
      - "00:01:41.50"
      - "1:41" (MM:SS)
      - "101" (seconds)
      - numeric input already in seconds
    """
    if t is None:
        return 0.0

    if isinstance(t, (int, float)):
        return float(t)

    s = str(t).strip()
    if not s:
        return 0.0

    # If it's plain number (seconds)
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)

    parts = s.split(":")
    parts = [p.strip() for p in parts if p.strip() != ""]
    if len(parts) == 3:
        h, m, sec = parts
        return float(h) * 3600.0 + float(m) * 60.0 + float(sec)
    if len(parts) == 2:
        m, sec = parts
        return float(m) * 60.0 + float(sec)

    # fallback: try to parse any number found
    m = re.search(r"(\d+(\.\d+)?)", s)
    return float(m.group(1)) if m else 0.0