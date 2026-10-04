"""KokoroTTS HTTP API routes."""

from __future__ import annotations

import io
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
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
    model_family_inventory,
    voice_ids,
    voice_inventory,
    voice_language,
    voices_for_language,
)
from .openai_compat import (
    OPENAI_MODEL_ID,
    OpenAIAPIError,
    openai_error_response,
    openai_speed_controls,
    openai_tts_request,
    require_openai_api_key,
    resolve_openai_model,
)
from .runtime import InferenceRuntime, SynthesisResult
from .sample_texts import get_initial_text, get_intro_text, get_random_quote
from .schemas import (
    MetricsRequest,
    OpenAISpeechRequest,
    PurgeRequest,
    ServedModelFamiliesRequest,
    ServedVoicesRequest,
    StreamingTTSRequest,
    TTSRequest,
)
from .ssml import SSMLSynthesisUnit, SSMLValidationError

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
    if not RUNTIME.serves_voice(payload.voice):
        raise HTTPException(
            status_code=400,
            detail=f"Voice '{payload.voice}' is not served by this deployment",
        )
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
    try:
        inference = RUNTIME.synthesize(
            payload.text,
            payload.voice,
            payload.speed,
            device,
            payload.input_type,
        )
    except SSMLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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
    if payload.input_type != "text":
        headers["X-KokoroTTS-Input-Type"] = payload.input_type
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
    payload: StreamingTTSRequest,
    stream_format: str,
    device: str,
    plan: list[SSMLSynthesisUnit] | None = None,
) -> Iterator[bytes]:
    for chunk in RUNTIME.iter_synthesis(
        payload.text,
        payload.voice,
        payload.speed,
        device,
        payload.input_type,
        plan,
    ):
        audio = apply_request_effects(to_int16_audio(chunk.audio), payload)
        if stream_format == "pcm_s16le":
            yield encode_pcm_s16le(audio)
        else:
            yield encode_audio_bytes(audio, "mp3", SAMPLE_RATE)


def get_text_metrics(
    text: str, voice: str = "af_heart", input_type: str = "text"
) -> dict[str, int | str]:
    phoneme_segments = []
    if text.strip():
        try:
            phoneme_segments = RUNTIME.phoneme_segments(text, voice, input_type)
        except Exception:  # noqa: BLE001 - metrics stay best-effort for UI compatibility
            if input_type == "ssml":
                raise
            phoneme_segments = []
    return {
        "characters": len(text or ""),
        "words": len((text or "").split()),
        "segments": len(phoneme_segments),
        "phoneme_characters": sum(len(segment) for segment in phoneme_segments),
    }


def get_phoneme_segments(
    text: str, voice: str = "af_heart", input_type: str = "text"
) -> list[str]:
    if not RUNTIME.serves_voice(voice):
        raise ValueError(f"Voice '{voice}' is not served by this deployment")
    return RUNTIME.phoneme_segments(text, voice, input_type) if text.strip() else []


api = FastAPI(
    title="KokoroTTS API",
    description="OpenAI-compatible speech and native KokoroTTS APIs",
    version=KOKORO_VERSION,
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
    openapi_tags=[
        {
            "name": "OpenAI-compatible API",
            "description": "Speech generation and model discovery for OpenAI clients.",
        },
        {"name": "Health", "description": "Container liveness and readiness."},
        {
            "name": "KokoroTTS native API",
            "description": "Full Kokoro controls, streaming, discovery, and diagnostics.",
        },
        {"name": "System", "description": "Deployment and model lifecycle controls."},
    ],
)


@api.exception_handler(OpenAIAPIError)
async def openai_api_error_handler(
    _request: Request, exc: OpenAIAPIError
) -> JSONResponse:
    return openai_error_response(
        exc.message,
        status_code=exc.status_code,
        error_type=exc.error_type,
        param=exc.param,
        code=exc.code,
        headers=exc.headers,
    )


@api.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
):
    if not request.url.path.startswith("/v1/"):
        return await request_validation_exception_handler(request, exc)
    first_error: dict[str, Any] = exc.errors()[0] if exc.errors() else {}
    location = [str(part) for part in first_error.get("loc", ()) if part != "body"]
    param = ".".join(location) or None
    message = first_error.get("msg", "Invalid request")
    if param:
        message = f"Invalid '{param}': {message}"
    return openai_error_response(
        message,
        status_code=400,
        param=param,
        code="invalid_parameter",
    )


@api.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if not request.url.path.startswith("/v1/"):
        return await http_exception_handler(request, exc)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return openai_error_response(
        detail,
        status_code=exc.status_code,
        headers=exc.headers,
    )


def health_payload() -> dict[str, Any]:
    served_voices = RUNTIME.served_voices
    return {
        "status": "ok" if served_voices else "not_ready",
        "service": "KokoroTTS",
        "version": APP_VERSION,
        "voices": len(served_voices),
    }


