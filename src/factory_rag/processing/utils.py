import hashlib
import math
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "find",
    "for",
    "get",
    "give",
    "has",
    "have",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "please",
    "show",
    "the",
    "this",
    "what",
    "which",
    "who",
    "with",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def normalize_name(value):
    if not value:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(cleaned.split())


def clean_text(value):
    if not value:
        return ""
    value = value.replace("\x00", " ")
    lines = []
    for line in value.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def short_snippet(value, limit=260):
    value = re.sub(r"\s+", " ", value or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def normalize_search_text(value):
    value = value or ""
    normalized = value.replace(",", "")
    normalized = re.sub(r"(?<=\d)\s+(?=\d)", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _token_variants(token):
    variants = []

    if re.search(r"[/-]", token):
        parts = [part for part in re.split(r"[/.-]+", token) if part]
        if len(parts) > 1:
            variants.append(" ".join(parts))
            variants.append("".join(parts))

    compact_numeric = re.sub(r"[^0-9.]", "", token)
    if compact_numeric and compact_numeric != token and re.search(r"\d", token):
        variants.append(compact_numeric)

    return variants


def build_search_text(value):
    normalized = normalize_search_text(value).lower()
    if not normalized:
        return ""

    pieces = [normalized]
    seen = {normalized}

    for token in re.findall(r"[a-z0-9./-]+", normalized):
        for variant in _token_variants(token):
            if variant and variant not in seen:
                seen.add(variant)
                pieces.append(variant)

    return " ".join(pieces)


def extract_search_terms(value):
    normalized = normalize_search_text(value).lower()
    terms = []
    seen = set()

    for term in re.findall(r"[a-z0-9.\-/]+", normalized):
        if term in SEARCH_STOPWORDS:
            continue
        if len(term) < 3 and not re.search(r"\d", term):
            continue
        if term not in seen:
            seen.add(term)
            terms.append(term)

        for variant in _token_variants(term):
            if len(variant) < 3 and not re.search(r"\d", variant):
                continue
            if variant not in seen:
                seen.add(variant)
                terms.append(variant)

    return terms


def json_ready(value):
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        items = []
        for item in value:
            items.append(json_ready(item))
        return items
    if isinstance(value, tuple):
        items = []
        for item in value:
            items.append(json_ready(item))
        return items
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def hash_embed(text, vector_size):
    vector = [0.0] * vector_size
    tokens = re.findall(r"[a-z0-9]{2,}", (text or "").lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % vector_size
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if not norm:
        return vector

    normalized = []
    for value in vector:
        normalized.append(value / norm)
    return normalized
