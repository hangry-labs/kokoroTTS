"""KokoroTTS HTTP API routes."""

from __future__ import annotations

import io
import os
from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np
import torch
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from . import __version__ as KOKORO_VERSION
from .audio import (
    FORMAT_ALIASES,
    OUTPUT_FORMATS,
    SAMPLE_RATE,
    STREAM_FORMAT_ALIASES,
    STREAM_FORMATS,
    apply_audio_effects,
    encode_audio_bytes,
    encode_pcm_s16le,
    get_supported_output_formats,
    normalize_output_format,
    normalize_stream_format,
    to_int16_audio,
)
from .catalog import (
    LANGUAGE_CHOICES,
    VOICE_CHOICES,
    voice_inventory,
    voice_language,
    voices_for_language,
)
from .runtime import InferenceRuntime, SynthesisResult
from .sample_texts import get_initial_text, get_intro_text, get_random_quote
from .schemas import MetricsRequest, PurgeRequest, StreamingTTSRequest, TTSRequest

APP_VERSION = os.getenv("APP_VERSION", KOKORO_VERSION)
BUILD_ID = os.getenv("BUILD_ID", "stable")
DEFAULT_DEVICE = os.getenv("KOKOROTTS_DEVICE", "auto")

# Tiny images intentionally download all advertised voices before readiness so every
# language behaves predictably for UI and API users.
RUNTIME = InferenceRuntime(eager_voices=True)


@dataclass(frozen=True)
class ProcessedSynthesis:
    output_format: str
    sample_rate: int
    waveform: np.ndarray
    inference: SynthesisResult | None


def get_cuda_devices() -> list[str]:
    if not torch.cuda.is_available():
        return []
    return [
        torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())
    ]


def get_runtime_label() -> str:
    cuda_devices = get_cuda_devices()
    if not cuda_devices:
        return "CPU"
    visible = os.getenv("CUDA_VISIBLE_DEVICES", "all")
    device_list = ", ".join(
        f"{index}:{name}" for index, name in enumerate(cuda_devices)
    )
    return f"GPU x{len(cuda_devices)} (visible={visible}) [{device_list}]"


def get_hardware_choices() -> list[tuple[str, str]]:
    choices = [("Auto", "auto"), ("CPU", "cpu")]
    choices.extend(
        (f"GPU {index} ({name})", f"cuda:{index}")
        for index, name in enumerate(get_cuda_devices())
    )
    return choices


def normalize_device(hardware: str) -> str:
    hardware = (hardware or "auto").strip().lower()
    if hardware == "auto":
        return "cuda:0" if get_cuda_devices() else "cpu"
    if hardware in {"gpu", "cuda"}:
        return "cuda:0"
    if hardware == "cpu":
        return "cpu"
    if hardware.startswith("cuda"):
        cuda_devices = get_cuda_devices()
        if not cuda_devices:
            raise RuntimeError("CUDA device requested but CUDA is not available")
        try:
            device_index = int(hardware.split(":", 1)[1])
        except (IndexError, ValueError) as exc:
            raise RuntimeError(
                f"Unsupported device '{hardware}'. Use auto, cpu, or cuda:N."
            ) from exc
        if device_index < 0 or device_index >= len(cuda_devices):
            raise RuntimeError(
                f"CUDA device index {device_index} is not available. "
                f"Visible CUDA devices: 0-{len(cuda_devices) - 1}."
            )
        return f"cuda:{device_index}"
    raise RuntimeError(f"Unsupported device '{hardware}'. Use auto, cpu, or cuda:N.")


def resolve_requested_hardware(device: str, use_gpu: bool | None = None) -> str:
    if use_gpu is True:
        return "auto"
    if use_gpu is False:
        return "cpu"
    return device


