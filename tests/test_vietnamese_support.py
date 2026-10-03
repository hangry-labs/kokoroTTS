from __future__ import annotations

import unittest
from unittest.mock import patch

from kokorotts.catalog import (
    CUSTOM_VOICE_ASSETS,
    VIETNAMESE_MODEL_FAMILY,
    VIETNAMESE_REPO_ID,
    VIETNAMESE_VOICE_FILES,
    voice_language,
    voices_for_language,
)
from kokorotts.pipeline import KPipeline
from kokorotts.prefetch_assets import main as prefetch_assets


class VietnameseSupportTest(unittest.TestCase):
    def test_catalog_maps_all_upstream_voices_to_one_model_family(self) -> None:
        self.assertEqual(voices_for_language("v"), list(VIETNAMESE_VOICE_FILES))
        for voice_id, voice_file in VIETNAMESE_VOICE_FILES.items():
            asset = CUSTOM_VOICE_ASSETS[voice_id]
            self.assertEqual(voice_language(voice_id), "v")
            self.assertEqual(asset["model_family"], VIETNAMESE_MODEL_FAMILY)
            self.assertEqual(asset["repo_id"], VIETNAMESE_REPO_ID)
            self.assertEqual(asset["model_file"], "kokoro_vi.pth")
            self.assertEqual(asset["config_file"], "config.json")
            self.assertEqual(asset["voice_file"], voice_file)

    def test_vig2p_phonemizes_and_normalizes_vietnamese_text(self) -> None:
        pipeline = KPipeline(lang_code="vi", model=False)
        segments = list(pipeline("Hôm nay là ngày 3 tháng 10 năm 2026."))

        self.assertEqual(len(segments), 1)
        self.assertTrue(segments[0].phonemes)
        self.assertNotIn("2026", segments[0].phonemes)

    def test_long_vietnamese_text_is_split_without_phoneme_truncation(self) -> None:
        pipeline = KPipeline(lang_code="v", model=False)
        text = (
            "Kokoro đang kiểm tra một đoạn văn tiếng Việt dài và rõ ràng. "
            "Mọi phần của nội dung đều cần được giữ lại khi tạo âm thanh. "
        ) * 20

        segments = list(pipeline(text))

        self.assertGreater(len(segments), 1)
        self.assertTrue(all(0 < len(segment.phonemes) <= 510 for segment in segments))

    @patch("kokorotts.prefetch_assets.hf_hub_download")
    def test_prefetch_downloads_only_deployable_vietnamese_assets_once(
        self, download
    ) -> None:
        prefetch_assets()
        downloads = [
            (call.kwargs["repo_id"], call.kwargs["filename"])
            for call in download.call_args_list
        ]
        vietnamese = [item for item in downloads if item[0] == VIETNAMESE_REPO_ID]

        self.assertEqual(vietnamese.count((VIETNAMESE_REPO_ID, "kokoro_vi.pth")), 1)
        self.assertEqual(vietnamese.count((VIETNAMESE_REPO_ID, "config.json")), 1)
        self.assertEqual(
            {filename for _, filename in vietnamese if filename.startswith("voicepacks/")},
            set(VIETNAMESE_VOICE_FILES.values()),
        )
        self.assertNotIn((VIETNAMESE_REPO_ID, "kokoro_vi.onnx"), vietnamese)


if __name__ == "__main__":
    unittest.main()
