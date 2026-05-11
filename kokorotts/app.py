import io
import os
import subprocess
import tempfile
import wave
from typing import Optional

import gradio as gr
import numpy as np
import torch
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from kokorotts import __version__ as KOKORO_VERSION
from kokorotts import KModel, KPipeline
from kokorotts.sample_texts import (
    get_initial_text,
    get_language_group_for_voice,
    get_random_quote,
    refresh_text_for_language_change,
)
from kokorotts.voices import LANGUAGE_CHOICES, VOICE_CHOICES

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
}
FORMAT_ALIASES = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".ogg": "ogg",
    "mpeg": "mp3",
    "vorbis": "ogg",
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
DEFAULT_REPO_ID = os.getenv("KOKORO_REPO_ID", "hexgrad/Kokoro-82M")
APP_VERSION = os.getenv("APP_VERSION", KOKORO_VERSION)
BUILD_ID = os.getenv("BUILD_ID", "stable")
DEFAULT_DEVICE = os.getenv("KOKOROTTS_DEVICE", "auto")
MODEL_CACHE = {}
pipelines = {
    lang_code: KPipeline(lang_code=lang_code, repo_id=DEFAULT_REPO_ID, model=False)
    for lang_code in LANGUAGE_CHOICES
}
pipelines["a"].g2p.lexicon.golds["kokoro"] = "kˈOkəɹO"
pipelines["b"].g2p.lexicon.golds["kokoro"] = "kˈQkəɹQ"


def get_cuda_devices() -> list[str]:
    if not torch.cuda.is_available():
        return []
    return [torch.cuda.get_device_name(idx) for idx in range(torch.cuda.device_count())]


def get_runtime_label() -> str:
    cuda_devices = get_cuda_devices()
    if cuda_devices:
        visible = os.getenv("CUDA_VISIBLE_DEVICES", "all")
        device_list = ", ".join(f"{idx}:{name}" for idx, name in enumerate(cuda_devices))
        return f"GPU x{len(cuda_devices)} (visible={visible}) [{device_list}]"
    return "CPU"


def get_hardware_choices():
    choices = [("Auto", "auto"), ("CPU 🐌", "cpu")]
    for idx, name in enumerate(get_cuda_devices()):
        choices.append((f"GPU {idx} 🚀 ({name})", f"cuda:{idx}"))
    return choices


def normalize_device(hardware: str) -> str:
    hardware = (hardware or "auto").strip().lower()
    if hardware == "auto":
        return "cuda:0" if get_cuda_devices() else "cpu"
    if hardware == "gpu" or hardware == "cuda":
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
            raise RuntimeError(f"Unsupported device '{hardware}'. Use auto, cpu, or cuda:N.") from exc
        if device_index < 0 or device_index >= len(cuda_devices):
            raise RuntimeError(
                f"CUDA device index {device_index} is not available. "
                f"Visible CUDA devices: 0-{len(cuda_devices) - 1}."
            )
        return f"cuda:{device_index}"
    raise RuntimeError(f"Unsupported device '{hardware}'. Use auto, cpu, or cuda:N.")


def get_model(device: str) -> KModel:
    if device not in MODEL_CACHE:
        MODEL_CACHE[device] = KModel(repo_id=DEFAULT_REPO_ID).to(device).eval()
    return MODEL_CACHE[device]


def synthesize_full(text, voice="af_heart", speed=1, hardware="auto", use_gpu: Optional[bool] = None):
    pipeline = pipelines[voice[0]]
    pack = pipeline.load_voice(voice)
    if use_gpu is not None:
        hardware = "auto" if use_gpu else "cpu"
    resolved_device = normalize_device(hardware)
    model = get_model(resolved_device)
    audio_chunks = []
    phoneme_chunks = []

    for _, ps, _ in pipeline(text, voice, speed):
        ref_s = pack[len(ps) - 1]
        try:
            audio = model(ps, ref_s, speed)
        except gr.exceptions.Error as exc:
            if resolved_device.startswith("cuda"):
                gr.Warning(str(exc))
                gr.Info("Retrying with CPU. To avoid this error, change Hardware to CPU.")
                audio = get_model("cpu")(ps, ref_s, speed)
            else:
                raise gr.Error(exc)
        audio_chunks.append(audio.numpy())
        phoneme_chunks.append(ps)

    if not audio_chunks:
        return None, ""

    merged_audio = to_int16_audio(np.concatenate(audio_chunks))
    merged_ps = "\n".join(phoneme_chunks)
    return (SAMPLE_RATE, merged_audio), merged_ps


