"""Persistent dialogue scripts and explicit audio workspace snapshots.

Storage and API contracts adapted from Hangry Labs VoxCPMTTS (Apache-2.0).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from ..audio import SAMPLE_RATE, encode_audio_bytes
from ..ssml_h import parse_dialogue
from . import dialogue_scripts as storage
from .magic_api import StudioRoute


class ScriptRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=80)
    document: str = Field(min_length=1, max_length=50000)
    description: str = Field(default="", max_length=240)
    tags: list[str] = Field(default_factory=list, max_length=12)
    folder: str = Field(default="", max_length=80)


class FolderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class FolderAssignment(BaseModel):
    folder: str = Field(default="", max_length=80)


def attach_scripts(app, root: Path):
    router = APIRouter(route_class=StudioRoute, tags=["Dialogue library"])

    def payload(name, record, full=False):
        loaded = storage.load_dialogue_workspace(root, record)
        manifest = loaded[0] if loaded else {}
        result = {
            "id": name,
            "name": record["title"],
            "description": record["description"],
            "tags": record["tags"],
            "folder": record.get("folder", ""),
            "turns": record["turns"],
            "words": record["words"],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
            "has_workspace": loaded is not None,
            "generated_takes": len(manifest.get("takes", [])),
            "download_url": f"/tts/dialogue-scripts/{name}/download",
        }
        if full:
            result["document"] = storage.resolve_dialogue_script(root, name)[
                2
            ].read_text(encoding="utf-8")

            def asset(item):
                if not item:
                    return None
                return {
                    **{k: v for k, v in item.items() if k != "file"},
                    "url": f"/tts/dialogue-scripts/{name}/workspace/{item['file']}",
                }

            result["workspace"] = (
                {
                    **{
                        k: v
                        for k, v in manifest.items()
                        if k not in {"takes", "output", "processed"}
                    },
                    "takes": [asset(item) for item in manifest.get("takes", [])],
                    "output": asset(manifest.get("output")),
                    "processed": asset(manifest.get("processed")),
                }
                if loaded
                else None
            )
        return result

    def validate(request):
        # Scripts may refer to voices not yet installed. Runtime resolves them
        # before synthesis. Structural validation still uses the hardened compiler.
        units = parse_dialogue(request.document, "af_heart")
        return sum(u.kind == "speech" for u in units), sum(
            len(u.text.split()) for u in units
        )

    def save(request, existing=None):
        if existing is not None:
            storage.resolve_dialogue_script(root, existing)
            if storage.normalize_script_name(
                request.name
            ) != storage.normalize_script_name(existing):
                raise ValueError("Create a new script to use a different name.")
        turns, words = validate(request)
        name, record = storage.save_dialogue_script(
            root,
            name=request.name,
            document=request.document,
            description=request.description,
            tags=request.tags,
            folder=request.folder,
            turns=turns,
            words=words,
            overwrite=existing is not None,
        )
        return payload(name, record, True)

    @router.get("/tts/dialogue-scripts")
    def scripts():
        records = [
            payload(n, r)
            for n, r in sorted(storage.load_dialogue_scripts(root).items())
        ]
        folders = [
            {"id": n, "name": r["title"], "created_at": r["created_at"]}
            for n, r in storage.load_dialogue_folders(root).items()
        ]
        return {
            "object": "list",
            "data": records,
            "count": len(records),
            "folders": folders,
        }

    @router.post("/tts/dialogue-script-folders")
    def add_folder(request: FolderRequest):
        name, record = storage.create_dialogue_folder(root, request.name)
        return {"id": name, "name": record["title"], "created_at": record["created_at"]}

    @router.delete("/tts/dialogue-script-folders/{identity}")
    def delete_folder(identity: str):
        return {"deleted": storage.delete_dialogue_folder(root, identity)}

    @router.post("/tts/dialogue-scripts")
    def create(request: ScriptRequest):
        return save(request)

    @router.get("/tts/dialogue-scripts/{identity}")
    def get(identity: str):
        name, record, _ = storage.resolve_dialogue_script(root, identity)
        return payload(name, record, True)

    @router.put("/tts/dialogue-scripts/{identity}")
    def edit(identity: str, request: ScriptRequest):
        return save(request, identity)

    @router.patch("/tts/dialogue-scripts/{identity}/folder")
    def move(identity: str, request: FolderAssignment):
        name, record = storage.move_dialogue_script(root, identity, request.folder)
        return payload(name, record)

    @router.get("/tts/dialogue-scripts/{identity}/download")
    def download(identity: str):
        name, _, path = storage.resolve_dialogue_script(root, identity)
        return FileResponse(
            path, media_type="application/ssml+xml", filename=name + ".ssml"
        )

    @router.get("/tts/dialogue-scripts/{identity}/workspace/{filename}")
    def audio(identity: str, filename: str):
        return FileResponse(
            storage.resolve_dialogue_workspace_asset(root, identity, filename)
        )

    @router.delete("/tts/dialogue-scripts/{identity}")
    def delete(identity: str):
        return {"deleted": storage.delete_dialogue_script(root, identity)}

    async def save_workspace(metadata, takes, output, processed, existing=None):
        if len(metadata) > 64000:
            raise ValueError("Workspace metadata exceeds 64000 characters.")
        raw = json.loads(metadata)
        request = ScriptRequest.model_validate(raw)
        validate(request)
        workspace = raw.get("workspace", {})
        if not isinstance(workspace, dict):
            raise ValueError("Workspace must be an object.")
        items = workspace.get("takes", [])
        if not isinstance(items, list) or len(items) != len(takes) or len(items) > 64:
            raise ValueError(
                "Workspace take metadata must match uploads, up to 64 takes."
            )
        total = 0
        decoded_total = 0

        async def asset(upload):
            nonlocal total, decoded_total
            content = await upload.read(20 * 1024 * 1024 + 1)
            total += len(content)
            if len(content) > 20 * 1024 * 1024 or total > 40 * 1024 * 1024:
                raise ValueError(
                    "Workspace exceeds the 20 MB per-file or 40 MB total limit."
                )
            # Saved audio is served as audio, never arbitrary user HTML/scripts.
            decoded = await asyncio.to_thread(decode_workspace_audio, content)
            decoded_total += decoded.nbytes
            if decoded_total > 40 * 1024 * 1024:
                raise ValueError(
                    "Decoded workspace audio exceeds 40 MB. Save a shorter dialogue or fewer takes."
                )
            return await asyncio.to_thread(
                encode_audio_bytes, decoded, "wav", SAMPLE_RATE
            )

        assets = []
        for index, (item, upload) in enumerate(zip(items, takes)):
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("speech_index", index), int)
                or not 0 <= item.get("speech_index", index) < 64
            ):
                raise ValueError("Invalid saved take speech_index.")
            if (
                not isinstance(item.get("seed", 0), int)
                or not 0 <= item.get("seed", 0) < 2**32
            ):
                raise ValueError("Invalid saved take seed.")
            assets.append(({**item, "extension": "wav"}, await asset(upload)))
        output_asset = ({"extension": "wav"}, await asset(output)) if output else None
        processed_asset = (
            ({"extension": "wav"}, await asset(processed)) if processed else None
        )
        # Finish validation/decoding before touching the saved script.
        saved = await asyncio.to_thread(save, request, existing)
        await asyncio.to_thread(
            storage.save_dialogue_workspace,
            root,
            saved["id"],
            settings=workspace.get("settings"),
            finishing=workspace.get("finishing"),
            takes=assets,
            output=output_asset,
            processed=processed_asset,
        )
        return get(saved["id"])

    @router.post("/tts/dialogue-workspaces")
    async def create_workspace(
        metadata: str = Form(...),
        takes: list[UploadFile] = File(default=[]),
        output: UploadFile | None = File(None),
        processed: UploadFile | None = File(None),
    ):
        return await save_workspace(metadata, takes, output, processed)

    @router.put("/tts/dialogue-workspaces/{identity}")
    async def update_workspace(
        identity: str,
        metadata: str = Form(...),
        takes: list[UploadFile] = File(default=[]),
        output: UploadFile | None = File(None),
        processed: UploadFile | None = File(None),
    ):
        return await save_workspace(metadata, takes, output, processed, identity)

    app.include_router(router)


def decode_workspace_audio(content):
    """Decode only uploaded bytes, never external URLs/playlists; cap decoded size."""
    import subprocess

    if not content:
        raise ValueError("Choose a non-empty audio file.")
    try:
        return _decode_workspace_audio(content)
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            "Audio decoding timed out. Upload a shorter generated recording."
        ) from exc


def _decode_workspace_audio(content):
    import subprocess

    import numpy as np

    result = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-protocol_whitelist",
            "pipe",
            "-i",
            "pipe:0",
            "-t",
            "301",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            "-f",
            "s16le",
            "pipe:1",
        ],
        input=content,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode or not result.stdout:
        raise ValueError(
            "Saved workspace audio cannot be decoded. Upload generated audio."
        )
    audio = np.frombuffer(result.stdout, dtype="<i2").copy()
    if audio.size > SAMPLE_RATE * 300:
        raise ValueError("Workspace audio exceeds 300 seconds.")
    return audio