@api.get("/health/live", tags=["Health"])
def health_live() -> dict[str, str]:
    return {"status": "ok", "service": "KokoroTTS", "version": APP_VERSION}


@api.get("/health", tags=["Health"])
@api.get("/health/ready", tags=["Health"])
def health_ready() -> JSONResponse:
    payload = health_payload()
    return JSONResponse(payload, status_code=200 if payload["status"] == "ok" else 503)


@api.get(
    "/v1/models",
    tags=["OpenAI-compatible API"],
    dependencies=[Depends(require_openai_api_key)],
)
def openai_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": OPENAI_MODEL_ID,
                "object": "model",
                "owned_by": "hangry-labs",
            }
        ],
    }


@api.get(
    "/v1/models/{requested_model:path}",
    tags=["OpenAI-compatible API"],
    dependencies=[Depends(require_openai_api_key)],
)
def openai_model(requested_model: str) -> dict[str, str]:
    model = resolve_openai_model(requested_model)
    return {"id": model, "object": "model", "owned_by": "hangry-labs"}


@api.get("/tts/ping", tags=["KokoroTTS native API"])
def ping() -> dict:
    return {
        "msg": "pong",
        "type": "KokoroTTS",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
    }


@api.get("/tts/status", tags=["KokoroTTS native API"])
def status() -> dict:
    served_voices = RUNTIME.served_voices
    served_languages = list(dict.fromkeys(voice_language(voice) for voice in served_voices))
    return {
        "msg": "pong",
        "type": "KokoroTTS",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
        "runtime": get_runtime_label(),
        "device": DEFAULT_DEVICE,
        "repo_id": RUNTIME.repo_id,
        "sample_rate": SAMPLE_RATE,
        "configured_languages": served_languages,
        "languages": {
            code: name for code, name in LANGUAGE_CHOICES.items() if code in served_languages
        },
        "voices": len(served_voices),
        "loaded_model_devices": RUNTIME.loaded_model_devices,
        "loaded_models": RUNTIME.loaded_models,
        "last_inference_fallback": RUNTIME.last_fallback,
        "hardware": [
            {"label": label, "value": value} for label, value in get_hardware_choices()
        ],
        "output_formats": get_supported_output_formats(),
        "stream_formats": STREAM_FORMATS,
        "input_types": {
            "text": {"label": "Plain text", "experimental": False},
            "ssml": {"label": "SSML", "experimental": True},
        },
    }


@api.get("/tts/defaults", tags=["KokoroTTS native API"])
def defaults() -> dict:
    served_voices = RUNTIME.served_voices
    default_voice = "af_heart" if "af_heart" in served_voices else served_voices[0]
    return {
        "text": get_initial_text(),
        "input_type": "text",
        "input_types": {
            "text": {"label": "Plain text", "experimental": False},
            "ssml": {"label": "SSML", "experimental": True},
        },
        "voice": default_voice,
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


@api.get("/tts/formats", tags=["KokoroTTS native API"])
def formats() -> dict:
    return {
        "default": "wav",
        "formats": get_supported_output_formats(),
        "aliases": FORMAT_ALIASES,
    }


@api.get("/tts/stream-formats", tags=["KokoroTTS native API"])
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


@api.get("/tts/languages", tags=["KokoroTTS native API"])
def languages() -> dict:
    served_languages = list(
        dict.fromkeys(voice_language(voice) for voice in RUNTIME.served_voices)
    )
    languages = {
        code: name for code, name in LANGUAGE_CHOICES.items() if code in served_languages
    }
    return {"languages": languages, "loaded_languages": served_languages}


@api.get("/tts/samples", tags=["KokoroTTS native API"])
def samples(
    language: str = Query("a", description="Kokoro language prefix."),
    random_sample: bool = Query(
        False,
        alias="random",
        description="Return a random sample instead of the intro.",
    ),
) -> dict:
    available = voices_for_language(language, RUNTIME.served_voices)
    if language not in LANGUAGE_CHOICES or not available:
        raise HTTPException(status_code=404, detail="Language not found")
    voice = available[0]
    text = get_random_quote(voice) if random_sample else get_intro_text(voice)
    return {
        "language": language,
        "language_name": LANGUAGE_CHOICES[language],
        "text": text,
        "random": random_sample,
    }


@api.get("/tts/speakers", tags=["KokoroTTS native API"])
def speakers(language: str = Query("a", description="Kokoro language prefix.")) -> dict:
    available = voices_for_language(language, RUNTIME.served_voices)
    if language not in LANGUAGE_CHOICES or not available:
        raise HTTPException(status_code=404, detail="Language not found")
    return {
        "language": language,
        "language_name": LANGUAGE_CHOICES[language],
        "speakers": available,
    }


@api.get("/tts/voices", tags=["KokoroTTS native API"])
def voices() -> dict:
    return {"voices": voice_inventory(RUNTIME.served_voices)}


@api.get("/system/settings", tags=["System"])
def system_settings() -> dict:
    return deployment_settings_payload()


def deployment_settings_payload() -> dict:
    served = RUNTIME.served_voices
    return {
        "served_voices": served,
        "supported_voices": voice_inventory(voice_ids()),
        "served_model_families": RUNTIME.served_model_families,
        "supported_model_families": model_family_inventory(),
        "settings_path": str(RUNTIME.settings.path),
        "model_loading": "lazy",
    }


@api.put("/system/settings/model-families", tags=["System"])
def update_served_model_families(payload: ServedModelFamiliesRequest) -> dict:
    try:
        RUNTIME.set_served_model_families(payload.model_families)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return deployment_settings_payload()


@api.put("/system/settings/voices", tags=["System"])
def update_served_voices(payload: ServedVoicesRequest) -> dict:
    try:
        RUNTIME.set_served_voices(payload.voices)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return deployment_settings_payload()


@api.post("/tts/metrics", tags=["KokoroTTS native API"])
def metrics(payload: MetricsRequest) -> dict:
    if not RUNTIME.serves_voice(payload.voice):
        raise HTTPException(
            status_code=400,
            detail=f"Voice '{payload.voice}' is not served by this deployment",
        )
    try:
        result = get_text_metrics(payload.text, payload.voice, payload.input_type)
    except SSMLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "voice": payload.voice,
        "language": voice_language(payload.voice),
        "input_type": payload.input_type,
        "metrics": result,
    }


