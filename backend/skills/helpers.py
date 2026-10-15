from __future__ import annotations

import re


def sentences(text: str, limit: int = 12) -> list[str]:
    values = []
    for line in re.split(r"\n+", text):
        line = re.sub(r"^\s*[-*#>\d.)、]+\s*", "", line).strip()
        if len(line) < 8:
            continue
        values.extend(x.strip() for x in re.split(r"(?<=[。！？!?])", line) if len(x.strip()) >= 8)
    values = list(dict.fromkeys(values))
    return values[:limit]


def keywords(text: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9-]{2,}", text)
    stop = {"一个", "以及", "通过", "进行", "相关", "主要", "内容", "目前", "其中", "可以"}
    counts: dict[str, int] = {}
    for word in words:
        key = word.lower()
        if key not in stop:
            counts[key] = counts.get(key, 0) + 1
    return [x[0] for x in sorted(counts.items(), key=lambda x: -x[1])[:limit]]
