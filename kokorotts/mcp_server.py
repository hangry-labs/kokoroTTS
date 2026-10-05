"""Opt-in Streamable HTTP MCP tools for the running KokoroTTS deployment."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import time
from contextlib import asynccontextmanager, suppress
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from . import __version__
from .api import (
    APP_VERSION,
    BUILD_DATE,
    BUILD_ID,
    RUNTIME,
    VCS_REF,
    deployment_settings_payload,
    get_runtime_label,
    status,
    synthesize_payload,
)
from .artifacts import (
    ArtifactExpiredError,
    ArtifactNotFoundError,
    ArtifactStore,
    MAX_ARTIFACT_TTL_SECONDS,
    MIN_ARTIFACT_TTL_SECONDS,
)
from .audio import OUTPUT_FORMATS, encode_audio_bytes
from .catalog import (
    model_family_inventory,
    voice_ids,
    voice_inventory,
    voice_language,
    voice_model_family,
    voices_for_model_families,
)
from .schemas import TTSRequest
from .standalone_ui.gpu import GPU_MONITOR


DEFAULT_ALLOWED_HOSTS = [
    "127.0.0.1",
    "127.0.0.1:*",
    "localhost",
    "localhost:*",
    "[::1]",
    "[::1]:*",
    "host.docker.internal",
    "host.docker.internal:*",
]
DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1",
    "http://127.0.0.1:*",
    "http://localhost",
    "http://localhost:*",
    "https://127.0.0.1",
    "https://127.0.0.1:*",
    "https://localhost",
    "https://localhost:*",
]
ARTIFACT_CLEANUP_INTERVAL_SECONDS = 60
MODEL_PACK_FIELDS = (
    ("standard_multilingual_enabled", "kokoro-v1.0"),
    ("german_martin_enabled", "kikiri-german-martin"),
    ("german_victoria_enabled", "kikiri-german-victoria"),
    ("vietnamese_enabled", "contextboxai-kokoro-vietnamese"),
    ("chinese_v11_enabled", "kokoro-v1.1-zh"),
)
VOICE_GROUPS = {
    1: {
        "name": "Standard multilingual",
        "model_pack_ids": ["kokoro-v1.0"],
        "languages": [
            "American English",
            "British English",
            "Japanese",
            "Mandarin Chinese",
            "Spanish",
            "French",
            "Hindi",
            "Italian",
            "Brazilian Portuguese",
        ],
    },
    2: {
        "name": "German Martin",
        "model_pack_ids": ["kikiri-german-martin"],
        "languages": ["German"],
    },
    3: {
        "name": "German Victoria",
        "model_pack_ids": ["kikiri-german-victoria"],
        "languages": ["German"],
    },
    4: {
        "name": "Vietnamese",
        "model_pack_ids": ["contextboxai-kokoro-vietnamese"],
        "languages": ["Vietnamese"],
    },
    5: {
        "name": "Chinese v1.1 plus English voices",
        "model_pack_ids": ["kokoro-v1.1-zh"],
        "languages": ["Mandarin Chinese", "American English", "British English"],
    },
}
SIMPLE_VOICES = {
    1: {"voice": "af_heart", "language": "American English", "name": "Heart"},
    2: {"voice": "bf_emma", "language": "British English", "name": "Emma"},
    3: {"voice": "jf_alpha", "language": "Japanese", "name": "Alpha"},
    4: {"voice": "zf_001", "language": "Mandarin Chinese", "name": "v1.1 Speaker 001"},
    5: {"voice": "ef_dora", "language": "Spanish", "name": "Dora"},
    6: {"voice": "ff_siwis", "language": "French", "name": "Siwis"},
    7: {"voice": "hf_alpha", "language": "Hindi", "name": "Alpha"},
    8: {"voice": "if_sara", "language": "Italian", "name": "Sara"},
    9: {"voice": "pf_dora", "language": "Brazilian Portuguese", "name": "Dora"},
    10: {"voice": "dm_martin", "language": "German", "name": "Martin"},
    11: {"voice": "diem_trinh", "language": "Vietnamese", "name": "Diem Trinh"},
}


class MCPAccessGate:
    """Keep the protocol endpoint unavailable until the operator opts in."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") == "http" and not RUNTIME.settings.mcp_enabled(
            default=_enabled("KOKOROTTS_ENABLE_MCP", False)
        ):
            response = JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "message": (
                            "MCP access is disabled. Enable MCP connectivity in the "
                            "KokoroTTS System tab, then reconnect and retry."
                        ),
                        "type": "mcp_access_forbidden",
                    }
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


