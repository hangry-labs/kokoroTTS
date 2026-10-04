from __future__ import annotations

import unittest
from unittest.mock import patch

from kokorotts.pipeline import KPipeline


class IdentityG2P:
    def __call__(self, text):
        return text, None


class PipelineChunkingTest(unittest.TestCase):
    def pipeline(self, language: str = "j") -> KPipeline:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = language
        pipeline.model = None
        pipeline.g2p = IdentityG2P()
        return pipeline

    def assert_complete_chunks(self, text: str) -> None:
        results = list(self.pipeline()(text, model=False))

        self.assertGreater(len(results), 1)
        self.assertEqual("".join(result.graphemes for result in results), text)
        self.assertEqual("".join(result.phonemes for result in results), text)
        self.assertTrue(all(len(result.phonemes) <= 510 for result in results))

    def test_non_english_unpunctuated_text_is_not_truncated(self) -> None:
        self.assert_complete_chunks("文" * 1_200)

    def test_cjk_sentence_punctuation_is_used_without_losing_text(self) -> None:
        self.assert_complete_chunks((("文" * 260) + "。") * 5)

    def test_non_english_decimal_point_stays_with_number(self) -> None:
        text = ("a" * 396) + "3.14" + ("b" * 20)

        chunks = KPipeline._split_graphemes(text)

        self.assertEqual("".join(chunks), text)
        self.assertTrue(any("3.14" in chunk for chunk in chunks))
        self.assertFalse(any(chunk.endswith("3.") for chunk in chunks))

    def test_sentence_period_after_decimal_remains_boundary(self) -> None:
        text = ("a" * 390) + " 3.14. " + ("b" * 30)

        chunks = KPipeline._split_graphemes(text)

        self.assertEqual("".join(chunks), text)
        self.assertTrue(chunks[0].endswith("3.14. "))

    def test_versions_and_currency_decimals_are_not_sentence_boundaries(self) -> None:
        text = "Version 1.2.3 costs 12.50 euros. Next sentence."

        chunks = KPipeline._split_graphemes(text)

        self.assertEqual(chunks, [text])
        self.assertIn("1.2.3", chunks[0])
        self.assertIn("12.50", chunks[0])

    def test_japanese_pipeline_uses_pyopenjtalk(self) -> None:
        with patch("misaki.ja.JAG2P") as g2p:
            KPipeline(lang_code="j", model=False)

        g2p.assert_called_once_with(version="pyopenjtalk")


if __name__ == "__main__":
    unittest.main()
