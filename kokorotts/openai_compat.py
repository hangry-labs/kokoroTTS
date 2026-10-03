"""OpenAI speech API request mapping, authentication, and errors."""

from __future__ import annotations

import hmac
import os
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse

from .schemas import OpenAISpeechRequest, TTSRequest


OPENAI_MODEL_ID = "kokoro"
OPENAI_MODEL_ALIASES = {
    "kokoro": OPENAI_MODEL_ID,
    "kokoro-82m": OPENAI_MODEL_ID,
    "kokorotts": OPENAI_MODEL_ID,
    "hexgrad/kokoro-82m": OPENAI_MODEL_ID,
}
OPENAI_VOICE_ALIASES = {
    "alloy": "af_alloy",
    "echo": "am_echo",
    "fable": "bm_fable",
    "nova": "af_nova",
    "onyx": "am_onyx",
}
OPENAI_RESPONSE_FORMATS = {"mp3", "opus", "aac", "flac", "wav", "pcm"}


class OpenAIAPIError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        error_type: str = "invalid_request_error",
        param: str | None = None,
        code: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.param = param
        self.code = code
        self.headers = headers or {}


def openai_error_response(
    message: str,
    *,
    status_code: int = 400,
    error_type: str = "invalid_request_error",
    param: str | None = None,
    code: str | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": param,
                "code": code,
            }
        },
        headers=headers,
    )


def require_openai_api_key(request: Request) -> None:
    configured_key = os.getenv("KOKOROTTS_API_KEY", "").strip()
    if not configured_key:
        return
    authorization = request.headers.get("authorization", "")
    scheme, _, provided_key = authorization.partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        provided_key, configured_key
    ):
        raise OpenAIAPIError(
            "Incorrect API key provided.",
            status_code=401,
            error_type="authentication_error",
            code="invalid_api_key",
            headers={"WWW-Authenticate": "Bearer"},
        )


def resolve_openai_model(model: str) -> str:
    normalized = model.strip().lower()
    resolved = OPENAI_MODEL_ALIASES.get(normalized)
    if resolved is None:
        raise OpenAIAPIError(
            f"The model '{model}' does not exist.",
            param="model",
            code="model_not_found",
        )
    return resolved


def resolve_openai_voice(
    voice: str | dict[str, str], serves_voice: Callable[[str], bool]
) -> str:
    if not isinstance(voice, str):
        raise OpenAIAPIError(
            "Custom voice objects are not supported; use a Kokoro voice id.",
            param="voice",
            code="unsupported_voice",
        )
    requested_voice = voice.strip()
    resolved = OPENAI_VOICE_ALIASES.get(requested_voice.lower(), requested_voice)
    if not serves_voice(resolved):
        raise OpenAIAPIError(
            f"Voice '{voice}' is not served by this deployment.",
            param="voice",
            code="unsupported_voice",
        )
    return resolved


def openai_speed_controls(speed: float) -> tuple[float, float]:
    model_speed = min(2.0, max(0.5, speed))
    return model_speed, speed / model_speed


def openai_tts_request(
    payload: OpenAISpeechRequest, serves_voice: Callable[[str], bool]
) -> TTSRequest:
    resolve_openai_model(payload.model)
    voice = resolve_openai_voice(payload.voice, serves_voice)
    response_format = payload.response_format.strip().lower()
    if response_format not in OPENAI_RESPONSE_FORMATS:
        supported = ", ".join(sorted(OPENAI_RESPONSE_FORMATS))
        raise OpenAIAPIError(
            f"Unsupported response_format '{payload.response_format}'. Supported formats: {supported}",
            param="response_format",
            code="unsupported_format",
        )
    if payload.instructions and payload.instructions.strip():
        raise OpenAIAPIError(
            "The instructions parameter is not supported by the Kokoro model.",
            param="instructions",
            code="unsupported_parameter",
        )
    if payload.stream_format.strip().lower() != "audio":
        raise OpenAIAPIError(
            "Only stream_format='audio' is supported. SSE speech events are not implemented.",
            param="stream_format",
            code="unsupported_parameter",
        )
    model_speed, tempo = openai_speed_controls(payload.speed)
    return TTSRequest(
        text=payload.input,
        voice=voice,
        speed=model_speed,
        tempo=tempo,
        output_format=response_format,
    )
