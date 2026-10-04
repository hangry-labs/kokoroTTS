"""HTTP request schemas shared by KokoroTTS routes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TTSRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., min_length=1, description="Text to synthesize.")
    input_type: Literal["text", "ssml"] = Field(
        "text",
        description=(
            "Input interpretation. Experimental SSML must be selected explicitly and "
            "can route language, voice, or optional prosody per segment."
        ),
    )
    voice: str = Field(
        "af_heart",
        description=(
            "Default Kokoro voice id. See /tts/voices. Experimental SSML <voice> "
            "segments can override it with another served voice."
        ),
    )
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier.")
    device: str = Field("auto", description="auto, cpu, or cuda:N.")
    use_gpu: bool | None = Field(
        None, description="Legacy compatibility switch. Prefer device."
    )
    pitch_semitones: float = Field(
        0.0,
        ge=-12.0,
        le=12.0,
        description="Optional post-synthesis pitch shift in semitones. 0 disables pitch processing.",
    )
    tempo: float = Field(
        1.0,
        ge=0.5,
        le=2.0,
        description="Optional post-synthesis tempo multiplier. 1 disables tempo processing.",
    )
    volume: float = Field(
        1.0,
        ge=0.0,
        le=2.0,
        description="Optional output volume multiplier. 1 disables volume processing.",
    )
    normalize: bool = Field(
        False, description="Apply ffmpeg loudness normalization after synthesis."
    )
    output_format: str = Field(
        "wav",
        alias="format",
        description=(
            "Response audio format. Defaults to wav for backward compatibility. "
            "Supported: wav, mp3, flac, ogg."
        ),
    )


class StreamingTTSRequest(TTSRequest):
    stream_format: str = Field(
        "pcm_s16le",
        description="Streaming response format. Supported: pcm_s16le, mp3.",
    )


class OpenAISpeechRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(..., min_length=1, description="OpenAI-compatible model id.")
    input: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str | dict[str, str] = Field(
        ..., description="Kokoro voice id or a supported exact-name alias."
    )
    response_format: str = Field(
        "mp3", description="Supported: mp3, opus, aac, flac, wav, pcm."
    )
    speed: float = Field(1.0, ge=0.25, le=4.0)
    instructions: str | None = Field(
        None, description="Reserved for OpenAI compatibility; not supported by Kokoro."
    )
    stream_format: str = Field(
        "audio", description="Only the OpenAI audio stream format is supported."
    )


class MetricsRequest(BaseModel):
    text: str = Field("", description="Text to inspect.")
    input_type: Literal["text", "ssml"] = Field(
        "text", description="Input interpretation used for token inspection."
    )
    voice: str = Field(
        "af_heart", description="Kokoro voice id used for language-aware tokenization."
    )


class PurgeRequest(BaseModel):
    device: str | None = Field(
        None,
        description="Optional cached model device to clear. Omit to clear all cached models.",
    )


class ServedVoicesRequest(BaseModel):
    voices: list[str] = Field(
        ..., description="Complete list of voice ids this deployment should serve."
    )


class ServedModelFamiliesRequest(BaseModel):
    model_families: list[str] = Field(
        ...,
        description="Complete list of independently loaded model families this deployment should serve.",
    )