def validate_request(
    payload: TTSRequest, *, streaming: bool = False
) -> tuple[str, str]:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")
    if payload.voice not in VOICE_CHOICES.values():
        raise HTTPException(status_code=400, detail=f"Invalid voice '{payload.voice}'")
    try:
        requested_format = (
            normalize_stream_format(payload.stream_format)
            if streaming and isinstance(payload, StreamingTTSRequest)
            else normalize_output_format(payload.output_format)
        )
        device = normalize_device(
            resolve_requested_hardware(payload.device, payload.use_gpu)
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return requested_format, device


def apply_request_effects(waveform: np.ndarray, payload: TTSRequest) -> np.ndarray:
    try:
        return apply_audio_effects(
            waveform,
            SAMPLE_RATE,
            payload.pitch_semitones,
            payload.tempo,
            payload.volume,
            payload.normalize,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def synthesize_payload(payload: TTSRequest) -> ProcessedSynthesis:
    output_format, device = validate_request(payload)
    inference = RUNTIME.synthesize(payload.text, payload.voice, payload.speed, device)
    waveform = inference.audio if inference else np.zeros(0, dtype=np.int16)
    return ProcessedSynthesis(
        output_format=output_format,
        sample_rate=SAMPLE_RATE,
        waveform=apply_request_effects(waveform, payload),
        inference=inference,
    )


def audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    result = synthesize_payload(payload)
    try:
        audio_bytes = encode_audio_bytes(
            result.waveform, result.output_format, result.sample_rate
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    config = OUTPUT_FORMATS[result.output_format]
    duration = len(result.waveform) / result.sample_rate if result.sample_rate else 0
    headers = {
        "Content-Disposition": f"attachment; filename=kokorotts_{payload.voice}.{config['extension']}",
        "X-KokoroTTS-Voice": payload.voice,
        "X-KokoroTTS-Language": voice_language(payload.voice),
        "X-KokoroTTS-Sample-Rate": str(result.sample_rate),
        "X-KokoroTTS-Duration": f"{duration:.3f}",
        "X-KokoroTTS-Route": route_name,
    }
    if result.output_format != "wav":
        headers["X-KokoroTTS-Format"] = result.output_format
    if result.inference:
        headers["X-KokoroTTS-Inference-Device"] = ",".join(
            result.inference.inference_devices
        )
        if result.inference.fallback_reason:
            headers["X-KokoroTTS-Fallback"] = "cpu"
            headers["X-KokoroTTS-Warning"] = (
                "CUDA inference failed; audio was generated on CPU"
            )
    return StreamingResponse(
        io.BytesIO(audio_bytes), media_type=config["media_type"], headers=headers
    )


def iter_stream_audio(
    payload: StreamingTTSRequest, stream_format: str, device: str
) -> Iterator[bytes]:
    for chunk in RUNTIME.iter_synthesis(
        payload.text, payload.voice, payload.speed, device
    ):
        audio = apply_request_effects(to_int16_audio(chunk.audio), payload)
        if stream_format == "pcm_s16le":
            yield encode_pcm_s16le(audio)
        else:
            yield encode_audio_bytes(audio, "mp3", SAMPLE_RATE)


def get_text_metrics(text: str, voice: str = "af_heart") -> dict[str, int | str]:
    phoneme_segments = []
    if text.strip():
        try:
            phoneme_segments = RUNTIME.phoneme_segments(text, voice)
        except Exception:  # noqa: BLE001 - metrics stay best-effort for UI compatibility
            phoneme_segments = []
    return {
        "characters": len(text or ""),
        "words": len((text or "").split()),
        "segments": len(phoneme_segments),
        "phoneme_characters": sum(len(segment) for segment in phoneme_segments),
    }


def get_phoneme_segments(text: str, voice: str = "af_heart") -> list[str]:
    if voice not in VOICE_CHOICES.values():
        raise ValueError(f"Invalid voice '{voice}'")
    return RUNTIME.phoneme_segments(text, voice) if text.strip() else []


api = FastAPI(
    title="TTS Service API",
    description="API documentation for the KokoroTTS service",
    version=KOKORO_VERSION,
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
)


@api.get("/tts/ping")
def ping() -> dict:
    return {
        "msg": "pong",
        "type": "KokoroTTS",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
    }


@api.get("/tts/status")
def status() -> dict:
    return {
        "msg": "pong",
        "type": "KokoroTTS",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
        "runtime": get_runtime_label(),
        "device": DEFAULT_DEVICE,
        "repo_id": RUNTIME.repo_id,
        "sample_rate": SAMPLE_RATE,
        "configured_languages": list(LANGUAGE_CHOICES),
        "languages": LANGUAGE_CHOICES,
        "voices": len(VOICE_CHOICES),
        "loaded_model_devices": RUNTIME.loaded_model_devices,
        "last_inference_fallback": RUNTIME.last_fallback,
        "hardware": [
            {"label": label, "value": value} for label, value in get_hardware_choices()
        ],
        "output_formats": get_supported_output_formats(),
        "stream_formats": STREAM_FORMATS,
    }


@api.get("/tts/defaults")
def defaults() -> dict:
    return {
        "text": get_initial_text(),
        "voice": "af_heart",
        "speed": 1.0,
        "device": "auto",
        "audio_controls": {
            "pitch_semitones": 0.0,
            "tempo": 1.0,
            "volume": 1.0,
            "normalize": False,
        },
        "output_formats": {
            "default": "wav",
            "available": get_supported_output_formats(),
        },
        "stream_formats": {"default": "pcm_s16le", "available": STREAM_FORMATS},
    }


@api.get("/tts/formats")
def formats() -> dict:
    return {
        "default": "wav",
        "formats": get_supported_output_formats(),
        "aliases": FORMAT_ALIASES,
    }


@api.get("/tts/stream-formats")
def stream_formats() -> dict:
    return {
        "default": "pcm_s16le",
        "formats": STREAM_FORMATS,
        "aliases": STREAM_FORMAT_ALIASES,
        "granularity": "kokoro_pipeline_segment",
        "notes": [
            "pcm_s16le is raw mono 16-bit little-endian PCM at 24000 Hz.",
            "mp3 streams are sent as consecutive encoded Kokoro pipeline chunks.",
        ],
    }


@api.get("/tts/languages")
def languages() -> dict:
    return {"languages": LANGUAGE_CHOICES, "loaded_languages": list(LANGUAGE_CHOICES)}


@api.get("/tts/samples")
def samples(
    language: str = Query("a", description="Kokoro language prefix."),
    random_sample: bool = Query(
        False,
        alias="random",
        description="Return a random sample instead of the intro.",
    ),
) -> dict:
    if language not in LANGUAGE_CHOICES:
        raise HTTPException(status_code=404, detail="Language not found")
    voice = voices_for_language(language)[0]
    text = get_random_quote(voice) if random_sample else get_intro_text(voice)
    return {
        "language": language,
        "language_name": LANGUAGE_CHOICES[language],
        "text": text,
        "random": random_sample,
    }


@api.get("/tts/speakers")
def speakers(language: str = Query("a", description="Kokoro language prefix.")) -> dict:
    if language not in LANGUAGE_CHOICES:
        raise HTTPException(status_code=404, detail="Language not found")
    return {
        "language": language,
        "language_name": LANGUAGE_CHOICES[language],
        "speakers": voices_for_language(language),
    }


@api.get("/tts/voices")
def voices() -> dict:
    return {"voices": voice_inventory()}


@api.post("/tts/metrics")
def metrics(payload: MetricsRequest) -> dict:
    return {
        "voice": payload.voice,
        "language": voice_language(payload.voice),
        "metrics": get_text_metrics(payload.text, payload.voice),
    }


@api.post("/tts/tokenize")
def tokenize(payload: MetricsRequest) -> dict:
    try:
        segments = get_phoneme_segments(payload.text, payload.voice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "voice": payload.voice,
        "language": voice_language(payload.voice),
        "segments": segments,
        "phonemes": "\n".join(segments),
        "metrics": {
            "characters": len(payload.text or ""),
            "words": len((payload.text or "").split()),
            "segments": len(segments),
            "phoneme_characters": sum(len(segment) for segment in segments),
        },
    }


@api.post("/tts/generate")
def generate_tts(payload: TTSRequest) -> StreamingResponse:
    return audio_response(payload, "/tts/generate")


@api.post("/tts/stream")
async def stream_tts(
    request: Request, payload: StreamingTTSRequest
) -> StreamingResponse:
    stream_format, device = validate_request(payload, streaming=True)
    config = STREAM_FORMATS[stream_format]

    async def disconnected_stream():
        iterator = iter(iter_stream_audio(payload, stream_format, device))
        try:
            async for chunk in iterate_in_threadpool(iterator):
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            close = getattr(iterator, "close", None)
            if close is not None:
                close()

    return StreamingResponse(
        disconnected_stream(),
        media_type=config["media_type"].format(sample_rate=SAMPLE_RATE),
        headers={
            "Content-Disposition": f"attachment; filename=kokorotts_{payload.voice}_stream.{config['extension']}",
            "X-KokoroTTS-Voice": payload.voice,
            "X-KokoroTTS-Language": voice_language(payload.voice),
            "X-KokoroTTS-Sample-Rate": str(SAMPLE_RATE),
            "X-KokoroTTS-Stream-Format": stream_format,
        },
    )


@api.post("/tts/purge")
def purge_models(payload: PurgeRequest | None = None) -> dict:
    requested_device = payload.device if payload else None
    if requested_device:
        try:
            requested_device = normalize_device(requested_device)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    purged, remaining = RUNTIME.purge(requested_device)
    return {"purged": purged, "remaining_model_devices": remaining}


@api.post("/tts/convert")
def convert(payload: TTSRequest) -> StreamingResponse:
    return audio_response(payload, "/tts/convert")
