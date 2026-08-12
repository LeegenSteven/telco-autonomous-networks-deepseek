from __future__ import annotations

import math
import re
from collections import Counter


def _tokens(text: str) -> list[str]:
    normalized = text.lower()
    latin_tokens = re.findall(r"[a-z0-9_]+", normalized)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", normalized)
    chinese_bigrams = [
        run[index:index + 2]
        for run in chinese_runs
        for index in range(max(1, len(run) - 1))
    ]
    return latin_tokens + chinese_bigrams


def cosine_similarity(left: str, right: str) -> float:
    """Small dependency-free lexical similarity suitable for incident summaries."""

    left_counts = Counter(_tokens(left))
    right_counts = Counter(_tokens(right))
    if not left_counts or not right_counts:
        return 0.0

    dot = sum(value * right_counts.get(token, 0) for token, value in left_counts.items())
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
