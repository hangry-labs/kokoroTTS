"""Bounded Magic take orchestration over Kokoro's existing runtime."""

from __future__ import annotations

import asyncio
import json
import threading
from contextlib import closing
from dataclasses import asdict
from functools import wraps

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..audio import (
    OUTPUT_FORMATS,
    SAMPLE_RATE,
    apply_audio_effects,
    compact_ssml_speech_audio,
    encode_audio_bytes,
    to_int16_audio,
)
from ..schemas import TTSRequest
from ..ssml_h import capabilities
from .magic_takes import (
    MAGIC_TAKE_MEDIA_TYPE,
    decode_pcm16_mono_wav,
    pack_magic_take_bundle,
)


class StudioRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        @wraps(original)
        async def handle(request):
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
                    raise HTTPException(
                        403,
                        detail="Cross-origin studio writes are blocked. Open the UI on this server or call the API from your application.",
                    )
            try:
                return await original(request)
            except ValidationError as exc:
                details = "; ".join(
                    f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                    for error in exc.errors(include_input=False)
                )
                raise HTTPException(400, detail=details) from exc
            except ValueError as exc:
                raise HTTPException(400, detail=str(exc)) from exc
            except FileNotFoundError as exc:
                raise HTTPException(
                    404,
                    detail="Saved script or audio not found. Refresh the script library.",
                ) from exc
            except OSError as exc:
                raise HTTPException(
                    500,
                    detail="Studio storage is unavailable. Check that the container's persistent app directory is writable and has free disk space.",
                ) from exc

        return handle


class MagicTakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: TTSRequest
    speech_index: int = Field(ge=0, strict=True)