@api.post("/tts/tokenize", tags=["KokoroTTS native API"])
def tokenize(payload: MetricsRequest) -> dict:
    try:
        segments = get_phoneme_segments(
            payload.text, payload.voice, payload.input_type
        )
    except (ValueError, SSMLValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "voice": payload.voice,
        "language": voice_language(payload.voice),
        "input_type": payload.input_type,
        "segments": segments,
        "phonemes": "\n".join(segments),
        "metrics": {
            "characters": len(payload.text or ""),
            "words": len((payload.text or "").split()),
            "segments": len(segments),
            "phoneme_characters": sum(len(segment) for segment in segments),
        },
    }


@api.post(
    "/v1/audio/speech",
    tags=["OpenAI-compatible API"],
    dependencies=[Depends(require_openai_api_key)],
)
def openai_speech(payload: OpenAISpeechRequest) -> StreamingResponse:
    tts_payload = openai_tts_request(payload, RUNTIME.serves_voice)
    try:
        response = audio_response(tts_payload, "/v1/audio/speech")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OpenAI-compatible speech generation failed")
        raise OpenAIAPIError(
            "Speech generation failed.",
            status_code=500,
            error_type="server_error",
            code="generation_failed",
        ) from exc
    response.headers["X-KokoroTTS-Model"] = OPENAI_MODEL_ID
    return response


@api.post("/tts/generate", tags=["KokoroTTS native API"])
def generate_tts(payload: TTSRequest) -> StreamingResponse:
    return audio_response(payload, "/tts/generate")


@api.post("/tts/stream", tags=["KokoroTTS native API"])
async def stream_tts(
    request: Request, payload: StreamingTTSRequest
) -> StreamingResponse:
    stream_format, device = validate_request(payload, streaming=True)
    config = STREAM_FORMATS[stream_format]
    try:
        plan = RUNTIME.prepare_synthesis(
            payload.text, payload.voice, payload.input_type
        )
    except SSMLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def disconnected_stream():
        iterator = iter(iter_stream_audio(payload, stream_format, device, plan))
        try:
            async for chunk in iterate_in_threadpool(iterator):
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            close = getattr(iterator, "close", None)
            if close is not None:
                close()

    headers = {
        "Content-Disposition": f"attachment; filename=kokorotts_{payload.voice}_stream.{config['extension']}",
        "X-KokoroTTS-Voice": payload.voice,
        "X-KokoroTTS-Language": voice_language(payload.voice),
        "X-KokoroTTS-Sample-Rate": str(SAMPLE_RATE),
        "X-KokoroTTS-Stream-Format": stream_format,
    }
    if payload.input_type != "text":
        headers["X-KokoroTTS-Input-Type"] = payload.input_type
    return StreamingResponse(
        disconnected_stream(),
        media_type=config["media_type"].format(sample_rate=SAMPLE_RATE),
        headers=headers,
    )


@api.post("/system/models/purge", tags=["System"])
@api.post("/tts/purge", tags=["KokoroTTS native API"], deprecated=True)
def purge_models(payload: PurgeRequest | None = None) -> dict:
    requested_device = payload.device if payload else None
    if requested_device:
        try:
            requested_device = normalize_device(requested_device)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    purged, remaining = RUNTIME.purge(requested_device)
    return {"purged": purged, "remaining_model_devices": remaining}


@api.post("/tts/convert", tags=["KokoroTTS native API"], deprecated=True)
def convert(payload: TTSRequest) -> StreamingResponse:
    return audio_response(payload, "/tts/convert")
