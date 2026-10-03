from __future__ import annotations

import unittest

from kokorotts.catalog import CUSTOM_VOICE_ASSETS, voices_for_language
from kokorotts.pipeline import KPipeline


class GermanSupportTest(unittest.TestCase):
    def test_catalog_maps_each_voice_to_its_matching_checkpoint(self) -> None:
        self.assertEqual(voices_for_language("d"), ["df_victoria", "dm_martin"])
        self.assertEqual(
            CUSTOM_VOICE_ASSETS["df_victoria"]["model_file"],
            "kikiri_german_victoria_ep10.pth",
        )
        self.assertEqual(
            CUSTOM_VOICE_ASSETS["dm_martin"]["model_file"],
            "kikiri_german_martin_ep10.pth",
        )

    def test_dedicated_german_g2p_normalizes_numbers_and_dates(self) -> None:
        pipeline = KPipeline(lang_code="de", model=False)
        segments = list(pipeline("Am 3.10.2026 kostet es 12,50 Euro."))

        self.assertEqual(len(segments), 1)
        self.assertTrue(segments[0].phonemes)
        self.assertNotIn("2026", segments[0].phonemes)
        self.assertNotIn("12,50", segments[0].phonemes)


if __name__ == "__main__":
    unittest.main()