class AssemblyItem(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    kind: str = Field(alias="type", pattern="^(speech|break)$")
    id: str = Field(default="", max_length=80)
    milliseconds: int = Field(default=0, ge=0, le=10000, strict=True)


class AssemblyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[AssemblyItem] = Field(min_length=1, max_length=200)
    output_format: str = "wav"
    normalize_loudness: bool = False


def assemble_audio(items, *, normalize=False):
    parts = []
    for index, (kind, value) in enumerate(items):
        if kind == "break":
            parts.append(np.zeros(round(value * SAMPLE_RATE / 1000), dtype=np.int16))
        else:
            parts.append(
                compact_ssml_speech_audio(
                    value,
                    trim_leading=index > 0,
                    trim_trailing=index < len(items) - 1,
                    append_implicit_pause=index < len(items) - 1
                    and items[index + 1][0] == "speech",
                )
            )
    if not parts:
        raise ValueError("Add at least one speech turn before generating.")
    if sum(len(part) for part in parts) > SAMPLE_RATE * 300:
        raise ValueError(
            "Dialogue exceeds 300 seconds. Split the script into smaller documents."
        )
    wave = np.concatenate(parts)
    return apply_audio_effects(wave, SAMPLE_RATE, normalize=True) if normalize else wave


async def uploaded_takes(files, metadata):
    if not isinstance(metadata, list) or len(metadata) != len(files) or len(files) > 64:
        raise ValueError("Supply one metadata item per uploaded take, up to 64 takes.")
    decoded, total, samples = {}, 0, 0
    for upload, item in zip(files, metadata):
        identity = item.get("id") if isinstance(item, dict) else None
        if (
            not isinstance(identity, str)
            or not identity
            or len(identity) > 80
            or identity in decoded
        ):
            raise ValueError(
                "Take ids must be unique non-empty strings up to 80 characters."
            )
        content = await upload.read(20 * 1024 * 1024 + 1)
        total += len(content)
        if len(content) > 20 * 1024 * 1024 or total > 40 * 1024 * 1024:
            raise ValueError("Take uploads exceed 20 MB per file or 40 MB total.")
        rate, wave = await asyncio.to_thread(decode_pcm16_mono_wav, content)
        if rate != SAMPLE_RATE or wave.size == 0:
            raise ValueError(
                "Magic takes must be non-empty mono PCM16 WAV at 24000 Hz."
            )
        samples += len(wave)
        if samples > SAMPLE_RATE * 300:
            raise ValueError("Uploaded takes exceed 300 seconds.")
        seed = item.get("seed", 0)
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("Take seed metadata must be an unsigned 32-bit integer.")
        decoded[identity] = (seed, wave)
    return decoded


def attach_magic(app):
    from .. import api as native

    router = APIRouter(route_class=StudioRoute, tags=["Magic studio"])

    def prepare(payload):
        if payload.input_type != "ssml-h":
            raise ValueError(
                "Magic expects input_type='ssml-h'. Export the Magic editor document or use /tts/generate for plain text and legacy SSML."
            )
        fmt, device = native.validate_request(payload)
        turns, groups = native.RUNTIME.prepare_dialogue(payload.text, payload.voice)
        native.validate_plan_prosody(
            [unit for group in groups for unit in group], payload
        )
        return fmt, device, turns, groups

    async def run(request, work):
        cancelled = threading.Event()

        async def watch():
            while not cancelled.is_set():
                if await request.is_disconnected():
                    cancelled.set()
                    return
                await asyncio.sleep(0.1)

        monitor = asyncio.create_task(watch())
        try:
            result = await asyncio.to_thread(work, cancelled)
            if cancelled.is_set():
                raise HTTPException(
                    499, "Generation cancelled. No workspace was saved."
                )
            return result
        finally:
            cancelled.set()
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)

    def check_cancel(cancelled):
        if cancelled.is_set():
            raise HTTPException(499, "Generation cancelled between synthesis chunks.")

    def speech(payload, group, cancelled, chunks):
        parts = []
        for unit in group:
            check_cancel(cancelled)
            chunk = next(chunks)
            check_cancel(cancelled)
            parts.append(
                native.apply_chunk_effects(
                    to_int16_audio(chunk.audio), chunk.prosody, payload, normalize=False
                )
            )
        return assemble_audio([("speech", part) for part in parts])

    def inference(payload, device, units):
        return native.RUNTIME.iter_synthesis(
            payload.text,
            payload.voice,
            payload.speed,
            device,
            payload.input_type,
            units,
        )

    @router.get("/tts/ssml/capabilities")
    def ssml_capabilities():
        return capabilities()

    @router.post("/tts/plan")
    def plan(payload: TTSRequest):
        if payload.input_type != "ssml-h":
            return native.tokenize(
                native.MetricsRequest(
                    text=payload.text,
                    voice=payload.voice,
                    input_type=payload.input_type,
                )
            )
        _, _, turns, groups = prepare(payload)
        return {
            "input_type": "ssml-h",
            "units": [
                {**asdict(turn), "phoneme_chunks": [asdict(unit) for unit in group]}
                for turn, group in zip(turns, groups)
            ],
            "speech_units": sum(turn.kind == "speech" for turn in turns),
        }

    @router.post("/tts/magic/take")
    async def take(payload: MagicTakeRequest, request: Request):
        _, device, turns, groups = await asyncio.to_thread(prepare, payload.payload)
        speech_groups = [
            group for turn, group in zip(turns, groups) if turn.kind == "speech"
        ]
        if payload.speech_index >= len(speech_groups):
            raise ValueError(
                "speech_index is outside this document. Use a zero-based speech turn index from /tts/plan."
            )

        def work(cancelled):
            group = speech_groups[payload.speech_index]
            with closing(inference(payload.payload, device, group)) as chunks:
                wave = speech(payload.payload, group, cancelled, chunks)
            return encode_audio_bytes(wave, "wav", SAMPLE_RATE)

        return Response(
            await run(request, work),
            media_type="audio/wav",
            headers={"X-KokoroTTS-Format": "wav", "X-KokoroTTS-Seed": "0"},
        )

    @router.post("/tts/magic/render")
    async def render(
        request: Request,
        payload: str = Form(...),
        speech_ids: str = Form(...),
        retained: str = Form("[]"),
        takes: list[UploadFile] = File(default=[]),
    ):
        config = TTSRequest.model_validate_json(payload)
        fmt, device, turns, groups = await asyncio.to_thread(prepare, config)
        ids = json.loads(speech_ids)
        count = sum(turn.kind == "speech" for turn in turns)
        if (
            not isinstance(ids, list)
            or not count
            or len(ids) != count
            or any(not isinstance(n, str) or not n or len(n) > 80 for n in ids)
            or len(set(ids)) != count
        ):
            raise ValueError(
                "speech_ids must uniquely identify every speech turn from /tts/plan."
            )
        kept = await uploaded_takes(takes, json.loads(retained))
        if set(kept) - set(ids):
            raise ValueError("Retained takes must belong to speech_ids.")

        def work(cancelled):
            timeline, generated = [], dict(kept)
            index = 0
            speech_groups = [
                group for turn, group in zip(turns, groups) if turn.kind == "speech"
            ]
            missing = [
                unit
                for identity, group in zip(ids, speech_groups)
                if identity not in kept
                for unit in group
            ]
            # One runtime generator owns leases/packs across the complete request,
            # including gaps between turns and switches across model families.
            with closing(inference(config, device, missing)) as chunks:
                for turn, group in zip(turns, groups):
                    check_cancel(cancelled)
                    if turn.kind == "break":
                        timeline.append(("break", turn.duration_ms))
                        continue
                    identity = ids[index]
                    index += 1
                    if identity not in generated:
                        generated[identity] = (
                            0,
                            speech(config, group, cancelled, chunks),
                        )
                    timeline.append(("speech", generated[identity][1]))
                    if (
                        sum(
                            len(v)
                            if kind == "speech"
                            else round(v * SAMPLE_RATE / 1000)
                            for kind, v in timeline
                        )
                        > SAMPLE_RATE * 300
                    ):
                        raise ValueError(
                            "Generated dialogue exceeds 300 seconds. Split the script."
                        )
            wave = assemble_audio(timeline, normalize=config.normalize)
            encoded = encode_audio_bytes(wave, fmt, SAMPLE_RATE)
            check_cancel(cancelled)
            return pack_magic_take_bundle(
                [
                    (
                        identity,
                        generated[identity][0],
                        encode_audio_bytes(generated[identity][1], "wav", SAMPLE_RATE),
                    )
                    for identity in ids
                ],
                encoded,
                sample_rate=SAMPLE_RATE,
                output_format=fmt,
                output_media_type=OUTPUT_FORMATS[fmt]["media_type"],
                request_seed=0,
                metrics={
                    "speech_turns": count,
                    "duration_seconds": len(wave) / SAMPLE_RATE,
                },
            )

        return Response(await run(request, work), media_type=MAGIC_TAKE_MEDIA_TYPE)

    @router.post("/tts/magic/assemble-upload")
    async def assemble(
        options: str = Form(...),
        take_metadata: str = Form(...),
        takes: list[UploadFile] = File(...),
    ):
        config = AssemblyRequest.model_validate_json(options)
        fmt = native.normalize_output_format(config.output_format)
        decoded = await uploaded_takes(takes, json.loads(take_metadata))
        ids = [item.id for item in config.items if item.kind == "speech"]
        if not ids or len(set(ids)) != len(ids) or set(ids) != set(decoded):
            raise ValueError(
                "Every speech item needs a unique matching uploaded take; unused takes are rejected."
            )
        if (
            sum(item.milliseconds for item in config.items if item.kind == "break")
            > 60000
        ):
            raise ValueError("Explicit pauses cannot exceed 60000 ms in total.")
        wave = await asyncio.to_thread(
            assemble_audio,
            [
                (
                    item.kind,
                    item.milliseconds if item.kind == "break" else decoded[item.id][1],
                )
                for item in config.items
            ],
            normalize=config.normalize_loudness,
        )
        encoded = await asyncio.to_thread(encode_audio_bytes, wave, fmt, SAMPLE_RATE)
        return Response(
            encoded,
            media_type=OUTPUT_FORMATS[fmt]["media_type"],
            headers={"X-KokoroTTS-Format": fmt},
        )

    app.include_router(router)
