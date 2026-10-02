from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
