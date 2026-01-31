"""ROM filename parsing helpers."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

_LANG_TOKEN_RE = re.compile(r"\(([A-Za-z]{2}(?:\s*,\s*[A-Za-z]{2})*)\)")
_VERSION_RE = re.compile(
    r"\b(v\d+(?:\.\d+)*|rev\s*[0-9a-z]+|final|beta|alpha|demo|prototype|proto|sample)\b",
    re.IGNORECASE,
)

_REGION_PAREN_TOKEN_RE = re.compile(r"\(([^\)]*)\)")
_REGION_HINT_RE = re.compile(
    r"\b(europe|eur|pal|usa|u\.?s\.?a\.?|united\s+states|ntsc-u|japan|ntsc-j|world)\b",
    re.IGNORECASE,
)


def infer_languages_and_version_from_name(name: str) -> Tuple[Tuple[str, ...], Optional[str]]:
    """Infer language codes and a version tag from a ROM filename."""

    filename = os.path.basename(str(name or ""))

    lang_tokens: List[str] = []
    for match in _LANG_TOKEN_RE.finditer(filename):
        raw = match.group(1) or ""
        for token in raw.split(","):
            token = token.strip()
            if len(token) == 2 and token.isalpha():
                lang_tokens.append(token.title())

    languages = tuple(sorted(set(lang_tokens)))

    version = None
    m = _VERSION_RE.search(filename)
    if m:
        raw = (m.group(1) or "").strip()
        low = raw.lower()
        if low.startswith("rev"):
            tail = raw[3:].strip()
            version = f"Rev {tail}".strip()
        elif low.startswith("v") and any(ch.isdigit() for ch in raw):
            version = raw.lower()
        else:
            version = raw.title()

    return languages, version


def infer_region_from_name(name: str) -> Optional[str]:
    filename = os.path.basename(str(name or ""))
    tokens = _REGION_PAREN_TOKEN_RE.findall(filename)
    for token in tokens:
        cleaned = token.strip().lower()
        if not cleaned:
            continue
        if cleaned in ("europe", "eur", "pal", "e"):
            return "Europe"
        if cleaned in ("usa", "u.s.a.", "u", "united states", "ntsc-u"):
            return "USA"
        if cleaned in ("japan", "j", "ntsc-j"):
            return "Japan"
        if cleaned in ("world", "w"):
            return "World"

    hint = _REGION_HINT_RE.search(filename)
    if hint:
        cleaned = hint.group(1).lower()
        if cleaned in ("europe", "eur", "pal"):
            return "Europe"
        if cleaned in ("usa", "u.s.a.", "united states", "ntsc-u"):
            return "USA"
        if cleaned in ("japan", "ntsc-j"):
            return "Japan"
        if cleaned in ("world",):
            return "World"

    return "Unknown"


def normalize_title_for_dedupe(name: str) -> str:
    filename = Path(str(name or "")).name
    stem = Path(filename).stem
    value = re.sub(r"\([^\)]*\)", "", stem)
    value = re.sub(r"\[[^\]]*\]", "", value)
    value = _VERSION_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def version_score(version: Optional[str]) -> float:
    if not version:
        return 0.0
    raw = str(version).strip().lower()
    if not raw:
        return 0.0

    if raw.startswith("rev"):
        tail = raw.replace("rev", "").strip()
        if tail.isdigit():
            return 50.0 + float(tail)
        if tail and tail[0].isalpha():
            return 50.0 + (ord(tail[0]) - ord("a") + 1) / 10.0

    if raw.startswith("v"):
        tail = raw[1:]
        parts = [p for p in re.split(r"[^0-9]+", tail) if p]
        score = 100.0
        for idx, part in enumerate(parts[:3]):
            try:
                value = int(part)
            except Exception:
                value = 0
            score += value / (10 ** idx)
        return score

    if "final" in raw:
        return 90.0
    if "beta" in raw:
        return 10.0
    if "alpha" in raw or "proto" in raw or "prototype" in raw:
        return 5.0

    return 1.0
