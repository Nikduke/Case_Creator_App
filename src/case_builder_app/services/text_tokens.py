from __future__ import annotations

import re


TOKEN_SPLIT_RE = re.compile(r"[,;\s]+")


def parse_token_text(text: str) -> list[str]:
    return [item.strip() for item in TOKEN_SPLIT_RE.split(text) if item.strip()]


def join_multiline(items: list[str]) -> str:
    return "\n".join(items)
