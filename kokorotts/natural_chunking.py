"""Opt-in non-English chunking with punctuation and word-aware boundaries."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterator
from math import ceil


_CLOSERS = frozenset(")]\"'}\u201d\u2019\u300d\u300f\u3009\u300b\uff09\u3011")
_SENTENCE_MARKS = re.compile(r"[.!?\u2026\u3002\uff01\uff1f\u0964]+")
_CLAUSE_MARKS = re.compile(r"[,;:\u2014\u3001\uff0c\uff1b\uff1a]+")
_ASCII_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]*")
_DECIMAL = re.compile(r"\d+(?:[.,]\d+)+")


class ChunkingValidationError(ValueError):
    """Text cannot be represented safely within the model's chunk limit."""


def _find_cut(text: str, target: int, maximum: int) -> int:
    maximum = min(maximum, len(text) - 1)
    target = max(1, min(target, maximum))
    minimum = max(1, target // 2)
    upper = min(maximum, target + max(1, target // 2))
    # Protect words and numeric tokens when a nearby alternative exists. The
    # final hard cut still guarantees progress for an oversized token.
    protected = set()
    for pattern in (_ASCII_TOKEN, _DECIMAL):
        for match in pattern.finditer(text[: upper + 1]):
            protected.update(range(match.start() + 1, match.end()))

    def eligible(position: int) -> bool:
        return (
            minimum <= position <= upper
            and position not in protected
            and text[position] not in _CLOSERS
            and not unicodedata.combining(text[position])
            and bool(text[:position].strip())
            and bool(text[position:].strip())
        )

    def after_marks(pattern: re.Pattern[str]) -> list[int]:
        positions = []
        for match in pattern.finditer(text[:upper]):
            position = match.end()
            while position < len(text) and text[position] in _CLOSERS:
                position += 1
            if eligible(position):
                positions.append(position)
        return positions

    def hiragana(character: str) -> bool:
        return "\u3041" <= character <= "\u309f"

    tiers = (
        after_marks(_SENTENCE_MARKS),
        after_marks(_CLAUSE_MARKS),
        [match.end() for match in re.finditer(r"\s+", text[:upper])],
        [
            position
            for position in range(minimum, upper + 1)
            if hiragana(text[position - 1])
            and not hiragana(text[position])
            and text[position].isalnum()
        ],
        range(minimum, upper + 1),
    )
    for positions in tiers:
        candidates = [position for position in positions if eligible(position)]
        if candidates:
            return min(candidates, key=lambda position: (abs(position - target), position))
    return target


def _text_chunks(text: str, maximum: int = 400) -> Iterator[str]:
    while len(text) > maximum:
        cut = _find_cut(text, maximum, maximum)
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


def phonemize_naturally(
    text: str,
    phonemize: Callable[[str], tuple[str, object]],
    phoneme_limit: int,
) -> Iterator[tuple[str, str]]:
    """Re-phonemize smaller pieces until every complete chunk fits the model."""
    for initial in _text_chunks(text):
        pending = [initial]
        while pending:
            chunk = pending.pop()
            if not chunk.strip():
                continue
            phonemes, _ = phonemize(chunk)
            if not phonemes:
                continue
            if len(phonemes) <= phoneme_limit:
                yield chunk, phonemes
                continue
            if len(chunk) == 1:
                raise ChunkingValidationError(
                    f"A single text character expands beyond {phoneme_limit} phonemes; "
                    "shorten or replace that character, or disable experimental chunking."
                )
            parts = ceil(len(phonemes) / phoneme_limit)
            target = max(1, len(chunk) // parts)
            cut = _find_cut(chunk, target, len(chunk) - 1)
            pending.extend((chunk[cut:], chunk[:cut]))
