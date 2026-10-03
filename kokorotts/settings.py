"""Persisted operator settings for the Docker deployment."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from .catalog import voice_ids

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = "/app/.cache/huggingface/.kokorotts/settings.json"
SERVED_VOICES_KEY = "served_voices"


class RuntimeSettingsStore:
    """Store the small set of operator-controlled settings atomically."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured_path = path or os.getenv("KOKOROTTS_SETTINGS_PATH")
        self.path = Path(configured_path or DEFAULT_SETTINGS_PATH)
        self._lock = RLock()

    def _read_unlocked(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Ignoring unreadable runtime settings %s: %s", self.path, exc)
            return {}
        if not isinstance(payload, dict):
            logger.warning("Ignoring runtime settings %s: expected a JSON object", self.path)
            return {}
        return payload

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._read_unlocked())

    def served_voices(self) -> list[str]:
        supported = voice_ids()
        configured = self.snapshot().get(SERVED_VOICES_KEY)
        if configured is None:
            env_value = os.getenv("KOKOROTTS_SERVED_VOICES", "").strip()
            configured = (
                [item.strip() for item in env_value.split(",") if item.strip()]
                if env_value
                else None
            )
            if configured is not None:
                unknown = sorted(set(configured) - set(supported))
                if unknown:
                    raise ValueError(
                        "KOKOROTTS_SERVED_VOICES contains unsupported voices: "
                        + ", ".join(unknown)
                    )
        if not isinstance(configured, list):
            return supported
        selected = [voice for voice in supported if voice in configured]
        return selected or supported

    def set_served_voices(self, voices: list[str]) -> list[str]:
        selected = self.validate_served_voices(voices)
        self._update(SERVED_VOICES_KEY, selected)
        return selected

    @staticmethod
    def validate_served_voices(voices: list[str]) -> list[str]:
        supported = voice_ids()
        unknown = sorted(set(voices) - set(supported))
        if unknown:
            raise ValueError(f"Unsupported voices: {', '.join(unknown)}")
        selected = [voice for voice in supported if voice in voices]
        if not selected:
            raise ValueError("At least one voice must be served.")
        return selected

    def _update(self, key: str, value: Any) -> None:
        with self._lock:
            payload = self._read_unlocked()
            payload[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(payload, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, self.path)
            finally:
                temporary_path.unlink(missing_ok=True)