def generate_first(text, voice="af_heart", speed=1, hardware="auto", use_gpu: Optional[bool] = None):
    pipeline = pipelines[voice[0]]
    pack = pipeline.load_voice(voice)
    if use_gpu is not None:
        hardware = "auto" if use_gpu else "cpu"
    resolved_device = normalize_device(hardware)
    model = get_model(resolved_device)
    for _, ps, _ in pipeline(text, voice, speed):
        ref_s = pack[len(ps) - 1]
        try:
            audio = model(ps, ref_s, speed)
        except gr.exceptions.Error as exc:
            if resolved_device.startswith("cuda"):
                gr.Warning(str(exc))
                gr.Info("Retrying with CPU. To avoid this error, set Hardware to CPU.")
                audio = get_model("cpu")(ps, ref_s, speed)
            else:
                raise gr.Error(exc)
        return (SAMPLE_RATE, to_int16_audio(audio.numpy())), ps
    return None, ""


def tokenize_first(text, voice="af_heart"):
    pipeline = pipelines[voice[0]]
    for _, ps, _ in pipeline(text, voice):
        return ps
    return ""


def predict(text, voice="af_heart", speed=1):
    return generate_first(text, voice, speed, use_gpu=False)[0]


def generate_all(
    text,
    voice="af_heart",
    speed=1,
    hardware="auto",
    pitch_semitones=0,
    tempo=1,
    volume=1,
    normalize=False,
    use_gpu: Optional[bool] = None,
):
    pipeline = pipelines[voice[0]]
    pack = pipeline.load_voice(voice)
    if use_gpu is not None:
        hardware = "auto" if use_gpu else "cpu"
    resolved_device = normalize_device(hardware)
    model = get_model(resolved_device)
    first = True
    for _, ps, _ in pipeline(text, voice, speed):
        ref_s = pack[len(ps) - 1]
        try:
            audio = model(ps, ref_s, speed)
        except gr.exceptions.Error as exc:
            if resolved_device.startswith("cuda"):
                gr.Warning(str(exc))
                gr.Info("Switching to CPU")
                audio = get_model("cpu")(ps, ref_s, speed)
            else:
                raise gr.Error(exc)
        processed_audio = apply_audio_effects(
            to_int16_audio(audio.numpy()),
            SAMPLE_RATE,
            pitch_semitones,
            tempo,
            volume,
            normalize,
        )
        yield SAMPLE_RATE, processed_audio
        if first:
            first = False
            yield SAMPLE_RATE, np.zeros(1, dtype=np.int16)


def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    if audio.dtype == np.int16:
        audio_int16 = audio
    else:
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio * 32767).astype(np.int16)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    return buffer.getvalue()


def normalize_output_format(output_format: str | None) -> str:
    normalized = (output_format or "wav").strip().lower()
    normalized = FORMAT_ALIASES.get(normalized, normalized)
    if normalized not in OUTPUT_FORMATS:
        supported = ", ".join(OUTPUT_FORMATS)
        raise ValueError(f"Unsupported output format '{output_format}'. Supported formats: {supported}")
    return normalized


def normalize_stream_format(stream_format: str | None) -> str:
    normalized = (stream_format or "pcm_s16le").strip().lower()
    normalized = STREAM_FORMAT_ALIASES.get(normalized, normalized)
    if normalized not in STREAM_FORMATS:
        supported = ", ".join(STREAM_FORMATS)
        raise ValueError(f"Unsupported stream_format '{stream_format}'. Supported formats: {supported}")
    return normalized


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
        shifted_rate = max(1, int(round(sample_rate * pitch_factor)))
        filters.extend([f"asetrate={shifted_rate}", f"aresample={sample_rate}"])
        filters.extend(atempo_filters(1 / pitch_factor))
    if abs(tempo - 1.0) > 0.001:
        filters.extend(atempo_filters(tempo))
    if abs(volume - 1.0) > 0.001:
        filters.append(f"volume={volume:.6f}")
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    return filters


