"""Bounded experimental SSML parsing and phoneme-plan compilation."""

from __future__ import annotations

import re
import unicodedata
from math import isfinite
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

SSML_NAMESPACE = "http://www.w3.org/2001/10/synthesis"
MAX_SSML_CHARACTERS = 50_000
MAX_SSML_ELEMENTS = 256
MAX_BREAK_MS = 10_000
MAX_TOTAL_BREAK_MS = 30_000
MAX_PHONEME_CHARACTERS = 510
MAX_ORDINAL_DIGITS = 18

_BREAK_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)\s*(ms|s)$")
_INTEGER_PATTERN = re.compile(r"^\d+$")
_NUMBER_PATTERN = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


class SSMLValidationError(ValueError):
    """Raised when experimental SSML input is malformed or unsupported."""


@dataclass(frozen=True)
class SSMLSegment:
    kind: Literal["text", "phoneme", "break"]
    value: str = ""
    duration_ms: int = 0


@dataclass(frozen=True)
class SSMLSynthesisUnit:
    kind: Literal["speech", "break"]
    phonemes: str = ""
    duration_ms: int = 0
    contains_phoneme_override: bool = False
    phoneme_override_characters: frozenset[str] = frozenset()


def _tag_name(tag: str) -> str:
    if tag.startswith("{"):
        namespace, separator, local_name = tag[1:].partition("}")
        if not separator or namespace != SSML_NAMESPACE:
            raise SSMLValidationError(f"Unsupported SSML namespace '{namespace}'.")
        return local_name
    return tag


def _require_attributes(element, allowed: set[str]) -> None:
    unknown = sorted(set(element.attrib) - allowed)
    if unknown:
        name = _tag_name(element.tag)
        raise SSMLValidationError(
            f"Unsupported attribute on <{name}>: {', '.join(unknown)}."
        )


def _plain_content(element, tag: str) -> str:
    if list(element):
        raise SSMLValidationError(f"Nested tags are not supported inside <{tag}>.")
    return element.text or ""


def _append_text(segments: list[SSMLSegment], value: str) -> None:
    if not value:
        return
    if segments and segments[-1].kind == "text":
        previous = segments[-1]
        segments[-1] = SSMLSegment("text", previous.value + value)
    else:
        segments.append(SSMLSegment("text", value))


def _parse_break_ms(value: str) -> int:
    match = _BREAK_PATTERN.fullmatch(value.strip())
    if not match:
        raise SSMLValidationError(
            "<break time> must use seconds or milliseconds, for example 500ms or 1.5s."
        )
    amount = float(match.group(1))
    multiplier = 1000 if match.group(2) == "s" else 1
    if not isfinite(amount) or amount * multiplier > MAX_BREAK_MS:
        raise SSMLValidationError(
            f"Each <break> is limited to {MAX_BREAK_MS / 1000:g} seconds."
        )
    duration_ms = round(amount * multiplier)
    return duration_ms


def _english_ordinal(value: str) -> str:
    number = int(value)
    remainder = number % 100
    if 10 <= remainder <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _say_as(value: str, interpretation: str, language: str) -> str:
    content = value.strip()
    if not content:
        raise SSMLValidationError("<say-as> content must not be empty.")
    if interpretation == "characters":
        return " ".join(content)
    if interpretation == "number":
        if not _NUMBER_PATTERN.fullmatch(content):
            raise SSMLValidationError(
                "<say-as interpret-as='number'> requires a numeric value."
            )
        return content
    if interpretation == "ordinal":
        if language not in {"a", "b"}:
            raise SSMLValidationError(
                "Experimental ordinal <say-as> currently supports English voices only."
            )
        if not _INTEGER_PATTERN.fullmatch(content):
            raise SSMLValidationError(
                "<say-as interpret-as='ordinal'> requires a non-negative integer."
            )
        if len(content) > MAX_ORDINAL_DIGITS:
            raise SSMLValidationError(
                f"Experimental ordinal values are limited to {MAX_ORDINAL_DIGITS} digits."
            )
        return _english_ordinal(content)
    raise SSMLValidationError(
        "Unsupported <say-as interpret-as> value. Use characters, number, or ordinal."
    )


def _validate_phonemes(value: str) -> str:
    phonemes = value.strip()
    if not phonemes:
        raise SSMLValidationError("<phoneme ph> must not be empty.")
    if len(phonemes) > MAX_PHONEME_CHARACTERS:
        raise SSMLValidationError(
            f"A phoneme override is limited to {MAX_PHONEME_CHARACTERS} characters."
        )
    if any(unicodedata.category(character).startswith("C") for character in phonemes):
        raise SSMLValidationError("<phoneme ph> contains unsupported control characters.")
    return phonemes


