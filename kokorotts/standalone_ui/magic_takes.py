"""Adapted from Hangry Labs VoxCPMTTS, Apache-2.0; see THIRD_PARTY_NOTICES.md."""

from __future__ import annotations

import io
import json
import struct
import wave
from collections.abc import Sequence

import numpy as np

MAGIC_TAKE_MEDIA_TYPE = "application/vnd.hangrylabs.magic-takes"
MAGIC_TAKE_BUNDLE_VERSION = 1


def decode_pcm16_mono_wav(data: bytes) -> tuple[int, np.ndarray]:
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            if source.getnchannels() != 1:
                raise ValueError("Magic takes must be mono WAV audio.")
            if source.getsampwidth() != 2 or source.getcomptype() != "NONE":
                raise ValueError(
                    "Magic takes must use uncompressed 16-bit PCM WAV audio."
                )
            sample_rate = source.getframerate()
            if not 8_000 <= sample_rate <= 192_000:
                raise ValueError(
                    "Magic take sample rate is outside the supported range."
                )
            frames = source.getnframes()
            payload = source.readframes(frames)
    except (EOFError, wave.Error) as exc:
        raise ValueError("Magic take is not a valid WAV file.") from exc
    waveform = np.frombuffer(payload, dtype="<i2").astype(np.int16, copy=True)
    if waveform.size != frames:
        raise ValueError("Magic take WAV data is incomplete.")
    return sample_rate, waveform


def pack_magic_take_bundle(
    takes: Sequence[tuple[str, int, bytes]],
    output: bytes,
    *,
    sample_rate: int,
    output_format: str,
    output_media_type: str,
    request_seed: int,
    committed_profiles: dict[str, str] | None = None,
    metrics: dict | None = None,
) -> bytes:
    payload = bytearray()
    take_manifest: list[dict[str, int | str]] = []
    for take_id, seed, audio in takes:
        offset = len(payload)
        payload.extend(audio)
        take_manifest.append(
            {
                "id": take_id,
                "seed": int(seed),
                "offset": offset,
                "length": len(audio),
                "media_type": "audio/wav",
                "extension": "wav",
            }
        )
    output_offset = len(payload)
    payload.extend(output)
    manifest = {
        "version": MAGIC_TAKE_BUNDLE_VERSION,
        "request_seed": int(request_seed),
        "sample_rate": int(sample_rate),
        "committed_profiles": committed_profiles or {},
        "metrics": metrics or {},
        "takes": take_manifest,
        "output": {
            "offset": output_offset,
            "length": len(output),
            "media_type": output_media_type,
            "extension": output_format,
        },
    }
    encoded_manifest = json.dumps(
        manifest, ensure_ascii=True, separators=(",", ":")
    ).encode("utf-8")
    return struct.pack("<I", len(encoded_manifest)) + encoded_manifest + payload


__all__ = [
    "MAGIC_TAKE_BUNDLE_VERSION",
    "MAGIC_TAKE_MEDIA_TYPE",
    "decode_pcm16_mono_wav",
    "pack_magic_take_bundle",
]
