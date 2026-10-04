from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kokorotts.catalog import (
    CHINESE_V11_MODEL_FAMILY,
    STANDARD_MODEL_FAMILY,
    model_family_ids,
    voice_ids,
    voices_for_model_families,
)
from kokorotts.settings import DEFAULT_SETTINGS_PATH, RuntimeSettingsStore


class RuntimeSettingsStoreTest(unittest.TestCase):
    def test_missing_settings_default_to_every_supported_voice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            self.assertEqual(store.served_voices(), voice_ids())

    def test_voice_compatibility_setting_expands_and_persists_model_families(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = RuntimeSettingsStore(path)

            selected = store.set_served_voices(["dm_martin", "af_heart"])

            expected = voices_for_model_families(
                [STANDARD_MODEL_FAMILY, "kikiri-german-martin"]
            )
            self.assertEqual(selected, expected)
            self.assertEqual(store.served_voices(), selected)
            self.assertEqual(
                json.loads(path.read_text())["served_model_families"],
                [STANDARD_MODEL_FAMILY, "kikiri-german-martin"],
            )

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
            with patch.dict(
                "os.environ", {"KOKOROTTS_SERVED_VOICES": "dm_martin,af_heart"}
            ):
                self.assertEqual(
                    store.served_model_families(),
                    [STANDARD_MODEL_FAMILY, "kikiri-german-martin"],
                )
                store.set_served_voices(["df_victoria"])
                self.assertEqual(store.served_voices(), ["df_victoria"])

    def test_invalid_environment_voice_fails_instead_of_serving_everything(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            with patch.dict("os.environ", {"KOKOROTTS_SERVED_VOICES": "typo"}):
                with self.assertRaisesRegex(ValueError, "unsupported voices"):
                    store.served_voices()

    def test_model_families_are_the_atomic_deployment_unit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = RuntimeSettingsStore(Path(directory) / "settings.json")
            selected = store.set_served_model_families(["kikiri-german-martin"])

            self.assertEqual(selected, ["kikiri-german-martin"])
            self.assertEqual(store.served_voices(), ["dm_martin"])
            with self.assertRaisesRegex(ValueError, "At least one model family"):
                store.set_served_model_families([])
            with self.assertRaisesRegex(ValueError, "Unsupported model families"):
                store.set_served_model_families(["unknown"])

    def test_previous_all_models_setting_enables_new_chinese_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "served_model_families": [
                            STANDARD_MODEL_FAMILY,
                            "kikiri-german-martin",
                            "kikiri-german-victoria",
                            "contextboxai-kokoro-vietnamese",
                        ]
                    }
                )
            )

            self.assertEqual(
                RuntimeSettingsStore(path).served_model_families(), model_family_ids()
            )
            self.assertEqual(
                json.loads(path.read_text())["served_model_families"],
                model_family_ids(),
            )

    def test_custom_model_selection_does_not_enable_new_chinese_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            selected = [STANDARD_MODEL_FAMILY, "kikiri-german-martin"]
            path.write_text(json.dumps({"served_model_families": selected}))

            self.assertEqual(
                RuntimeSettingsStore(path).served_model_families(), selected
            )
            self.assertEqual(
                json.loads(path.read_text())["served_model_families"],
                selected,
            )

    def test_new_explicit_previous_four_selection_remains_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            selected = model_family_ids()[:-1]
            store = RuntimeSettingsStore(path)

            self.assertEqual(store.set_served_model_families(selected), selected)
            self.assertEqual(store.served_model_families(), selected)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 2)

    def test_legacy_partial_voice_setting_expands_to_the_model_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"served_voices": ["af_heart"]}))
            store = RuntimeSettingsStore(path)

            self.assertEqual(store.served_model_families(), [STANDARD_MODEL_FAMILY])
            self.assertEqual(
                store.served_voices(),
                voices_for_model_families([STANDARD_MODEL_FAMILY]),
            )

    def test_default_settings_path_uses_the_optional_persistent_data_root(self) -> None:
        self.assertEqual(DEFAULT_SETTINGS_PATH, "/app/persistent/app/settings.json")
        self.assertEqual(
            model_family_ids(),
            [
                STANDARD_MODEL_FAMILY,
                "kikiri-german-martin",
                "kikiri-german-victoria",
                "contextboxai-kokoro-vietnamese",
                CHINESE_V11_MODEL_FAMILY,
            ],
        )


if __name__ == "__main__":
    unittest.main()
