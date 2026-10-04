from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from kokorotts.catalog import (
    CHINESE_V11_ENGLISH_VOICES,
    CHINESE_V11_FEMALE_VOICES,
    CHINESE_V11_MALE_VOICES,
    CHINESE_V11_MODEL_FAMILY,
    CHINESE_V11_REPO_ID,
    CHINESE_V11_REVISION,
    CHINESE_V11_VOICE_IDS,
    CUSTOM_VOICE_ASSETS,
    voice_language,
    voices_for_model_families,
)
from kokorotts.pipeline import KPipeline
from kokorotts.prefetch_assets import main as prefetch_assets


class ChineseV11SupportTest(unittest.TestCase):
    def test_catalog_maps_all_upstream_voices_to_one_model_family(self) -> None:
        self.assertEqual(len(CHINESE_V11_FEMALE_VOICES), 55)
        self.assertEqual(len(CHINESE_V11_MALE_VOICES), 45)
        self.assertEqual(len(CHINESE_V11_ENGLISH_VOICES), 3)
        self.assertEqual(len(CHINESE_V11_VOICE_IDS), 103)
        self.assertEqual(len(set(CHINESE_V11_VOICE_IDS)), 103)
        self.assertEqual(
            voices_for_model_families([CHINESE_V11_MODEL_FAMILY]),
            list(CHINESE_V11_VOICE_IDS),
        )

        for voice_id in CHINESE_V11_VOICE_IDS:
            asset = CUSTOM_VOICE_ASSETS[voice_id]
            self.assertEqual(asset["model_family"], CHINESE_V11_MODEL_FAMILY)
            self.assertEqual(asset["repo_id"], CHINESE_V11_REPO_ID)
            self.assertEqual(asset["model_file"], "kokoro-v1_1-zh.pth")
            self.assertEqual(asset["config_file"], "config.json")
            self.assertEqual(asset["voice_file"], f"voices/{voice_id}.pt")
            self.assertEqual(asset["pipeline_repo_id"], CHINESE_V11_REPO_ID)
            self.assertEqual(asset["revision"], CHINESE_V11_REVISION)

        self.assertTrue(
            all(voice_language(voice) == "z" for voice in CHINESE_V11_FEMALE_VOICES)
        )
        self.assertTrue(
            all(voice_language(voice) == "z" for voice in CHINESE_V11_MALE_VOICES)
        )
        self.assertEqual(
            [voice_language(voice) for voice in CHINESE_V11_ENGLISH_VOICES],
            ["a", "a", "b"],
        )

    def test_chinese_pipeline_selects_v11_frontend_from_repository(self) -> None:
        pipeline = KPipeline(lang_code="z", repo_id=CHINESE_V11_REPO_ID, model=False)

        self.assertEqual(pipeline.repo_id, CHINESE_V11_REPO_ID)
        self.assertEqual(getattr(pipeline.g2p, "version", None), "1.1")
        segments = list(pipeline("银行行长今天使用新的中文语音。"))
        self.assertTrue(segments)
        self.assertTrue(all(segment.phonemes for segment in segments))

    def test_public_gallery_has_every_chinese_v11_voice_and_audio_file(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / "examples" / "voices.js").read_text(encoding="utf-8").strip()
        payload = source.removeprefix("window.VOICE_EXAMPLES =").removesuffix(";")
        examples = json.loads(payload)
        by_voice = {example["voice"]: example for example in examples}

        self.assertEqual(set(CHINESE_V11_VOICE_IDS) - set(by_voice), set())
        for voice_id in CHINESE_V11_VOICE_IDS:
            audio_path = root / "examples" / by_voice[voice_id]["file"]
            self.assertTrue(audio_path.is_file(), audio_path)
            self.assertGreater(audio_path.stat().st_size, 10_000, audio_path)

    @patch("kokorotts.prefetch_assets.hf_hub_download")
    def test_prefetch_downloads_only_deployable_chinese_assets_once(
        self, download
    ) -> None:
        with patch("builtins.print"):
            prefetch_assets()
        downloads = [
            (call.kwargs["repo_id"], call.kwargs["filename"])
            for call in download.call_args_list
        ]
        chinese = [item for item in downloads if item[0] == CHINESE_V11_REPO_ID]

        self.assertEqual(chinese.count((CHINESE_V11_REPO_ID, "kokoro-v1_1-zh.pth")), 1)
        self.assertEqual(chinese.count((CHINESE_V11_REPO_ID, "config.json")), 1)
        self.assertEqual(
            {filename for _, filename in chinese if filename.startswith("voices/")},
            {f"voices/{voice_id}.pt" for voice_id in CHINESE_V11_VOICE_IDS},
        )
        self.assertEqual(len(chinese), 105)
        self.assertTrue(
            all(
                call.kwargs.get("revision") == CHINESE_V11_REVISION
                for call in download.call_args_list
                if call.kwargs["repo_id"] == CHINESE_V11_REPO_ID
            )
        )


if __name__ == "__main__":
    unittest.main()
