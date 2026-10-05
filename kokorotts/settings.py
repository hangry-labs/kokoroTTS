"""Persisted operator settings for the Docker deployment."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any

from .catalog import (
    CHINESE_V11_MODEL_FAMILY,
    STANDARD_MODEL_FAMILY,
    VIETNAMESE_MODEL_FAMILY,
    model_families_for_voices,
    model_family_ids,
    voice_ids,
    voices_for_model_families,
)

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS_PATH = "/app/persistent/app/settings.json"
SERVED_VOICES_KEY = "served_voices"
SERVED_MODEL_FAMILIES_KEY = "served_model_families"
SETTINGS_SCHEMA_VERSION_KEY = "schema_version"
SETTINGS_SCHEMA_VERSION = 2
MCP_ENABLED_KEY = "mcp_enabled"

# v0.3/v1.0-snapshot installations persisted this exact list when every
# available pack was enabled. Preserve that intent when adding the v1.1 family.
PRE_CHINESE_ALL_MODEL_FAMILIES = (
    STANDARD_MODEL_FAMILY,
    "kikiri-german-martin",
    "kikiri-german-victoria",
    VIETNAMESE_MODEL_FAMILY,
)


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
            logger.warning(
                "Ignoring unreadable runtime settings %s: %s", self.path, exc
            )
            return {}
        if not isinstance(payload, dict):
            logger.warning(
                "Ignoring runtime settings %s: expected a JSON object", self.path
            )
            return {}
        return payload

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._read_unlocked())

    def served_model_families(self) -> list[str]:
        snapshot = self.snapshot()
        configured = snapshot.get(SERVED_MODEL_FAMILIES_KEY)
        schema_version = snapshot.get(SETTINGS_SCHEMA_VERSION_KEY, 1)
        if not isinstance(schema_version, int):
            schema_version = 1
        if schema_version < SETTINGS_SCHEMA_VERSION and configured == list(
            PRE_CHINESE_ALL_MODEL_FAMILIES
        ):
            configured = [*PRE_CHINESE_ALL_MODEL_FAMILIES, CHINESE_V11_MODEL_FAMILY]
            self._update(SERVED_MODEL_FAMILIES_KEY, configured)
            logger.info(
                "Enabled newly available model family %s for an existing "
                "all-models deployment",
                CHINESE_V11_MODEL_FAMILY,
            )
        if configured is None and isinstance(snapshot.get(SERVED_VOICES_KEY), list):
            configured = model_families_for_voices(snapshot[SERVED_VOICES_KEY])
        if configured is None:
            family_env = os.getenv("KOKOROTTS_SERVED_MODEL_FAMILIES", "").strip()
            env_value = os.getenv("KOKOROTTS_SERVED_VOICES", "").strip()
            if family_env:
                configured = [
                    item.strip() for item in family_env.split(",") if item.strip()
                ]
            elif env_value:
                env_voices = [
                    item.strip() for item in env_value.split(",") if item.strip()
                ]
                unknown = sorted(set(env_voices) - set(voice_ids()))
                if unknown:
                    raise ValueError(
                        "KOKOROTTS_SERVED_VOICES contains unsupported voices: "
                        + ", ".join(unknown)
                    )
                configured = model_families_for_voices(env_voices)
        if not isinstance(configured, list):
            return model_family_ids()
        return self.validate_served_model_families(configured)

    def served_voices(self) -> list[str]:
        return voices_for_model_families(self.served_model_families())

    def mcp_enabled(self, *, default: bool = False) -> bool:
        value = self.snapshot().get(MCP_ENABLED_KEY, default)
        return value if isinstance(value, bool) else default

    def set_mcp_enabled(self, enabled: bool) -> None:
        self._update(MCP_ENABLED_KEY, bool(enabled))

    def set_served_model_families(self, families: list[str]) -> list[str]:
        selected = self.validate_served_model_families(families)
        self._update(SERVED_MODEL_FAMILIES_KEY, selected, remove=(SERVED_VOICES_KEY,))
        return selected

    def set_served_voices(self, voices: list[str]) -> list[str]:
        selected = self.validate_served_voices(voices)
        self.set_served_model_families(model_families_for_voices(selected))
        return selected

    @staticmethod
    def validate_served_model_families(families: list[str]) -> list[str]:
        supported = model_family_ids()
        unknown = sorted(set(families) - set(supported))
        if unknown:
            raise ValueError(f"Unsupported model families: {', '.join(unknown)}")
        selected = [family for family in supported if family in families]
        if not selected:
            raise ValueError("At least one model family must be served.")
        return selected

    @staticmethod
    def validate_served_voices(voices: list[str]) -> list[str]:
        supported = voice_ids()
        unknown = sorted(set(voices) - set(supported))
        if unknown:
            raise ValueError(f"Unsupported voices: {', '.join(unknown)}")
        requested = [voice for voice in supported if voice in voices]
        if not requested:
            raise ValueError("At least one voice must be served.")
        return voices_for_model_families(model_families_for_voices(requested))

    def _update(self, key: str, value: Any, *, remove: tuple[str, ...] = ()) -> None:
        with self._lock:
            payload = self._read_unlocked()
            for obsolete_key in remove:
                payload.pop(obsolete_key, None)
            payload[SETTINGS_SCHEMA_VERSION_KEY] = SETTINGS_SCHEMA_VERSION
            payload[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(
                    descriptor, "w", encoding="utf-8", newline="\n"
                ) as handle:
                    json.dump(payload, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_path, self.path)
            finally:
                temporary_path.unlink(missing_ok=True)