def parse_ssml(document: str, language: str) -> list[SSMLSegment]:
    """Parse the documented SSML subset without loading models or producing audio."""
    if len(document) > MAX_SSML_CHARACTERS:
        raise SSMLValidationError(
            f"Experimental SSML input is limited to {MAX_SSML_CHARACTERS} characters."
        )
    try:
        root = ElementTree.fromstring(
            document,
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        )
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise SSMLValidationError(f"Invalid or unsafe SSML: {exc}") from exc

    if _tag_name(root.tag) != "speak":
        raise SSMLValidationError("SSML input must have one <speak> root element.")
    _require_attributes(root, {"version"})
    if root.attrib.get("version", "1.0") != "1.0":
        raise SSMLValidationError("Only SSML version 1.0 is supported.")
    if sum(1 for _ in root.iter()) > MAX_SSML_ELEMENTS:
        raise SSMLValidationError(
            f"Experimental SSML is limited to {MAX_SSML_ELEMENTS} elements."
        )

    segments: list[SSMLSegment] = []
    total_break_ms = 0
    _append_text(segments, root.text or "")

    for element in root:
        tag = _tag_name(element.tag)
        if tag == "break":
            _require_attributes(element, {"time"})
            if list(element) or (element.text and element.text.strip()):
                raise SSMLValidationError("<break> must be empty.")
            if "time" not in element.attrib:
                raise SSMLValidationError("<break> requires a time attribute.")
            duration_ms = _parse_break_ms(element.attrib["time"])
            total_break_ms += duration_ms
            if total_break_ms > MAX_TOTAL_BREAK_MS:
                raise SSMLValidationError(
                    f"Total SSML break time is limited to {MAX_TOTAL_BREAK_MS / 1000:g} seconds."
                )
            if duration_ms:
                segments.append(SSMLSegment("break", duration_ms=duration_ms))
        elif tag == "phoneme":
            _require_attributes(element, {"alphabet", "ph"})
            _plain_content(element, tag)
            if element.attrib.get("alphabet") != "ipa":
                raise SSMLValidationError(
                    "<phoneme> requires alphabet='ipa' using Kokoro/eSpeak-compatible IPA."
                )
            if "ph" not in element.attrib:
                raise SSMLValidationError("<phoneme> requires a ph attribute.")
            segments.append(
                SSMLSegment("phoneme", _validate_phonemes(element.attrib["ph"]))
            )
        elif tag == "sub":
            _require_attributes(element, {"alias"})
            _plain_content(element, tag)
            alias = element.attrib.get("alias", "").strip()
            if not alias:
                raise SSMLValidationError("<sub> requires a non-empty alias attribute.")
            _append_text(segments, alias)
        elif tag == "say-as":
            _require_attributes(element, {"interpret-as"})
            content = _plain_content(element, tag)
            interpretation = element.attrib.get("interpret-as", "")
            _append_text(segments, _say_as(content, interpretation, language))
        else:
            raise SSMLValidationError(f"Unsupported SSML element <{tag}>.")
        _append_text(segments, element.tail or "")

    if not segments:
        raise SSMLValidationError("SSML input must contain speech or a break.")
    return segments


def _join_phonemes(left: str, right: str) -> str:
    if not left:
        return right.strip()
    if not right:
        return left
    return f"{left.rstrip()} {right.lstrip()}"


def compile_ssml(
    document: str,
    language: str,
    phonemize: Callable[[str], Iterable[str]],
) -> list[SSMLSynthesisUnit]:
    """Compile SSML into model-safe speech units and bounded silence units."""
    units: list[SSMLSynthesisUnit] = []
    pending = ""
    pending_override = False
    pending_override_characters: set[str] = set()

    def flush() -> None:
        nonlocal pending, pending_override, pending_override_characters
        if pending:
            units.append(
                SSMLSynthesisUnit(
                    "speech",
                    phonemes=pending,
                    contains_phoneme_override=pending_override,
                    phoneme_override_characters=frozenset(
                        pending_override_characters
                    ),
                )
            )
        pending = ""
        pending_override = False
        pending_override_characters = set()

    for segment in parse_ssml(document, language):
        if segment.kind == "break":
            flush()
            units.append(SSMLSynthesisUnit("break", duration_ms=segment.duration_ms))
            continue

        chunks = (
            [segment.value]
            if segment.kind == "phoneme"
            else [chunk for chunk in phonemize(segment.value) if chunk]
        )
        for chunk in chunks:
            if len(chunk) > MAX_PHONEME_CHARACTERS:
                raise SSMLValidationError(
                    f"Compiled phoneme segment exceeds {MAX_PHONEME_CHARACTERS} characters."
                )
            combined = _join_phonemes(pending, chunk)
            if pending and len(combined) > MAX_PHONEME_CHARACTERS:
                flush()
                combined = chunk.strip()
            pending = combined
            pending_override = pending_override or segment.kind == "phoneme"
            if segment.kind == "phoneme":
                pending_override_characters.update(chunk)

    flush()
    return units
