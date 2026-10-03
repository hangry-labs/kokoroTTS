from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kokorotts.catalog import voice_ids
from kokorotts.settings import RuntimeSettingsStore


class RuntimeSettingsStoreTest(unittest.TestCase):
    def test_missing_settings_default_to_every_supported_voice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            self.assertEqual(store.served_voices(), voice_ids())

    def test_served_voices_are_validated_ordered_and_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = RuntimeSettingsStore(path)

            selected = store.set_served_voices(["dm_martin", "af_heart"])

            self.assertEqual(selected, ["af_heart", "dm_martin"])
            self.assertEqual(store.served_voices(), selected)
            self.assertEqual(json.loads(path.read_text())["served_voices"], selected)

    def test_empty_or_unknown_selection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            with self.assertRaisesRegex(ValueError, "At least one"):
                store.set_served_voices([])
            with self.assertRaisesRegex(ValueError, "Unsupported voices"):
                store.set_served_voices(["not_a_voice"])

    def test_environment_default_is_used_until_a_setting_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            with patch.dict("os.environ", {"KOKOROTTS_SERVED_VOICES": "dm_martin,af_heart"}):
                self.assertEqual(store.served_voices(), ["af_heart", "dm_martin"])
                store.set_served_voices(["df_victoria"])
                self.assertEqual(store.served_voices(), ["df_victoria"])

    def test_invalid_environment_voice_fails_instead_of_serving_everything(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            with patch.dict("os.environ", {"KOKOROTTS_SERVED_VOICES": "typo"}):
                with self.assertRaisesRegex(ValueError, "unsupported voices"):
                    store.served_voices()


if __name__ == "__main__":
    unittest.main()
