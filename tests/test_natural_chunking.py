from __future__ import annotations

import unittest
from unittest.mock import patch

from kokorotts.natural_chunking import ChunkingValidationError, phonemize_naturally
from kokorotts.pipeline import KPipeline, MODEL_PHONEME_LIMIT


def expanded(text: str):
    return "".join(character * 3 for character in text), None


class NaturalChunkingTest(unittest.TestCase):
    def assert_complete(self, text: str) -> list[tuple[str, str]]:
        chunks = list(phonemize_naturally(text, expanded, MODEL_PHONEME_LIMIT))
        self.assertEqual("".join(chunk for chunk, _ in chunks), text)
        self.assertEqual("".join(ps for _, ps in chunks), expanded(text)[0])
        self.assertTrue(all(0 < len(ps) <= MODEL_PHONEME_LIMIT for _, ps in chunks))
        return chunks

    def test_long_cjk_unpunctuated_and_ascii_input_is_complete(self) -> None:
        for text in (
            "今日はいい天気ですね。" * 40,
            "文" * 1200,
            "A" * 1200,
            ("αβγ " * 250) + "終",
        ):
            with self.subTest(text=text[:24]):
                self.assertGreater(len(self.assert_complete(text)), 1)

    def test_short_input_keeps_the_same_phonemes(self) -> None:
        text = "你好。世界！"
        self.assertEqual(self.assert_complete(text), [(text, expanded(text)[0])])

    def test_closing_quote_stays_with_its_sentence(self) -> None:
        text = "「" + ("文" * 169) + "。」" + ("次" * 170)
        chunks = list(phonemize_naturally(text, lambda value: (value * 2, None), 510))
        self.assertTrue(chunks[0][0].endswith("。」"))
        self.assertEqual("".join(value for value, _ in chunks), text)

    def test_ascii_word_is_not_split_when_a_nearby_boundary_exists(self) -> None:
        word = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        chunks = self.assert_complete(("文" * 80) + word + ("文" * 80))
        self.assertTrue(any(word in value for value, _ in chunks))

    def test_decimals_versions_and_urls_survive_nearby_cuts(self) -> None:
        for token in ("3.14159", "12,50", "1.2.3", "example.com", "https://example.com/a"):
            with self.subTest(token=token):
                chunks = self.assert_complete(("文" * 80) + token + ("文" * 80))
                self.assertTrue(any(token in value for value, _ in chunks))

    def test_nonuniform_frontend_expansion_is_rechecked_after_each_cut(self) -> None:
        text = ("a" * 130) + ("文" * 150) + ("b" * 100)

        def uneven(value):
            return "".join(character * (8 if character == "文" else 1) for character in value), None

        chunks = list(phonemize_naturally(text, uneven, 510))
        self.assertEqual("".join(value for value, _ in chunks), text)
        self.assertEqual("".join(ps for _, ps in chunks), uneven(text)[0])
        self.assertTrue(all(len(ps) <= 510 for _, ps in chunks))

    def test_single_character_overflow_fails_instead_of_truncating(self) -> None:
        with self.assertRaisesRegex(ChunkingValidationError, "disable experimental"):
            list(phonemize_naturally("文", lambda _value: ("a" * 511, None), 510))

    def test_pipeline_default_and_explicit_false_use_established_splitter(self) -> None:
        pipeline = KPipeline.__new__(KPipeline)
        pipeline.lang_code = "j"
        pipeline.model = None
        pipeline.g2p = expanded
        text = "文" * 400
        with patch("kokorotts.pipeline.phonemize_naturally", side_effect=AssertionError):
            implicit = list(pipeline(text))
            explicit = list(pipeline(text, experimental_natural_chunking=False))
        self.assertEqual([r.graphemes for r in implicit], ["文" * 100] * 4)
        self.assertEqual([r.phonemes for r in implicit], [r.phonemes for r in explicit])

        natural = list(pipeline(text, experimental_natural_chunking=True))
        self.assertEqual([len(r.graphemes) for r in natural], [133, 133, 134])
        self.assertEqual("".join(r.graphemes for r in natural), text)

    def test_english_chunks_and_quality_ceiling_are_identical_in_both_modes(self) -> None:
        pipeline = KPipeline(lang_code="a", model=False)
        text = "A careful reader follows the sentence, and keeps every word clear. " * 15
        with patch("kokorotts.pipeline.phonemize_naturally", side_effect=AssertionError):
            standard = list(pipeline(text))
            experimental = list(pipeline(text, experimental_natural_chunking=True))
        self.assertEqual(
            [(r.graphemes, r.phonemes) for r in standard],
            [(r.graphemes, r.phonemes) for r in experimental],
        )
        self.assertTrue(all(len(r.phonemes) <= 400 for r in experimental))