class GeneratedSpeechLink(BaseModel):
    download_url: str
    expires_at: str
    ttl_seconds: int
    format: str
    mime_type: str
    size_bytes: int
    duration_seconds: float
    sample_rate: int
    voice: str
    language: str
    voices: list[str]
    languages: list[str]
    inference_devices: list[str]
    fallback_reason: str | None


def _enabled(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _csv_setting(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def _download_base_url() -> str:
    configured = os.getenv("KOKOROTTS_MCP_BASE_URL", "").strip()
    base_url = configured or f"http://localhost:{os.getenv('PORT', '7860')}"
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "KOKOROTTS_MCP_BASE_URL must be an absolute http:// or https:// URL "
            "that MCP clients and downstream services can reach."
        )
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise RuntimeError(
            "KOKOROTTS_MCP_BASE_URL must not contain credentials, a path, a query, "
            "or a fragment."
        )
    return base_url.rstrip("/")


def _allowed_hosts(base_url: str) -> list[str]:
    configured = _csv_setting("KOKOROTTS_MCP_ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS)
    public_host = urlsplit(base_url).netloc
    return list(dict.fromkeys([*configured, public_host]))


def _tool_error(exc: Exception, action: str) -> ToolError:
    if isinstance(exc, HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    else:
        detail = str(exc) or exc.__class__.__name__
    return ToolError(f"{detail} {action}")


def _pack_state() -> list[dict[str, Any]]:
    enabled = set(RUNTIME.served_model_families)
    loaded: dict[str, list[str]] = {}
    for item in RUNTIME.loaded_models:
        loaded.setdefault(item["model_family"], []).append(item["device"])
    return [
        {
            **{key: value for key, value in pack.items() if key != "voices"},
            "enabled": pack["id"] in enabled,
            "loaded_devices": loaded.get(str(pack["id"]), []),
        }
        for pack in model_family_inventory()
    ]


def _pack_flags() -> dict[str, bool]:
    enabled = set(RUNTIME.served_model_families)
    return {
        field_name: model_pack_id in enabled
        for field_name, model_pack_id in MODEL_PACK_FIELDS
    }


def _voice_group_catalog() -> list[dict[str, Any]]:
    return [
        {
            "voice_group": number,
            "name": group["name"],
            "model_pack_ids": list(group["model_pack_ids"]),
            "languages": list(group["languages"]),
        }
        for number, group in VOICE_GROUPS.items()
    ]


def _simple_voice_catalog() -> list[dict[str, Any]]:
    return [
        {
            "voice_number": number,
            "voice": choice["voice"],
            "language": choice["language"],
            "name": choice["name"],
            "model_pack_id": voice_model_family(str(choice["voice"])),
        }
        for number, choice in SIMPLE_VOICES.items()
    ]


def create_mcp_server(
    *,
    artifact_store: ArtifactStore,
    base_url: str,
) -> MCPServer[Any]:
    """Build a model-readable MCP surface around the shared TTS runtime."""
    started_at = time.monotonic()
    mcp: MCPServer[Any] = MCPServer(
        "kokorotts",
        title="KokoroTTS by Hangry Labs",
        description=(
            "Private local text-to-speech generation, expiring audio links, deployment health, "
            "voice discovery, and model-pack memory controls."
        ),
        instructions=(
            "Call talk_simple directly for ordinary neutral MP3 speech; it needs only text, "
            "voice_number 1-11, and ttl_seconds, with the complete number-to-language mapping "
            "in its schema. No health or voice-discovery call is required first. Use "
            "get_available_voices only to choose an exact voice for talk_advanced: voice_group=0 "
            "lists all currently enabled voices and groups 1-5 inspect one checkpoint family. "
            "Use talk_advanced only when "
            "format, SSML, speed, pitch, tempo, volume, or normalization must be controlled. "
            "manage_model_packs requires all five Boolean package states and returns the complete "
            "resulting status. Speech tools return only a temporary HTTP link and metadata, never "
            "audio bytes or base64. ttl_seconds must be from 60 to 86400."
        ),
        website_url="https://hangrylabs.app/software/kokorotts",
        version=APP_VERSION or __version__,
    )

    read_only = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
    configuration = ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )
    generation = ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )

    @mcp.tool(
        title="Get KokoroTTS deployment health",
        description=(
            "Inspect readiness, version, runtime, enabled and loaded model packs, current GPU "
            "telemetry, supported synthesis capabilities, MCP output storage, and link TTL limits."
        ),
        annotations=read_only,
        structured_output=True,
    )
    async def get_health() -> dict[str, Any]:
        runtime_status, gpu = await asyncio.gather(
            asyncio.to_thread(status),
            asyncio.to_thread(GPU_MONITOR.request_snapshot),
        )
        return {
            "status": "ok" if RUNTIME.served_voices else "not_ready",
            "product": {
                "name": "KokoroTTS",
                "version": APP_VERSION,
                "build_id": BUILD_ID,
                "build_date": BUILD_DATE,
                "revision": VCS_REF,
                "python_version": platform.python_version(),
                "uptime_seconds": round(time.monotonic() - started_at, 3),
            },
            "runtime": runtime_status,
            "model_packs": _pack_state(),
            "gpu": list(gpu.get("gpus") or []),
            "mcp": {
                "enabled": True,
                "transport": "streamable-http",
                "endpoint": "/mcp",
                "download_base_url": base_url,
                "output_directory": str(artifact_store.directory),
                "minimum_ttl_seconds": MIN_ARTIFACT_TTL_SECONDS,
                "maximum_ttl_seconds": MAX_ARTIFACT_TTL_SECONDS,
                "returns_raw_audio": False,
            },
            "model_pack_status": _pack_flags(),
            "voice_groups": _voice_group_catalog(),
            "simple_voice_choices": _simple_voice_catalog(),
        }

    @mcp.tool(
        title="Manage model packs",
        description=(
            "Set the complete desired enabled state of all five independently loaded checkpoint "
            "packages. Every Boolean is required. Disabling packages waits for active synthesis, "
            "unloads only those checkpoints, and preserves unrelated loaded models. At least one "
            "package must remain enabled. The result confirms every current Boolean state."
        ),
        annotations=configuration,
        structured_output=True,
    )
    async def manage_model_packs(
        standard_multilingual_enabled: Annotated[
            bool,
            Field(
                description=(
                    "Enable standard Kokoro v1.0: English, Japanese, Mandarin, Spanish, French, "
                    "Hindi, Italian, and Brazilian Portuguese voices."
                )
            ),
        ],
        german_martin_enabled: Annotated[
            bool,
            Field(description="Enable the German Martin checkpoint and voice."),
        ],
        german_victoria_enabled: Annotated[
            bool,
            Field(description="Enable the German Victoria checkpoint and voice."),
        ],
        vietnamese_enabled: Annotated[
            bool,
            Field(description="Enable the Vietnamese checkpoint and its fourteen voices."),
        ],
        chinese_v11_enabled: Annotated[
            bool,
            Field(
                description=(
                    "Enable Chinese v1.1 with Mandarin voices and the Maple, Sol, and Vale "
                    "English voices."
                )
            ),
        ],
    ) -> dict[str, Any]:
        requested_flags = {
            "standard_multilingual_enabled": standard_multilingual_enabled,
            "german_martin_enabled": german_martin_enabled,
            "german_victoria_enabled": german_victoria_enabled,
            "vietnamese_enabled": vietnamese_enabled,
            "chinese_v11_enabled": chinese_v11_enabled,
        }
        selected = [
            model_pack_id
            for field_name, model_pack_id in MODEL_PACK_FIELDS
            if requested_flags[field_name]
        ]
        if not selected:
            raise ToolError(
                "At least one model package must remain enabled. Retry manage_model_packs with "
                "one or more of its five required Boolean fields set to true."
            )
        changed = selected != RUNTIME.served_model_families
        try:
            if changed:
                await asyncio.to_thread(RUNTIME.set_served_model_families, selected)
        except Exception as exc:
            raise _tool_error(
                exc,
                "Inspect get_health, preserve all five required Boolean fields, ensure newly enabled "
                "assets are reachable, and retry the desired complete package state.",
            ) from exc
        flags = _pack_flags()
        return {
            "status": "updated" if changed else "unchanged",
            "message": (
                "Model package state updated successfully."
                if changed
                else "Model package state already matched the request."
            ),
            **flags,
            "model_packs": _pack_state(),
        }

    @mcp.tool(
        title="Get available voices",
        description=(
            "Return voice choices using one required number. Use voice_group=0 for every voice in "
            "currently enabled packages; 1 for standard multilingual; 2 for German Martin; 3 for "
            "German Victoria; 4 for Vietnamese; or 5 for Chinese v1.1 plus its English voices. "
            "Specific groups remain inspectable when disabled and report their package state."
        ),
        annotations=read_only,
        structured_output=True,
    )
    async def get_available_voices(
        voice_group: Annotated[
            Literal[0, 1, 2, 3, 4, 5],
            Field(description="Required voice group number. Use 0 for all enabled voices."),
        ],
    ) -> dict[str, Any]:
        if voice_group == 0:
            family_ids = RUNTIME.served_model_families
            name = "All voices in enabled model packages"
            languages = list(
                dict.fromkeys(
                    language
                    for group in VOICE_GROUPS.values()
                    for language in group["languages"]
                )
            )
        else:
            group = VOICE_GROUPS[voice_group]
            family_ids = list(group["model_pack_ids"])
            name = str(group["name"])
            languages = list(group["languages"])
        enabled = set(RUNTIME.served_model_families)
        voices = voices_for_model_families(family_ids)
        return {
            "voice_group": voice_group,
            "group_name": name,
            "languages": languages,
            "model_packs": [
                {
                    "id": family_id,
                    "enabled": family_id in enabled,
                }
                for family_id in family_ids
            ],
            "all_selected_packs_enabled": all(
                family_id in enabled for family_id in family_ids
            ),
            "voices": voice_inventory(voices),
            "voice_groups": _voice_group_catalog(),
        }

    async def generate_link(
        *,
        text: str,
        input_type: str,
        voice: str,
        output_format: str,
        ttl_seconds: int,
        speed: float,
        pitch_semitones: float,
        tempo: float,
        volume: float,
        normalize: bool,
    ) -> GeneratedSpeechLink:
        known_voices = set(voice_ids())
        if voice not in known_voices:
            raise ToolError(
                f"Unknown voice '{voice}'. Call get_available_voices with voice_group=0 for all "
                "currently enabled voices, or use voice_group 1 through 5 for one numbered group, "
                "then retry with an exact returned voice id."
            )
        if not RUNTIME.serves_voice(voice):
            pack = voice_model_family(voice)
            desired = _pack_flags()
            field_name = next(
                field for field, model_pack_id in MODEL_PACK_FIELDS if model_pack_id == pack
            )
            desired[field_name] = True
            raise ToolError(
                f"Voice '{voice}' belongs to disabled model package '{pack}'. Call "
                f"manage_model_packs with this complete argument object, then retry speech: "
                f"{json.dumps(desired, sort_keys=True)}"
            )
        payload = TTSRequest(
            text=text,
            input_type=input_type,
            voice=voice,
            output_format=output_format,
            speed=speed,
            device="auto",
            pitch_semitones=pitch_semitones,
            tempo=tempo,
            volume=volume,
            normalize=normalize,
        )
        try:
            result = await asyncio.to_thread(synthesize_payload, payload)
            audio = await asyncio.to_thread(
                encode_audio_bytes,
                result.waveform,
                result.output_format,
                result.sample_rate,
            )
        except Exception as exc:
            raise _tool_error(
                exc,
                "Correct the text, SSML, voice, format, or control value named in the error and retry. "
                "Use get_health and get_available_voices with voice_group=0 if deployment state may "
                "have changed.",
            ) from exc

        inference = result.inference
        config = OUTPUT_FORMATS[result.output_format]
        artifact = await asyncio.to_thread(
            artifact_store.create,
            audio,
            extension=str(config["extension"]),
            ttl_seconds=ttl_seconds,
            format=result.output_format,
            mime_type=str(config["media_type"]),
            duration_seconds=(
                len(result.waveform) / result.sample_rate if result.sample_rate else 0
            ),
            sample_rate=result.sample_rate,
            voice=voice,
            language=voice_language(voice),
            voices=list(inference.voices) if inference else [voice],
            languages=(
                list(inference.languages) if inference else [voice_language(voice)]
            ),
            inference_devices=(
                list(inference.inference_devices) if inference else []
            ),
            fallback_reason=inference.fallback_reason if inference else None,
        )
        metadata = artifact.public_metadata(
            f"{base_url}/tts/artifacts/{artifact.token}"
        )
        return GeneratedSpeechLink.model_validate(metadata)

    @mcp.tool(
        title="Talk with simple neutral MP3 settings",
        description=(
            "Generate ordinary plain-text speech using neutral controls and MP3 output without a "
            "discovery call. Requires only text, one stable voice_number, and a link TTL. Voice "
            "numbers: 1 American English Heart; 2 British English Emma; 3 Japanese Alpha; 4 "
            "Mandarin Chinese v1.1 Speaker 001; 5 Spanish Dora; 6 French Siwis; 7 Hindi Alpha; "
            "8 Italian Sara; 9 Brazilian Portuguese Dora; 10 German Martin; 11 Vietnamese Diem "
            "Trinh. Returns an expiring HTTP link plus metadata; it never returns raw audio or "
            "base64. Prefer this tool unless an exact different voice, custom controls, SSML, or "
            "another format is specifically requested."
        ),
        annotations=generation,
        structured_output=True,
    )
    async def talk_simple(
        text: Annotated[
            str,
            Field(min_length=1, max_length=50_000, description="Plain text to speak."),
        ],
        voice_number: Annotated[
            Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            Field(
                description=(
                    "Required default voice: 1 American English; 2 British English; 3 Japanese; "
                    "4 Mandarin Chinese; 5 Spanish; 6 French; 7 Hindi; 8 Italian; 9 Brazilian "
                    "Portuguese; 10 German; 11 Vietnamese."
                )
            ),
        ],
        ttl_seconds: Annotated[
            int,
            Field(
                ge=MIN_ARTIFACT_TTL_SECONDS,
                le=MAX_ARTIFACT_TTL_SECONDS,
                description="Required link lifetime in seconds, from 60 through 86400.",
            ),
        ],
    ) -> GeneratedSpeechLink:
        voice = str(SIMPLE_VOICES[voice_number]["voice"])
        return await generate_link(
            text=text,
            input_type="text",
            voice=voice,
            output_format="mp3",
            ttl_seconds=ttl_seconds,
            speed=1,
            pitch_semitones=0,
            tempo=1,
            volume=1,
            normalize=False,
        )

    @mcp.tool(
        title="Talk with advanced speech controls",
        description=(
            "Generate complete speech with explicit input type, output format, and controls. Every "
            "argument is required. Returns an expiring HTTP link plus metadata; it never returns "
            "raw audio or base64. Use talk_simple instead for neutral plain-text MP3 speech."
        ),
        annotations=generation,
        structured_output=True,
    )
    async def talk_advanced(
        text: Annotated[
            str,
            Field(
                min_length=1,
                max_length=50_000,
                description="Plain text or a complete supported SSML document.",
            ),
        ],
        input_type: Annotated[
            Literal["text", "ssml"],
            Field(description="Use text for ordinary input or ssml for explicit SSML."),
        ],
        voice: Annotated[
            str,
            Field(description="Exact enabled Kokoro voice id."),
        ],
        output_format: Annotated[
            Literal["mp3", "wav", "flac", "ogg", "opus", "aac", "pcm"],
            Field(description="Generated file format."),
        ],
        ttl_seconds: Annotated[
            int,
            Field(
                ge=MIN_ARTIFACT_TTL_SECONDS,
                le=MAX_ARTIFACT_TTL_SECONDS,
                description="Required link lifetime in seconds, from 60 through 86400.",
            ),
        ],
        speed: Annotated[
            float,
            Field(ge=0.5, le=2.0, description="Speech speed. Use 1 for neutral."),
        ],
        pitch_semitones: Annotated[
            float,
            Field(ge=-12, le=12, description="Pitch shift. Use 0 for neutral."),
        ],
        tempo: Annotated[
            float,
            Field(ge=0.5, le=2.0, description="Post-processing tempo. Use 1 for neutral."),
        ],
        volume: Annotated[
            float,
            Field(ge=0, le=2.0, description="Output gain. Use 1 for neutral."),
        ],
        normalize: Annotated[
            bool,
            Field(description="Whether to apply complete-file loudness normalization."),
        ],
    ) -> GeneratedSpeechLink:
        return await generate_link(
            text=text,
            input_type=input_type,
            voice=voice,
            output_format=output_format,
            ttl_seconds=ttl_seconds,
            speed=speed,
            pitch_semitones=pitch_semitones,
            tempo=tempo,
            volume=volume,
            normalize=normalize,
        )

    return mcp


def attach_mcp(*, api_app: FastAPI, artifact_store: ArtifactStore | None = None) -> FastAPI:
    """Mount opt-in stateless Streamable HTTP MCP and expiring downloads."""
    store = artifact_store or ArtifactStore()
    base_url = _download_base_url()
    mcp = create_mcp_server(artifact_store=store, base_url=base_url)

    async def download_artifact(token: str) -> FileResponse:
        try:
            artifact, path = await asyncio.to_thread(store.resolve, token)
        except ArtifactExpiredError as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from exc
        except ArtifactNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(
            path,
            media_type=artifact.mime_type,
            filename=artifact.filename,
            headers={
                "Cache-Control": "private, no-store",
                "X-KokoroTTS-Artifact-Expires": datetime_iso(artifact.expires_at),
            },
        )

    api_app.add_api_route(
        "/tts/artifacts/{token}",
        download_artifact,
        methods=["GET", "HEAD"],
        include_in_schema=False,
        name="mcp-generated-audio",
    )

    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=_enabled(
            "KOKOROTTS_MCP_DNS_REBINDING_PROTECTION"
        ),
        allowed_hosts=_allowed_hosts(base_url),
        allowed_origins=_csv_setting(
            "KOKOROTTS_MCP_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS
        ),
    )
    mcp_app = mcp.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        max_request_body_size=4 * 1024 * 1024,
        transport_security=transport_security,
    )
    original_lifespan = api_app.router.lifespan_context

    async def cleanup_expired() -> None:
        while True:
            await asyncio.sleep(ARTIFACT_CLEANUP_INTERVAL_SECONDS)
            await asyncio.to_thread(store.cleanup_expired)

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        await asyncio.to_thread(store.cleanup_expired)
        cleanup_task = asyncio.create_task(cleanup_expired())
        try:
            async with original_lifespan(app), mcp.session_manager.run():
                yield
        finally:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task

    api_app.router.lifespan_context = combined_lifespan
    api_app.mount("/mcp", MCPAccessGate(mcp_app), name="mcp")
    api_app.state.mcp_server = mcp
    api_app.state.mcp_artifact_store = store
    api_app.state.mcp_output_directory = store.directory
    api_app.state.mcp_base_url = base_url
    return api_app


def datetime_iso(timestamp: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
