"""Audio post-processing and response encoding."""

import io
import subprocess
import wave

import numpy as np

SAMPLE_RATE = 24000

OUTPUT_FORMATS = {
    "wav": {
        "label": "WAV",
        "extension": "wav",
        "media_type": "audio/wav",
        "ffmpeg_args": None,
    },
    "mp3": {
        "label": "MP3",
        "extension": "mp3",
        "media_type": "audio/mpeg",
        "ffmpeg_args": ["-f", "mp3", "-codec:a", "libmp3lame", "-b:a", "192k"],
    },
    "flac": {
        "label": "FLAC",
        "extension": "flac",
        "media_type": "audio/flac",
        "ffmpeg_args": ["-f", "flac", "-codec:a", "flac"],
    },
    "ogg": {
        "label": "OGG Vorbis",
        "extension": "ogg",
        "media_type": "audio/ogg",
        "ffmpeg_args": ["-f", "ogg", "-codec:a", "libvorbis", "-q:a", "5"],
    },
    "opus": {
        "label": "Opus",
        "extension": "opus",
        "media_type": "audio/ogg",
        "ffmpeg_args": ["-f", "opus", "-codec:a", "libopus", "-b:a", "96k"],
    },
    "aac": {
        "label": "AAC",
        "extension": "aac",
        "media_type": "audio/aac",
        "ffmpeg_args": ["-f", "adts", "-codec:a", "aac", "-b:a", "192k"],
    },
    "pcm": {
        "label": "Raw PCM 16-bit little-endian",
        "extension": "pcm",
        "media_type": "audio/pcm",
        "ffmpeg_args": None,
        "browser_playback": False,
    },
}

FORMAT_ALIASES = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".ogg": "ogg",
    ".opus": "opus",
    ".aac": "aac",
    ".pcm": "pcm",
    "mpeg": "mp3",
    "vorbis": "ogg",
    "pcm_s16le": "pcm",
    "s16le": "pcm",
    "raw": "pcm",
}

STREAM_FORMATS = {
    "pcm_s16le": {
        "label": "Raw PCM 16-bit little-endian",
        "extension": "pcm",
        "media_type": "audio/pcm;rate={sample_rate};channels=1;encoding=signed-integer;bits=16",
    },
    "mp3": {
        "label": "MP3 sentence chunks",
        "extension": "mp3",
        "media_type": "audio/mpeg",
    },
}

STREAM_FORMAT_ALIASES = {
    "pcm": "pcm_s16le",
    "s16le": "pcm_s16le",
    "raw": "pcm_s16le",
    ".pcm": "pcm_s16le",
    ".mp3": "mp3",
    "mpeg": "mp3",
}


def normalize_output_format(output_format: str | None) -> str:
    normalized = (output_format or "wav").strip().lower()
    normalized = FORMAT_ALIASES.get(normalized, normalized)
    if normalized not in OUTPUT_FORMATS:
        supported = ", ".join(OUTPUT_FORMATS)
        raise ValueError(
            f"Unsupported output format '{output_format}'. Supported formats: {supported}"
        )
    return normalized


def normalize_stream_format(stream_format: str | None) -> str:
    normalized = (stream_format or "pcm_s16le").strip().lower()
    normalized = STREAM_FORMAT_ALIASES.get(normalized, normalized)
    if normalized not in STREAM_FORMATS:
        supported = ", ".join(STREAM_FORMATS)
        raise ValueError(
            f"Unsupported stream_format '{stream_format}'. Supported formats: {supported}"
        )
    return normalized


def get_supported_output_formats() -> dict[str, dict[str, str | bool]]:
    return {
        key: {
            **{name: config[name] for name in ("label", "extension", "media_type")},
            "browser_playback": config.get("browser_playback", True),
        }
        for key, config in OUTPUT_FORMATS.items()
    }


def audio_effects_enabled(
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> bool:
    return (
        abs(pitch_semitones) > 0.001
        or abs(tempo - 1.0) > 0.001
        or abs(volume - 1.0) > 0.001
        or normalize
    )


def atempo_filters(multiplier: float) -> list[str]:
    filters = []
    current = multiplier
    while current > 2.0:
        filters.append("atempo=2.0")
        current /= 2.0
    while current < 0.5:
        filters.append("atempo=0.5")
        current /= 0.5
    filters.append(f"atempo={current:.6f}")
    return filters


def build_audio_effect_filters(
    sample_rate: int,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> list[str]:
    filters = []
    if abs(pitch_semitones) > 0.001:
        pitch_factor = 2 ** (pitch_semitones / 12)
        shifted_rate = max(1, round(sample_rate * pitch_factor))
        filters.extend([f"asetrate={shifted_rate}", f"aresample={sample_rate}"])
        filters.extend(atempo_filters(1 / pitch_factor))
    if abs(tempo - 1.0) > 0.001:
        filters.extend(atempo_filters(tempo))
    if abs(volume - 1.0) > 0.001:
        filters.append(f"volume={volume:.6f}")
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    return filters


def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    audio_int16 = to_int16_audio(audio)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    return buffer.getvalue()


def _run_ffmpeg(command: list[str], input_bytes: bytes, action: str) -> bytes:
    try:
        result = subprocess.run(
            command,
            input=input_bytes,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"ffmpeg is required to {action}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to {action}: {stderr}") from exc
    return result.stdout


def apply_audio_effects(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> np.ndarray:
    if (
        not audio_effects_enabled(pitch_semitones, tempo, volume, normalize)
        or audio.size == 0
    ):
        return audio
    filters = build_audio_effect_filters(
        sample_rate, pitch_semitones, tempo, volume, normalize
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        "-af",
        ",".join(filters),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "pipe:1",
    ]
    output = _run_ffmpeg(
        command, audio_to_wav_bytes(audio, sample_rate), "apply audio controls"
    )
    return np.frombuffer(output, dtype="<i2").astype(np.int16, copy=True)


def encode_audio_bytes(
    audio: np.ndarray, output_format: str = "wav", sample_rate: int = SAMPLE_RATE
) -> bytes:
    normalized_format = normalize_output_format(output_format)
    if normalized_format == "pcm":
        return encode_pcm_s16le(audio)
    wav_bytes = audio_to_wav_bytes(audio, sample_rate)
    ffmpeg_args = OUTPUT_FORMATS[normalized_format]["ffmpeg_args"]
    if ffmpeg_args is None:
        return wav_bytes
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        *ffmpeg_args,
        "pipe:1",
    ]
    return _run_ffmpeg(command, wav_bytes, f"encode {normalized_format}")


def encode_pcm_s16le(audio: np.ndarray) -> bytes:
    return to_int16_audio(audio).astype("<i2", copy=False).tobytes()


def to_int16_audio(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.int16:
        return audio
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
