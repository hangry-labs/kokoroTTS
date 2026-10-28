"""Adapted from Hangry Labs VoxCPMTTS, Apache-2.0; see THIRD_PARTY_NOTICES.md."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPT_LOCK = threading.RLock()
MAX_SCRIPT_NAME_CHARACTERS = 80
MAX_SCRIPT_DESCRIPTION_CHARACTERS = 240
MAX_SCRIPT_DOCUMENT_BYTES = 1_000_000
MAX_SCRIPT_TAGS = 12
MAX_SCRIPT_TAG_CHARACTERS = 32
MAX_SCRIPT_FOLDER_CHARACTERS = 80
MAX_WORKSPACE_METADATA_BYTES = 64_000


def normalize_script_name(name: str | None) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (name or "").strip().lower()).strip("-_")
    if not value:
        raise ValueError("Script name must contain at least one letter or number.")
    if len(value) > MAX_SCRIPT_NAME_CHARACTERS:
        raise ValueError(
            f"Script name must be {MAX_SCRIPT_NAME_CHARACTERS} characters or fewer."
        )
    return value


def normalize_script_document(document: str | None) -> str:
    value = (document or "").strip()
    if not value:
        raise ValueError("SSML-H document must not be empty.")
    if len(value.encode("utf-8")) > MAX_SCRIPT_DOCUMENT_BYTES:
        raise ValueError("SSML-H document exceeds the 1 MB storage limit.")
    return f"{value}\n"


def normalize_script_tags(tags: list[Any] | tuple[Any, ...] | None) -> list[str]:
    if tags is None:
        return []
    if not isinstance(tags, (list, tuple)):
        raise ValueError("Dialogue script tags must be a JSON array.")
    if len(tags) > MAX_SCRIPT_TAGS:
        raise ValueError(f"Dialogue scripts support at most {MAX_SCRIPT_TAGS} tags.")
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = re.sub(r"\s+", " ", str(raw_tag or "").strip())
        if not tag:
            continue
        if len(tag) > MAX_SCRIPT_TAG_CHARACTERS:
            raise ValueError(
                f"Dialogue script tags must be {MAX_SCRIPT_TAG_CHARACTERS} characters or fewer."
            )
        identity = tag.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append(tag)
    return normalized


def normalize_script_folder(folder: str | None) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (folder or "").strip().lower()).strip("-_")
    if len(value) > MAX_SCRIPT_FOLDER_CHARACTERS:
        raise ValueError(
            f"Script folder name must be {MAX_SCRIPT_FOLDER_CHARACTERS} characters or fewer."
        )
    return value


def _folder_title(value: str) -> str:
    title = re.sub(r"\s+", " ", value.strip())
    if not title:
        raise ValueError("Script folder name must not be empty.")
    if len(title) > MAX_SCRIPT_FOLDER_CHARACTERS:
        raise ValueError(
            f"Script folder name must be {MAX_SCRIPT_FOLDER_CHARACTERS} characters or fewer."
        )
    return title


def _write_index(script_dir: Path, scripts: dict[str, dict[str, Any]]) -> None:
    script_dir.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=script_dir,
            prefix=".scripts.",
            suffix=".tmp",
        ) as output:
            temporary_path = Path(output.name)
            json.dump(scripts, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, script_dir / "scripts.json")
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_folders(script_dir: Path, folders: dict[str, dict[str, str]]) -> None:
    script_dir.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=script_dir,
            prefix=".folders.",
            suffix=".tmp",
        ) as output:
            temporary_path = Path(output.name)
            json.dump(folders, output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, script_dir / "folders.json")
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _document_path(script_dir: Path, filename: str) -> Path | None:
    if not filename:
        return None
    root = script_dir.resolve()
    candidate = (root / Path(filename).name).resolve()
    if candidate.parent != root or not candidate.is_file():
        return None
    return candidate


def _workspace_path(script_dir: Path, dirname: str) -> Path | None:
    if not dirname:
        return None
    root = script_dir.resolve()
    candidate = (root / Path(dirname).name).resolve()
    if candidate.parent != root or not candidate.is_dir():
        return None
    return candidate


def load_dialogue_folders(script_dir: Path) -> dict[str, dict[str, str]]:
    path = script_dir / "folders.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    folders: dict[str, dict[str, str]] = {}
    for raw_id, raw_folder in raw.items():
        if not isinstance(raw_folder, dict):
            continue
        try:
            folder_id = normalize_script_folder(str(raw_id))
        except ValueError:
            continue
        if not folder_id:
            continue
        try:
            title = _folder_title(str(raw_folder.get("title") or folder_id))
        except ValueError:
            continue
        folders[folder_id] = {
            "title": title,
            "created_at": str(raw_folder.get("created_at") or ""),
        }
    return folders


def create_dialogue_folder(script_dir: Path, name: str) -> tuple[str, dict[str, str]]:
    folder_id = normalize_script_folder(name)
    title = _folder_title(name)
    if not folder_id:
        raise ValueError(
            "Script folder name must contain at least one letter or number."
        )
    with SCRIPT_LOCK:
        folders = load_dialogue_folders(script_dir)
        if folder_id in folders:
            raise ValueError(f"Script folder '{folder_id}' already exists.")
        record = {"title": title, "created_at": datetime.now(UTC).isoformat()}
        folders[folder_id] = record
        _write_folders(script_dir, folders)
    return folder_id, record


def delete_dialogue_folder(script_dir: Path, name: str) -> str:
    folder_id = normalize_script_folder(name)
    with SCRIPT_LOCK:
        folders = load_dialogue_folders(script_dir)
        if folders.pop(folder_id, None) is None:
            raise ValueError(f"Script folder '{folder_id}' does not exist.")
        scripts = load_dialogue_scripts(script_dir)
        for script in scripts.values():
            if script.get("folder") == folder_id:
                script["folder"] = ""
        _write_folders(script_dir, folders)
        _write_index(script_dir, scripts)
    return folder_id


def load_dialogue_scripts(script_dir: Path) -> dict[str, dict[str, Any]]:
    index_path = script_dir / "scripts.json"
    if not index_path.exists():
        return {}
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}

    scripts: dict[str, dict[str, Any]] = {}
    for raw_name, raw_script in raw.items():
        if not isinstance(raw_script, dict):
            continue
        try:
            name = normalize_script_name(str(raw_name))
        except ValueError:
            continue
        filename = Path(str(raw_script.get("document_file") or "")).name
        if _document_path(script_dir, filename) is None:
            continue
        try:
            turns = max(0, int(raw_script.get("turns") or 0))
            words = max(0, int(raw_script.get("words") or 0))
        except (TypeError, ValueError):
            turns = 0
            words = 0
        try:
            tags = normalize_script_tags(raw_script.get("tags"))
        except ValueError:
            tags = []
        try:
            folder = normalize_script_folder(str(raw_script.get("folder") or ""))
        except ValueError:
            folder = ""
        scripts[name] = {
            "title": str(raw_script.get("title") or name).strip()[
                :MAX_SCRIPT_NAME_CHARACTERS
            ],
            "description": str(raw_script.get("description") or "").strip()[
                :MAX_SCRIPT_DESCRIPTION_CHARACTERS
            ],
            "tags": tags,
            "folder": folder,
            "document_file": filename,
            "workspace_dir": Path(str(raw_script.get("workspace_dir") or "")).name
            if _workspace_path(script_dir, str(raw_script.get("workspace_dir") or ""))
            is not None
            else "",
            "turns": turns,
            "words": words,
            "created_at": str(raw_script.get("created_at") or ""),
            "updated_at": str(raw_script.get("updated_at") or ""),
        }
    return scripts


def save_dialogue_script(
    script_dir: Path,
    *,
    name: str,
    document: str,
    description: str = "",
    tags: list[Any] | tuple[Any, ...] | None = None,
    folder: str = "",
    turns: int = 0,
    words: int = 0,
    overwrite: bool = False,
) -> tuple[str, dict[str, Any]]:
    script_name = normalize_script_name(name)
    title = re.sub(r"\s+", " ", name.strip())
    if len(title) > MAX_SCRIPT_NAME_CHARACTERS:
        raise ValueError(
            f"Script name must be {MAX_SCRIPT_NAME_CHARACTERS} characters or fewer."
        )
    normalized_description = description.strip()
    if len(normalized_description) > MAX_SCRIPT_DESCRIPTION_CHARACTERS:
        raise ValueError(
            f"Script description must be {MAX_SCRIPT_DESCRIPTION_CHARACTERS} characters or fewer."
        )
    normalized_document = normalize_script_document(document)
    normalized_tags = normalize_script_tags(tags)
    normalized_folder = normalize_script_folder(folder)
    if normalized_folder and normalized_folder not in load_dialogue_folders(script_dir):
        raise ValueError(f"Script folder '{normalized_folder}' does not exist.")

    with SCRIPT_LOCK:
        script_dir.mkdir(parents=True, exist_ok=True)
        scripts = load_dialogue_scripts(script_dir)
        existing = scripts.get(script_name)
        if existing is not None and not overwrite:
            raise ValueError(f"Dialogue script '{script_name}' already exists.")

        filename = f"script-{script_name}-{secrets.token_hex(6)}.ssml"
        destination = script_dir / filename
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=script_dir,
                prefix=".script.",
                suffix=".tmp",
            ) as output:
                temporary_path = Path(output.name)
                output.write(normalized_document)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, destination)
            temporary_path = None

            now = datetime.now(UTC).isoformat()
            record = {
                "title": title,
                "description": normalized_description,
                "tags": normalized_tags,
                "folder": normalized_folder,
                "document_file": filename,
                "workspace_dir": str((existing or {}).get("workspace_dir") or ""),
                "turns": max(0, int(turns)),
                "words": max(0, int(words)),
                "created_at": existing.get("created_at", now) if existing else now,
                "updated_at": now,
            }
            scripts[script_name] = record
            _write_index(script_dir, scripts)
        except Exception:
            destination.unlink(missing_ok=True)
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

        previous = str((existing or {}).get("document_file") or "")
        if previous and previous != filename:
            (script_dir / Path(previous).name).unlink(missing_ok=True)
        return script_name, record


def move_dialogue_script(
    script_dir: Path, name: str, folder: str
) -> tuple[str, dict[str, Any]]:
    script_name = normalize_script_name(name)
    folder_id = normalize_script_folder(folder)
    with SCRIPT_LOCK:
        if folder_id and folder_id not in load_dialogue_folders(script_dir):
            raise ValueError(f"Script folder '{folder_id}' does not exist.")
        scripts = load_dialogue_scripts(script_dir)
        record = scripts.get(script_name)
        if record is None:
            raise ValueError(f"Dialogue script '{script_name}' does not exist.")
        record["folder"] = folder_id
        record["updated_at"] = datetime.now(UTC).isoformat()
        _write_index(script_dir, scripts)
    return script_name, record


def _workspace_extension(value: Any, default: str = "wav") -> str:
    extension = re.sub(r"[^a-z0-9]", "", str(value or default).lower())[:8]
    return extension or default


def save_dialogue_workspace(
    script_dir: Path,
    name: str,
    *,
    settings: dict[str, Any] | None,
    finishing: dict[str, Any] | None,
    takes: list[tuple[dict[str, Any], bytes]],
    output: tuple[dict[str, Any], bytes] | None,
    processed: tuple[dict[str, Any], bytes] | None,
) -> dict[str, Any]:
    script_name = normalize_script_name(name)
    workspace_name = f"workspace-{script_name}-{secrets.token_hex(6)}"
    workspace_path = script_dir / workspace_name
    workspace_path.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "version": 1,
        "settings": settings if isinstance(settings, dict) else {},
        "finishing": finishing if isinstance(finishing, dict) else {},
        "takes": [],
        "output": None,
        "processed": None,
    }
    try:
        for position, (metadata, data) in enumerate(takes):
            extension = _workspace_extension(metadata.get("extension"), "wav")
            filename = f"take-{position:03d}.{extension}"
            (workspace_path / filename).write_bytes(data)
            manifest["takes"].append(
                {
                    "speech_index": max(0, int(metadata.get("speech_index", position))),
                    "seed": max(0, int(metadata.get("seed", 0))),
                    "locked": bool(metadata.get("locked", False)),
                    "extension": extension,
                    "file": filename,
                }
            )
        for key, asset in (("output", output), ("processed", processed)):
            if asset is None:
                continue
            metadata, data = asset
            extension = _workspace_extension(metadata.get("extension"), "wav")
            filename = f"{key}.{extension}"
            (workspace_path / filename).write_bytes(data)
            manifest[key] = {"extension": extension, "file": filename}
        encoded = json.dumps(manifest, ensure_ascii=True, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(encoded) > MAX_WORKSPACE_METADATA_BYTES:
            raise ValueError("Dialogue workspace metadata is too large.")
        (workspace_path / "workspace.json").write_bytes(encoded + b"\n")

        with SCRIPT_LOCK:
            scripts = load_dialogue_scripts(script_dir)
            record = scripts.get(script_name)
            if record is None:
                raise ValueError(f"Dialogue script '{script_name}' does not exist.")
            previous = str(record.get("workspace_dir") or "")
            record["workspace_dir"] = workspace_name
            record["updated_at"] = datetime.now(UTC).isoformat()
            _write_index(script_dir, scripts)
        previous_path = _workspace_path(script_dir, previous)
        if previous_path is not None and previous_path != workspace_path:
            shutil.rmtree(previous_path)
        return manifest
    except Exception:
        shutil.rmtree(workspace_path, ignore_errors=True)
        raise


def load_dialogue_workspace(
    script_dir: Path, record: dict[str, Any]
) -> tuple[dict[str, Any], Path] | None:
    workspace_path = _workspace_path(script_dir, str(record.get("workspace_dir") or ""))
    if workspace_path is None:
        return None
    manifest_path = workspace_path / "workspace.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        return None
    return manifest, workspace_path


def resolve_dialogue_workspace_asset(
    script_dir: Path, name: str, filename: str
) -> Path:
    _, record, _ = resolve_dialogue_script(script_dir, name)
    loaded = load_dialogue_workspace(script_dir, record)
    if loaded is None:
        raise ValueError("Dialogue script has no saved workspace audio.")
    manifest, workspace_path = loaded
    allowed = {
        str(item.get("file") or "")
        for item in manifest.get("takes", [])
        if isinstance(item, dict)
    }
    for key in ("output", "processed"):
        item = manifest.get(key)
        if isinstance(item, dict):
            allowed.add(str(item.get("file") or ""))
    safe_name = Path(filename).name
    candidate = (workspace_path / safe_name).resolve()
    if (
        safe_name not in allowed
        or candidate.parent != workspace_path.resolve()
        or not candidate.is_file()
    ):
        raise ValueError("Dialogue workspace audio asset does not exist.")
    return candidate


def resolve_dialogue_script(
    script_dir: Path, name: str
) -> tuple[str, dict[str, Any], Path]:
    script_name = normalize_script_name(name)
    with SCRIPT_LOCK:
        record = load_dialogue_scripts(script_dir).get(script_name)
        path = _document_path(
            script_dir, str((record or {}).get("document_file") or "")
        )
    if record is None or path is None:
        raise FileNotFoundError(f"Dialogue script '{script_name}' does not exist.")
    return script_name, record, path


def delete_dialogue_script(script_dir: Path, name: str) -> str:
    script_name = normalize_script_name(name)
    with SCRIPT_LOCK:
        scripts = load_dialogue_scripts(script_dir)
        record = scripts.pop(script_name, None)
        if record is None:
            raise ValueError(f"Dialogue script '{script_name}' does not exist.")
        _write_index(script_dir, scripts)
        (script_dir / Path(str(record.get("document_file") or "")).name).unlink(
            missing_ok=True
        )
        workspace_path = _workspace_path(
            script_dir, str(record.get("workspace_dir") or "")
        )
        if workspace_path is not None:
            shutil.rmtree(workspace_path)
    return script_name
