"""Kokoro processor profile for the shared, engine-neutral SSML-H compiler.

Legacy SSML deliberately keeps its established parser and model-speed semantics.
Standard SSML-H rate is post-processing tempo, not Kokoro's model speed.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from xml.etree import ElementTree as XML

from defusedxml import ElementTree as SafeXML
from ssml_h import compile_ssml, ssml_capabilities

from .catalog import resolve_language_code, voice_language
from .ssml import SSMLProsody, SSMLSynthesisUnit, SSMLValidationError

LANGUAGE_TAGS = {
    "a": "en-US",
    "b": "en-GB",
    "e": "es-ES",
    "f": "fr-FR",
    "h": "hi-IN",
    "i": "it-IT",
    "j": "ja-JP",
    "p": "pt-BR",
    "z": "zh-CN",
    "d": "de-DE",
    "v": "vi-VN",
}


@dataclass(frozen=True)
class DialogueTurn:
    kind: str
    text: str = ""
    duration_ms: int = 0
    voice: str = ""
    language: str = ""
    prosody: SSMLProsody = field(default_factory=SSMLProsody)


def capabilities() -> dict:
    result = ssml_capabilities(description_supported=False)
    result["ssml"]["phoneme_alphabets"] = []
    result["ssml_h"].update(
        extensions=[],
        voice_scopes=[],
        voice_definitions_supported=False,
        design_processor={"supported": False},
        unsupported_reason="Kokoro uses pretrained voices; choose /tts/voices and per-turn prosody instead of voice design or cloning.",
    )
    result["limits"].update(voice_definitions=0, speech_turns=64, output_seconds=300)
    result["legacy_ssml"] = {
        "input_type": "ssml",
        "phoneme_alphabets": ["ipa"],
        "prosody_attributes": ["speed", "pitch", "tempo", "volume"],
        "phoneme_characters": 510,
    }
    result["magic"] = {"supported": True, "take_rate": 24000, "seed_supported": False}
    result["ssml"]["prosody_bounds"] = {
        "rate": [0.5, 2],
        "pitch_semitones": [-12, 12],
        "volume": [0, 2],
    }
    return result


def parse_dialogue(document: str, voice: str, serves_voice=None) -> list[DialogueTurn]:
    def validate_voice(name, _definitions):
        if serves_voice is not None and not serves_voice(name):
            raise ValueError(
                f"Voice '{name}' is disabled or unknown. Choose an enabled voice from /tts/voices or enable its model pack in System."
            )
        voice_language(name)

    def language_tag(value):
        return LANGUAGE_TAGS[resolve_language_code(value)]

    try:
        validate_voice(voice, frozenset())
        plan = compile_ssml(
            document,
            "ssml-h",
            default_voice=voice,
            default_language=LANGUAGE_TAGS[voice_language(voice)],
            resolve_language=language_tag,
            validate_voice=validate_voice,
        )
        if plan.voice_definitions:
            raise ValueError(capabilities()["ssml_h"]["unsupported_reason"])
        # The shared semantic compiler coalesces equal contexts. Preserve explicit
        # document-level turns for Magic take identity, including same-voice turns.
        # First validate the WHOLE document so splitting cannot bypass global limits.
        root = SafeXML.fromstring(
            document, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
        units = []

        def add_block(text="", child=None):
            wrapper = XML.Element(root.tag, dict(root.attrib))
            wrapper.text = text
            if child is not None:
                item = deepcopy(child)
                item.tail = None
                wrapper.append(item)
            if not text.strip() and child is None:
                return
            partial = compile_ssml(
                XML.tostring(wrapper, encoding="unicode"),
                "ssml-h",
                default_voice=voice,
                default_language=LANGUAGE_TAGS[voice_language(voice)],
                resolve_language=language_tag,
                validate_voice=validate_voice,
            )
            units.extend(partial.units)

        add_block(root.text or "")
        for child in root:
            if child.tag.rsplit("}", 1)[-1] != "metadata":
                add_block(child=child)
            add_block(child.tail or "")
        if sum(unit.kind == "speech" for unit in units) > 64:
            raise ValueError(
                "Magic supports up to 64 speech turns. Split this script into smaller documents."
            )
        turns = []
        for unit in units:
            selected = unit.voice or voice
            language = (
                resolve_language_code(unit.language)
                if unit.language_explicit
                else voice_language(selected)
            )
            prosody = SSMLProsody(
                tempo=unit.prosody.rate,
                pitch_semitones=unit.prosody.pitch_semitones,
                volume=unit.prosody.volume,
            )
            if (
                not 0.5 <= prosody.tempo <= 2
                or not -12 <= prosody.pitch_semitones <= 12
                or not 0 <= prosody.volume <= 2
            ):
                raise ValueError(
                    "Kokoro SSML-H requires effective rate 0.5-2, pitch -12 to 12 semitones, and volume 0-2."
                )
            turns.append(
                DialogueTurn(
                    unit.kind, unit.text, unit.duration_ms, selected, language, prosody
                )
            )
        return turns
    except ValueError as exc:
        raise SSMLValidationError(str(exc)) from exc


def compile_dialogue(
    turns: list[DialogueTurn], phonemize
) -> list[list[SSMLSynthesisUnit]]:
    result = []
    for turn in turns:
        if turn.kind == "break":
            result.append(
                [
                    SSMLSynthesisUnit(
                        "break",
                        duration_ms=turn.duration_ms,
                        voice=turn.voice,
                        language=turn.language,
                    )
                ]
            )
        else:
            chunks = list(phonemize(turn.text, turn.language, turn.voice))
            if not chunks or any(not p or len(p) > 510 for p in chunks):
                raise SSMLValidationError(
                    "A dialogue turn produced empty or oversized phonemes. Change its text or split it into shorter turns."
                )
            result.append(
                [
                    SSMLSynthesisUnit(
                        "speech",
                        phonemes=p,
                        voice=turn.voice,
                        language=turn.language,
                        prosody=turn.prosody,
                    )
                    for p in chunks
                ]
            )
    return result