def apply_audio_effects(
    audio: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> np.ndarray:
    if not audio_effects_enabled(pitch_semitones, tempo, volume, normalize) or audio.size == 0:
        return audio

    filters = build_audio_effect_filters(sample_rate, pitch_semitones, tempo, volume, normalize)
    wav_bytes = audio_to_wav_bytes(audio, sample_rate)
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
    try:
        result = subprocess.run(
            command,
            input=wav_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for pitch, tempo, volume, or normalization controls") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to apply audio controls: {stderr}") from exc
    return np.frombuffer(result.stdout, dtype="<i2").astype(np.int16, copy=True)


def encode_audio_bytes(audio: np.ndarray, output_format: str = "wav", sample_rate: int = SAMPLE_RATE) -> bytes:
    normalized_format = normalize_output_format(output_format)
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
    try:
        result = subprocess.run(
            command,
            input=wav_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for non-WAV output formats") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to encode {normalized_format}: {stderr}") from exc
    return result.stdout


def encode_pcm_s16le(audio: np.ndarray) -> bytes:
    if audio.dtype == np.int16:
        return audio.astype("<i2", copy=False).tobytes()
    return (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def encoded_audio_to_temp_file(audio: np.ndarray, output_format: str = "wav", sample_rate: int = SAMPLE_RATE) -> str:
    normalized_format = normalize_output_format(output_format)
    extension = OUTPUT_FORMATS[normalized_format]["extension"]
    audio_bytes = encode_audio_bytes(audio, normalized_format, sample_rate)
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as file:
        file.write(audio_bytes)
        return file.name


def synthesize_file(
    text,
    voice="af_heart",
    speed=1,
    hardware="auto",
    output_format="wav",
    pitch_semitones=0,
    tempo=1,
    volume=1,
    normalize=False,
):
    audio_tuple, phonemes = synthesize_full(text, voice, speed, hardware)
    if audio_tuple is None:
        return None, phonemes
    sample_rate, waveform = audio_tuple
    try:
        waveform = apply_audio_effects(waveform, sample_rate, pitch_semitones, tempo, volume, normalize)
        output_file = encoded_audio_to_temp_file(waveform, output_format, sample_rate)
    except (RuntimeError, ValueError) as exc:
        raise gr.Error(str(exc)) from exc
    return output_file, phonemes


def to_int16_audio(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.int16:
        return audio
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def get_voice_language(voice_id: str) -> str:
    if not voice_id:
        return "a"
    return voice_id[0] if voice_id[0] in LANGUAGE_CHOICES else "a"


def resolve_requested_hardware(device: str, use_gpu: Optional[bool] = None) -> str:
    if use_gpu is True:
        return "auto"
    if use_gpu is False:
        return "cpu"
    return device


def get_voice_choices_for_language(language_code: str) -> list[str]:
    return [voice_id for voice_id in VOICE_CHOICES.values() if get_voice_language(voice_id) == language_code]


def get_voice_label(voice_id: str) -> str:
    for label, registered_voice in VOICE_CHOICES.items():
        if registered_voice == voice_id:
            return label
    return voice_id


def get_voice_inventory() -> list[dict[str, str]]:
    return [
        {
            "id": voice_id,
            "name": get_voice_label(voice_id),
            "language": get_voice_language(voice_id),
            "language_name": LANGUAGE_CHOICES[get_voice_language(voice_id)],
        }
        for voice_id in VOICE_CHOICES.values()
    ]


def get_supported_output_formats() -> dict[str, dict[str, str]]:
    return {
        key: {
            "label": config["label"],
            "extension": config["extension"],
            "media_type": config["media_type"],
        }
        for key, config in OUTPUT_FORMATS.items()
    }


def get_text_metrics(text: str, voice: str = "af_heart") -> dict[str, int | str]:
    pipeline = pipelines[get_voice_language(voice)]
    phoneme_segments = []
    if text.strip():
        try:
            phoneme_segments = [ps for _, ps, _ in pipeline(text, voice)]
        except Exception:
            phoneme_segments = []
    return {
        "characters": len(text or ""),
        "words": len((text or "").split()),
        "segments": len(phoneme_segments),
        "phoneme_characters": sum(len(ps) for ps in phoneme_segments),
    }


def get_status_payload() -> dict:
    return {
        "msg": "pong",
        "type": "KokoroTTS",
        "version": APP_VERSION,
        "build_id": BUILD_ID,
        "runtime": get_runtime_label(),
        "device": DEFAULT_DEVICE,
        "repo_id": DEFAULT_REPO_ID,
        "sample_rate": SAMPLE_RATE,
        "configured_languages": list(LANGUAGE_CHOICES),
        "languages": LANGUAGE_CHOICES,
        "voices": len(VOICE_CHOICES),
        "loaded_model_devices": list(MODEL_CACHE),
        "output_formats": get_supported_output_formats(),
        "stream_formats": STREAM_FORMATS,
    }


for voice_id in VOICE_CHOICES.values():
    pipelines[voice_id[0]].load_voice(voice_id)

TOKEN_NOTE = """
💡 Customize pronunciation with Markdown link syntax and /slashes/ like `[Kokoro](/kˈOkəɹO/)`

💬 To adjust intonation, try punctuation `;:,.!?—…"()“”` or stress `ˈ` and `ˌ`

⬇️ Lower stress `[1 level](-1)` or `[2 levels](-2)`

⬆️ Raise stress 1 level `[or](+2)` 2 levels (only works on less stressed, usually short words)
"""

with gr.Blocks() as generate_tab:
    out_audio = gr.Audio(label="Output Audio", interactive=False, streaming=False, autoplay=True)
    generate_btn = gr.Button("Generate", variant="primary")
    with gr.Accordion("Output Tokens", open=True):
        out_ps = gr.Textbox(
            interactive=False,
            show_label=False,
            info="Tokens used to generate the audio, up to 510 context length.",
        )
        tokenize_btn = gr.Button("Tokenize", variant="secondary")
        gr.Markdown(TOKEN_NOTE)
        predict_btn = gr.Button("Predict", variant="secondary", visible=False)

with gr.Blocks() as stream_tab:
    out_stream = gr.Audio(label="Output Audio Stream", interactive=False, streaming=True, autoplay=True)
    with gr.Row():
        stream_btn = gr.Button("Stream", variant="primary")
        stop_btn = gr.Button("Stop", variant="stop")
    gr.DuplicateButton()

BADGE_CSS = """
#build-badge {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.45);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 12px;
    font-family: Arial, sans-serif;
    backdrop-filter: blur(2px);
}
"""

hardware_choices = get_hardware_choices()
hardware_values = {value for _, value in hardware_choices}
default_hardware = DEFAULT_DEVICE if DEFAULT_DEVICE in hardware_values else "auto"

with gr.Blocks(title="KokoroTTS") as ui:
    gr.HTML(f"<style>{BADGE_CSS}</style>")
    gr.HTML(f"<div id='build-badge'>Version: {APP_VERSION} | Build: {BUILD_ID}<br>{get_runtime_label()}</div>")
    voice_language_state = gr.State(get_language_group_for_voice("af_heart"))
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(
                label="Input Text",
                info="Arbitrarily many characters supported",
                value=get_initial_text(),
            )
            with gr.Row():
                voice = gr.Dropdown(
                    choices=list(VOICE_CHOICES.items()),
                    value="af_heart",
                    label="Voice",
                    info="Quality and availability vary by language",
                    filterable=False,
                    allow_custom_value=False,
                )
                hardware = gr.Dropdown(
                    hardware_choices,
                    value=default_hardware,
                    label="Hardware",
                    info="Select Auto/CPU or a specific visible GPU",
                )
            speed = gr.Slider(minimum=0.5, maximum=2, value=1, step=0.1, label="Speed")
            with gr.Accordion("Audio Controls", open=False):
                pitch_semitones = gr.Slider(
                    minimum=-12,
                    maximum=12,
                    value=0,
                    step=0.5,
                    label="Pitch",
                    info="Semitone shift after synthesis. 0 disables pitch processing.",
                )
                tempo = gr.Slider(
                    minimum=0.5,
                    maximum=2,
                    value=1,
                    step=0.05,
                    label="Tempo",
                    info="Post-synthesis tempo multiplier. 1 disables tempo processing.",
                )
                volume = gr.Slider(
                    minimum=0,
                    maximum=2,
                    value=1,
                    step=0.05,
                    label="Volume",
                    info="Output volume multiplier. 1 disables volume processing.",
                )
                normalize = gr.Checkbox(
                    value=False,
                    label="Normalize Loudness",
                    info="Apply ffmpeg loudness normalization after synthesis.",
                )
            output_format = gr.Dropdown(
                choices=[(config["label"], key) for key, config in OUTPUT_FORMATS.items()],
                value="mp3",
                label="Output Format",
                info="WAV preserves existing API/UI behavior; other formats are encoded with ffmpeg",
            )
            random_btn = gr.Button("🎲 Random Quote 💬", variant="secondary")
        with gr.Column():
            gr.TabbedInterface([generate_tab, stream_tab], ["Generate", "Stream"])

    random_btn.click(fn=get_random_quote, inputs=[voice], outputs=[text])
    voice.change(fn=refresh_text_for_language_change, inputs=[voice, voice_language_state], outputs=[text, voice_language_state])
    generate_btn.click(
        fn=synthesize_file,
        inputs=[text, voice, speed, hardware, output_format, pitch_semitones, tempo, volume, normalize],
        outputs=[out_audio, out_ps],
    )
    tokenize_btn.click(fn=tokenize_first, inputs=[text, voice], outputs=[out_ps])
    stream_event = stream_btn.click(
        fn=generate_all,
        inputs=[text, voice, speed, hardware, pitch_semitones, tempo, volume, normalize],
        outputs=[out_stream],
    )
    stop_btn.click(fn=None, cancels=stream_event)
    predict_btn.click(fn=predict, inputs=[text, voice, speed], outputs=[out_audio])

api = FastAPI(
    title="TTS Service API",
    description="API documentation for the KokoroTTS service",
    version=KOKORO_VERSION,
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
)


class TTSRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str = Field("af_heart", description="Kokoro voice id. See /tts/voices.")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech speed multiplier.")
    device: str = Field("auto", description="auto, cpu, or cuda:N.")
    use_gpu: Optional[bool] = Field(None, description="Legacy compatibility switch. Prefer device.")
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
        False,
        description="Apply ffmpeg loudness normalization after synthesis.",
    )
    output_format: str = Field(
        "wav",
        alias="format",
        description="Response audio format. Defaults to wav for backward compatibility. Supported: wav, mp3, flac, ogg.",
    )


class StreamingTTSRequest(TTSRequest):
    stream_format: str = Field(
        "pcm_s16le",
        description="Streaming response format. Supported: pcm_s16le, mp3.",
    )


class MetricsRequest(BaseModel):
    text: str = Field("", description="Text to inspect.")
    voice: str = Field("af_heart", description="Kokoro voice id used for language-aware tokenization.")


class PurgeRequest(BaseModel):
    device: Optional[str] = Field(
        None,
        description="Optional cached model device to clear. Omit to clear all cached models.",
    )


def synthesize_payload(payload: TTSRequest) -> tuple[str, int, np.ndarray]:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")
    try:
        output_format = normalize_output_format(payload.output_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.voice not in VOICE_CHOICES.values():
        raise HTTPException(status_code=400, detail=f"Invalid voice '{payload.voice}'")
    try:
        normalize_device(resolve_requested_hardware(payload.device, payload.use_gpu))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audio_tuple, _ = synthesize_full(
        text=payload.text,
        voice=payload.voice,
        speed=payload.speed,
        hardware=payload.device,
        use_gpu=payload.use_gpu,
    )
    if audio_tuple is None:
        return output_format, SAMPLE_RATE, np.zeros(0, dtype=np.int16)
    sample_rate, waveform = audio_tuple
    try:
        waveform = apply_audio_effects(
            waveform,
            sample_rate,
            payload.pitch_semitones,
            payload.tempo,
            payload.volume,
            payload.normalize,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return output_format, sample_rate, waveform


def stream_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    output_format, sample_rate, waveform = synthesize_payload(payload)
    try:
        audio_bytes = encode_audio_bytes(waveform, output_format, sample_rate)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    extension = OUTPUT_FORMATS[output_format]["extension"]
    media_type = OUTPUT_FORMATS[output_format]["media_type"]
    duration = len(waveform) / sample_rate if sample_rate else 0
    headers = {
        "Content-Disposition": f"attachment; filename=kokorotts_{payload.voice}.{extension}",
        "X-KokoroTTS-Voice": payload.voice,
        "X-KokoroTTS-Language": get_voice_language(payload.voice),
        "X-KokoroTTS-Sample-Rate": str(sample_rate),
        "X-KokoroTTS-Duration": f"{duration:.3f}",
        "X-KokoroTTS-Route": route_name,
    }
    if output_format != "wav":
        headers["X-KokoroTTS-Format"] = output_format
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=media_type, headers=headers)


def iter_stream_audio(payload: StreamingTTSRequest, stream_format: str):
    pipeline = pipelines[get_voice_language(payload.voice)]
    pack = pipeline.load_voice(payload.voice)
    if payload.use_gpu is not None:
        hardware = "auto" if payload.use_gpu else "cpu"
    else:
        hardware = payload.device
    resolved_device = normalize_device(hardware)
    model = get_model(resolved_device)
    for _, ps, _ in pipeline(payload.text, payload.voice, payload.speed):
        ref_s = pack[len(ps) - 1]
        audio = to_int16_audio(model(ps, ref_s, payload.speed).numpy())
        audio = apply_audio_effects(
            audio,
            SAMPLE_RATE,
            payload.pitch_semitones,
            payload.tempo,
            payload.volume,
            payload.normalize,
        )
        if stream_format == "pcm_s16le":
            yield encode_pcm_s16le(audio)
        elif stream_format == "mp3":
            yield encode_audio_bytes(audio, "mp3", SAMPLE_RATE)


@api.get("/tts/ping")
def ping() -> dict:
    return {"msg": "pong", "type": "KokoroTTS", "version": APP_VERSION, "build_id": BUILD_ID}


@api.get("/tts/status")
def status() -> dict:
    return get_status_payload()


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
        "output_formats": {"default": "wav", "available": get_supported_output_formats()},
        "stream_formats": {"default": "pcm_s16le", "available": STREAM_FORMATS},
    }


@api.get("/tts/formats")
def formats() -> dict:
    return {"default": "wav", "formats": get_supported_output_formats(), "aliases": FORMAT_ALIASES}


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


@api.get("/tts/speakers")
def speakers(language: str = Query("a", description="Kokoro language prefix.")) -> dict:
    if language not in LANGUAGE_CHOICES:
        raise HTTPException(status_code=404, detail="Language not found")
    return {"language": language, "language_name": LANGUAGE_CHOICES[language], "speakers": get_voice_choices_for_language(language)}


@api.get("/tts/voices")
def voices() -> dict:
    return {"voices": get_voice_inventory()}


@api.post("/tts/metrics")
def metrics(payload: MetricsRequest = Body(...)) -> dict:
    return {"voice": payload.voice, "language": get_voice_language(payload.voice), "metrics": get_text_metrics(payload.text, payload.voice)}


@api.post("/tts/generate")
def generate_tts(payload: TTSRequest = Body(...)) -> StreamingResponse:
    return stream_audio_response(payload, "/tts/generate")


@api.post("/tts/stream")
def stream_tts(payload: StreamingTTSRequest = Body(...)) -> StreamingResponse:
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text must not be empty")
    if payload.voice not in VOICE_CHOICES.values():
        raise HTTPException(status_code=400, detail=f"Invalid voice '{payload.voice}'")
    try:
        stream_format = normalize_stream_format(payload.stream_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        normalize_device(resolve_requested_hardware(payload.device, payload.use_gpu))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    format_config = STREAM_FORMATS[stream_format]
    media_type = format_config["media_type"].format(sample_rate=SAMPLE_RATE)
    return StreamingResponse(
        iter_stream_audio(payload, stream_format),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=kokorotts_{payload.voice}_stream.{format_config['extension']}",
            "X-KokoroTTS-Voice": payload.voice,
            "X-KokoroTTS-Language": get_voice_language(payload.voice),
            "X-KokoroTTS-Sample-Rate": str(SAMPLE_RATE),
            "X-KokoroTTS-Stream-Format": stream_format,
        },
    )


@api.post("/tts/purge")
def purge_models(payload: PurgeRequest | None = Body(None)) -> dict:
    requested_device = payload.device if payload else None
    if requested_device:
        try:
            device = normalize_device(requested_device)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if device not in MODEL_CACHE:
            return {"purged": [], "remaining_model_devices": list(MODEL_CACHE)}
        del MODEL_CACHE[device]
        return {"purged": [device], "remaining_model_devices": list(MODEL_CACHE)}

    purged = list(MODEL_CACHE)
    MODEL_CACHE.clear()
    return {"purged": purged, "remaining_model_devices": []}


@api.post("/tts/convert")
def convert(payload: TTSRequest = Body(...)) -> StreamingResponse:
    return stream_audio_response(payload, "/tts/convert")



app = gr.mount_gradio_app(api, ui, path="/")


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    reload_enabled = os.getenv("UVICORN_RELOAD", "0").lower() in {"1", "true", "yes"}
    uvicorn.run("kokorotts.app:app", host=host, port=port, reload=reload_enabled)

